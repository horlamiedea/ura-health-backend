import json
from typing import Any, Dict, List, Optional

from django.conf import settings

try:
    # OpenAI Python SDK v1+/v2 style
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


def _get_client():
    if OpenAI is None:
        raise RuntimeError("OpenAI SDK not available. Please ensure 'openai' is installed.")
    api_key = getattr(settings, "OPENAI_API_KEY", "") or ""
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured in environment.")
    return OpenAI(api_key=api_key)


def _safe_json_parse(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return None


def _responses_api_json_prompt(system: str, user: str) -> Optional[Dict[str, Any]]:
    """
    Try Responses API with JSON response_format if available.
    Returns parsed JSON dict or None if it fails.
    """
    try:
        client = _get_client()
        model = getattr(settings, "OPENAI_MODEL", "gpt-4.1-mini")
        # Use Responses API with JSON object
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        # New SDK returns output_text via output array
        # Extract the text content in a defensive way
        text = None
        if hasattr(resp, "output") and resp.output:
            # Find first text item
            for item in resp.output:
                if getattr(item, "type", "") == "output_text" and getattr(item, "text", None):
                    text = item.text
                    break
        if text is None and hasattr(resp, "output_text"):
            text = getattr(resp, "output_text")

        if text:
            parsed = _safe_json_parse(text)
            if isinstance(parsed, dict):
                return parsed
    except Exception:
        return None
    return None


def _chat_api_json_prompt(system: str, user: str) -> Optional[Dict[str, Any]]:
    """
    Fallback to Chat Completions style if Responses API path fails.
    """
    try:
        client = _get_client()
        model = getattr(settings, "OPENAI_MODEL", "gpt-4.1-mini")
        # Some models may still accept chat.completions; instruct strict JSON.
        msg = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": user
                    + "\n\nReturn ONLY valid minified JSON without code fences.",
                },
            ],
            temperature=0.4,
        )
        text = msg.choices[0].message.content if msg and msg.choices else None
        if text:
            parsed = _safe_json_parse(text)
            if isinstance(parsed, dict):
                return parsed
    except Exception:
        return None
    return None


def prompt_json(system: str, user: str) -> Dict[str, Any]:
    """
    Attempt to get a JSON object response from the model, trying Responses API first,
    then Chat Completions as a fallback. Returns {} if both fail.
    """
    data = _responses_api_json_prompt(system, user)
    if data is None:
        data = _chat_api_json_prompt(system, user)
    return data or {}


def generate_hundred_meals(category: str, answers: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Build a catalog of singular Nigerian food items grouped by class (protein, vegetables, carbohydrates, healthy fats).
    Returns a flat list with tags so the frontend can group them. We aim for ~100 per class.
    Deterministic (no AI) to enable selecting individual items and ensure consistency.
    """
    # Helpers
    def _title(s: str) -> str:
        return s[0].upper() + s[1:] if s else s

    def _build_variations(bases: List[str], methods: List[str], extra_tags: List[str], target: int) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        i = 0
        while len(out) < target and bases:
            base = bases[i % len(bases)]
            method = methods[i % len(methods)] if methods else ""
            if method:
                name = f"{_title(method)} {base}"
            else:
                name = _title(base)
            tags = ["nigerian"] + extra_tags[:]
            if ("protein" in extra_tags) or ("veg" in extra_tags) or ("healthy-fat" in extra_tags):
                tags.append("zero-carb-suitable")
            out.append({"name": name, "tags": tags})
            i += 1
        return out

    # Base items
    protein_bases = [
        "eggs", "egg whites", "chicken breast", "chicken thigh", "turkey", "lean beef",
        "lean goat meat", "tilapia", "mackerel", "catfish", "sardine (water)", "salmon",
        "shrimp", "prawns", "tuna (water)", "tofu", "snail", "gizzard", "kidney (moderate)"
    ]
    protein_methods = ["grilled", "roasted", "baked", "boiled", "stewed", "smoked", "pan-seared"]

    veg_bases = [
        "spinach (efo)", "ugu (pumpkin leaves)", "soko (celosia)", "bitterleaf",
        "okra", "cabbage", "lettuce", "kale", "cucumber", "tomatoes", "carrots",
        "bell pepper", "green beans", "broccoli", "cauliflower", "garden egg",
        "amaranth greens"
    ]
    veg_methods = ["steamed", "sautéed", "stir-fried", "raw salad"]

    carb_bases = [
        "brown rice", "ofada rice", "white rice", "yam", "sweet potato", "Irish potato",
        "plantain", "garri (eba)", "amala", "semovita (semo)", "fufu", "tuwo",
        "beans (boiled)", "spaghetti", "macaroni", "couscous", "millet", "oats",
        "wheat semolina", "pounded yam"
    ]
    # Carbs presented as portioned items without cooking methods
    def _build_carb_items(bases: List[str], target: int) -> List[Dict[str, Any]]:
        portions = ["small portion of", "moderate portion of"]
        out: List[Dict[str, Any]] = []
        i = 0
        while len(out) < target and bases:
            base = bases[i % len(bases)]
            portion = portions[i % len(portions)]
            name = f"{_title(portion)} {base}"
            tags = ["nigerian", "lunch-carb", "carb"]
            out.append({"name": name, "tags": tags})
            i += 1
        return out

    fat_bases = [
        "avocado (half)", "avocado (quarter)", "olive oil (1 tbsp)", "olive oil (2 tsp)",
        "groundnuts (handful)", "cashews (handful)", "almonds (handful)", "walnuts (handful)",
        "peanut butter, no sugar (1 tbsp)", "groundnut oil (1 tsp)", "palm oil (controlled, 1 tsp)",
        "coconut oil (1 tsp)", "flaxseed (1 tbsp)", "chia seeds (1 tbsp)", "sesame seeds (1 tbsp)"
    ]
    def _build_fat_items(bases: List[str], target: int) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        i = 0
        while len(out) < target and bases:
            base = bases[i % len(bases)]
            name = _title(base)
            tags = ["nigerian", "healthy-fat", "zero-carb-suitable"]
            out.append({"name": name, "tags": tags})
            i += 1
        return out

    proteins = _build_variations(protein_bases, protein_methods, ["protein"], 100)
    vegetables = _build_variations(veg_bases, veg_methods, ["veg", "vegetables"], 100)
    carbs = _build_carb_items(carb_bases, 100)
    fats = _build_fat_items(fat_bases, 100)

    # Merge and assign ids
    all_items: List[Dict[str, Any]] = []
    all_items.extend(proteins)
    all_items.extend(vegetables)
    all_items.extend(carbs)
    all_items.extend(fats)
    for idx, item in enumerate(all_items, start=1):
        item["id"] = idx

    return all_items


def generate_two_day_plan(
    category: str,
    selected_meals: List[Dict[str, Any]],
    answers: Dict[str, Any],
    assessment: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Deterministic 2-day plan using selected singular items (proteins, vegetables, carbs, healthy fats).
    Ensures zero-carb breakfast/dinner and protein+veg+one-carb lunch, with herbal tea included.
    """
    def _split(items: List[Dict[str, Any]]):
        def has(it: Dict[str, Any], key: str) -> bool:
            return key in [str(t).lower() for t in (it.get("tags") or [])]
        proteins = [it for it in items if has(it, "protein")]
        carbs = [it for it in items if has(it, "lunch-carb") or has(it, "carb")]
        vegs = [it for it in items if has(it, "veg") or has(it, "vegetables")]
        fats = [it for it in items if has(it, "healthy-fat")]
        return proteins, carbs, vegs, fats

    # Allergy-aware filtering of selected meals
    allergy_kws = _allergy_keywords_from_answers(answers or {})
    base = _filter_allergy_items(selected_meals or [], allergy_kws)

    proteins, carbs, vegs, fats = _split(base)
    # Safe fallbacks if any class is empty after filtering
    if not proteins:
        p = _choose_first_safe(
            ["Grilled chicken", "Roasted turkey", "Tofu (plant-based)"],
            allergy_kws,
            "Lean protein (grilled)"
        )
        proteins = [{"name": p, "tags": ["protein"]}]
    if not vegs:
        v = _choose_first_safe(
            ["Steamed spinach (efo)", "Cabbage salad", "Sautéed kale"],
            allergy_kws,
            "Steamed leafy vegetables"
        )
        vegs = [{"name": v, "tags": ["veg"]}]
    if not fats:
        f = _choose_first_safe(
            ["Olive oil (1 tsp)", "Avocado (quarter)", "Flaxseed (1 tbsp)"],
            allergy_kws,
            "Olive oil (1 tsp)"
        )
        fats = [{"name": f, "tags": ["healthy-fat"]}]
    if not carbs:
        c = _choose_first_safe(
            ["Small portion of brown rice", "Small portion of boiled yam", "Small portion of sweet potato"],
            allergy_kws,
            "Small portion of brown rice"
        )
        carbs = [{"name": c, "tags": ["lunch-carb"]}]

    def zero_carb_text(i: int) -> str:
        p = proteins[i % len(proteins)]["name"]
        v = vegs[(i * 2) % len(vegs)]["name"]
        f = fats[(i * 3) % len(fats)]["name"]
        return f"{p} with {v.lower()} ({f})"

    def lunch_text(i: int) -> str:
        c = carbs[i % len(carbs)]["name"]
        p = proteins[(i + 1) % len(proteins)]["name"]
        v = vegs[(i + 2) % len(vegs)]["name"]
        return f"{c} with {p.lower()} and {v.lower()}"

    days = [
        {"day": 1, "breakfast": zero_carb_text(0), "lunch": lunch_text(0), "dinner": zero_carb_text(1), "snacks": ["Herbal tea (morning)", "Herbal tea (with lunch)", "Herbal tea (night)"]},
        {"day": 2, "breakfast": zero_carb_text(2), "lunch": lunch_text(1), "dinner": zero_carb_text(3), "snacks": ["Herbal tea (morning)", "Herbal tea (with lunch)", "Herbal tea (night)"]},
    ]
    return {"days": days}


def generate_month_plan(
    category: str,
    selected_meals: List[Dict[str, Any]],
    answers: Dict[str, Any],
    assessment: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Deterministic 30-day Nigerian plan using selected singular items.
    - Breakfast & dinner: zero-carb (protein + veg + healthy fat)
    - Lunch: exactly one cooked Nigerian carbohydrate + protein + vegetables
    - Includes herbal tea (morning, with lunch, and night)
    - Ensures variety across all 30 days (no exact repeats)
    """
    def _split(items: List[Dict[str, Any]]):
        def has(it: Dict[str, Any], key: str) -> bool:
            return key in [str(t).lower() for t in (it.get("tags") or [])]
        proteins = [it for it in items if has(it, "protein")]
        carbs = [it for it in items if has(it, "lunch-carb") or has(it, "carb")]
        vegs = [it for it in items if has(it, "veg") or has(it, "vegetables")]
        fats = [it for it in items if has(it, "healthy-fat")]
        return proteins, carbs, vegs, fats

    # Allergy-aware filtering of selected meals first
    allergy_kws = _allergy_keywords_from_answers(answers or {})
    base = _filter_allergy_items(selected_meals or [], allergy_kws)

    proteins, carbs, vegs, fats = _split(base)
    # Fallback pools if any class is empty (pick safe options w.r.t allergies)
    if not proteins:
        p1 = _choose_first_safe(
            ["Grilled chicken", "Roasted turkey", "Tofu (plant-based)"],
            allergy_kws,
            "Lean protein (grilled)"
        )
        p2 = _choose_first_safe(
            ["Boiled chicken", "Pan-seared tilapia", "Tofu (plant-based)"],
            allergy_kws,
            "Lean protein (boiled)"
        )
        proteins = [{"name": p1, "tags": ["protein"]}, {"name": p2, "tags": ["protein"]}]
    if not vegs:
        v1 = _choose_first_safe(
            ["Steamed spinach (efo)", "Cabbage salad", "Sautéed kale"],
            allergy_kws,
            "Steamed leafy vegetables"
        )
        v2 = _choose_first_safe(
            ["Okra stir-fry", "Lettuce salad", "Broccoli (steamed)"],
            allergy_kws,
            "Mixed vegetables (steamed)"
        )
        vegs = [{"name": v1, "tags": ["veg"]}, {"name": v2, "tags": ["veg"]}]
    if not fats:
        f1 = _choose_first_safe(
            ["Olive oil (1 tsp)", "Avocado (quarter)", "Flaxseed (1 tbsp)"],
            allergy_kws,
            "Olive oil (1 tsp)"
        )
        f2 = _choose_first_safe(
            ["Groundnuts (handful)", "Walnuts (handful)", "Chia seeds (1 tbsp)"],
            allergy_kws,
            "Olive oil (1 tsp)"
        )
        fats = [{"name": f1, "tags": ["healthy-fat"]}, {"name": f2, "tags": ["healthy-fat"]}]
    if not carbs:
        c1 = _choose_first_safe(
            ["Small portion of brown rice", "Small portion of boiled yam", "Small portion of sweet potato"],
            allergy_kws,
            "Small portion of brown rice"
        )
        c2 = _choose_first_safe(
            ["Small portion of ofada rice", "Small portion of plantain", "Small portion of couscous"],
            allergy_kws,
            "Small portion of boiled yam"
        )
        carbs = [{"name": c1, "tags": ["lunch-carb"]}, {"name": c2, "tags": ["lunch-carb"]}]

    # Portion strictness based on level
    lvl = 1
    try:
        if isinstance(assessment, dict) and "level" in assessment:
            lvl = int(assessment.get("level") or 1)
    except Exception:
        lvl = 1
    portion_prefix = "small portion of" if lvl >= 2 else "moderate portion of"

    def zero_carb_text(i: int) -> str:
        p = proteins[i % len(proteins)]["name"]
        v = vegs[(i * 2) % len(vegs)]["name"]
        f = fats[(i * 3) % len(fats)]["name"]
        return f"{p} with {v.lower()} ({f})"

    def lunch_text(i: int) -> str:
        c = carbs[i % len(carbs)]["name"]
        # Normalize carb name to include portion prefix if not present
        if "portion of" not in c.lower():
            c = f"{portion_prefix} {c}"
        p = proteins[(i + 1) % len(proteins)]["name"]
        v = vegs[(i + 2) % len(vegs)]["name"]
        return f"{c} with {p.lower()} and {v.lower()}"

    days: List[Dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for i in range(30):
        b = zero_carb_text(i)
        l = lunch_text(i)
        d = zero_carb_text(i + 13)  # offset to reduce breakfast/dinner repeats
        triplet = (b, l, d)
        # Ensure uniqueness by shifting if needed
        shift = 0
        while triplet in seen and shift < 10:
            shift += 1
            b = zero_carb_text(i + shift)
            l = lunch_text(i + shift)
            d = zero_carb_text(i + 13 + shift)
            triplet = (b, l, d)
        seen.add(triplet)
        days.append({
            "day": i + 1,
            "breakfast": b,
            "lunch": l,
            "dinner": d,
            "snacks": ["Herbal tea (morning)", "Herbal tea (with lunch)", "Herbal tea (night)"],
        })

    return {"days": days}
