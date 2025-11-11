import re
import json
from typing import Any, Dict, Optional, Tuple

from django.conf import settings

# Lazy import to avoid circular dependency at module import time
def _prompt_json(system: str, user: str) -> Dict[str, Any]:
    try:
        from . import ai  # local import
        return ai.prompt_json(system, user)
    except Exception:
        return {}


def _to_number(text: Any) -> Optional[float]:
    if text in (None, ""):
        return None
    try:
        return float(text)
    except Exception:
        s = str(text)
        m = re.search(r"-?\d+(\.\d+)?", s)
        if m:
            try:
                return float(m.group(0))
            except Exception:
                return None
    return None


def _parse_bp(bp_text: Any) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse blood pressure strings like '130/85', '140 / 95 mmHg' -> (130, 95).
    """
    if bp_text in (None, ""):
        return (None, None)
    s = str(bp_text)
    m = re.search(r"(\d{2,3})\s*/\s*(\d{2,3})", s)
    if not m:
        return (None, None)
    try:
        sys = float(m.group(1))
        dia = float(m.group(2))
        return (sys, dia)
    except Exception:
        return (None, None)


def _parse_hba1c(text: Any) -> Optional[float]:
    """
    Parse HbA1c like '6.5%', '7', '7.2 %' -> 6.5, 7.0, 7.2
    """
    v = _to_number(text)
    return v


def _parse_fbs(text: Any) -> Optional[float]:
    """
    Parse fasting blood sugar in mg/dL from strings like '110 mg/dL', '180', etc.
    Assumes mg/dL. If mmol/L provided, user should specify; we do not convert automatically here.
    """
    v = _to_number(text)
    return v


def _compute_bmi(weight_kg: Optional[float], height_cm: Optional[float]) -> Optional[float]:
    if weight_kg is None or height_cm is None or height_cm == 0:
        return None
    h_m = height_cm / 100.0
    if h_m <= 0:
        return None
    return round(weight_kg / (h_m * h_m), 1)


def _get_answer(answers: Dict[str, Any], label: str) -> Any:
    # answers come keyed by exact question label
    return answers.get(label)


def _classify_diabetes(answers: Dict[str, Any]) -> Dict[str, Any]:
    fbs = _parse_fbs(_get_answer(answers, "Last known blood sugar reading (Fasting):"))
    hba1c = _parse_hba1c(_get_answer(answers, "Last known HbA1c (if tested):"))
    bp_str = _get_answer(answers, "Blood pressure (last reading, if known):")
    sys, dia = _parse_bp(bp_str)

    # Determine severity by worst metric met
    level = 1
    reasons = []

    if fbs is not None:
        if fbs > 180:
            level = max(level, 3)
            reasons.append(f"FBS {fbs} mg/dL > 180 -> Level 3")
        elif 126 <= fbs <= 180:
            level = max(level, 2)
            reasons.append(f"FBS {fbs} mg/dL in 126–180 -> Level 2")
        elif 100 <= fbs <= 125:
            level = max(level, 1)
            reasons.append(f"FBS {fbs} mg/dL in 100–125 -> Level 1")

    if hba1c is not None:
        if hba1c >= 8.0:
            level = max(level, 3)
            reasons.append(f"HbA1c {hba1c}% ≥ 8 -> Level 3")
        elif 6.5 <= hba1c <= 7.9:
            level = max(level, 2)
            reasons.append(f"HbA1c {hba1c}% in 6.5–7.9 -> Level 2")
        elif 5.7 <= hba1c <= 6.4:
            level = max(level, 1)
            reasons.append(f"HbA1c {hba1c}% in 5.7–6.4 -> Level 1")

    # Blood pressure may suggest metabolic syndrome risk; do not upstage beyond glucose-based rules automatically.
    if sys is not None and dia is not None:
        reasons.append(f"BP reading noted: {int(sys)}/{int(dia)} mmHg")

    label = {1: "mild", 2: "moderate", 3: "severe"}[level]
    return {
        "condition": "diabetes",
        "level": level,
        "label": label,
        "metrics": {"fbs_mg_dl": fbs, "hba1c_percent": hba1c, "bp": f"{int(sys)}/{int(dia)}" if sys and dia else None},
        "reasoning": "; ".join(reasons) if reasons else "Insufficient metrics; defaulted to Level 1 (mild).",
    }


def _classify_hbp(answers: Dict[str, Any]) -> Dict[str, Any]:
    bp = _get_answer(answers, "Current Blood Pressure Reading:")
    sys, dia = _parse_bp(bp)
    level = 1
    reasons = []

    if sys is None or dia is None:
        # Fallback on qualitative symptoms/diet; default to Level 1
        return {
            "condition": "hbp",
            "level": level,
            "label": "mild",
            "metrics": {"bp": None},
            "reasoning": "No BP reading provided; defaulted to Level 1 if history suggests prehypertension.",
        }

    if sys >= 160 or dia >= 100:
        level = 3
        reasons.append(f"BP {int(sys)}/{int(dia)} ≥ 160/100 -> Level 3")
    elif (140 <= sys <= 159) or (90 <= dia <= 99):
        level = 2
        reasons.append(f"BP {int(sys)}/{int(dia)} in 140–159/90–99 -> Level 2")
    elif (130 <= sys <= 139) or (80 <= dia <= 89):
        level = 1
        reasons.append(f"BP {int(sys)}/{int(dia)} in 130–139/80–89 -> Level 1")
    else:
        # <130/80, if user still has HBP history, keep mild
        reasons.append(f"BP {int(sys)}/{int(dia)} below 130/80; classify as Level 1 if symptomatic/history.")

    label = {1: "mild", 2: "moderate", 3: "severe"}[level]
    return {
        "condition": "hbp",
        "level": level,
        "label": label,
        "metrics": {"bp": f"{int(sys)}/{int(dia)}"},
        "reasoning": "; ".join(reasons),
    }


def _classify_weight(answers: Dict[str, Any]) -> Dict[str, Any]:
    bmi = _to_number(_get_answer(answers, "Body Mass Index (BMI):"))
    if bmi is None:
        wt = _to_number(_get_answer(answers, "Current Weight (kg):"))
        ht = _to_number(_get_answer(answers, "Height (cm):"))
        bmi = _compute_bmi(wt, ht)

    level = 1
    reasons = []
    if bmi is not None:
        if bmi >= 40:
            level = 3
            reasons.append(f"BMI {bmi} ≥ 40 -> Level 3")
        elif 30 <= bmi <= 39.9:
            level = 2
            reasons.append(f"BMI {bmi} in 30–39.9 -> Level 2")
        elif 25 <= bmi <= 29.9:
            level = 1
            reasons.append(f"BMI {bmi} in 25–29.9 -> Level 1")
        else:
            reasons.append(f"BMI {bmi} below 25; default to Level 1 if weight concerns persist.")
    else:
        reasons.append("Insufficient data to compute BMI; defaulted to Level 1.")

    label = {1: "mild", 2: "moderate", 3: "severe"}[level]
    return {
        "condition": "weight",
        "level": level,
        "label": label,
        "metrics": {"bmi": bmi},
        "reasoning": "; ".join(reasons),
    }


def _deterministic_assessment(category: str, answers: Dict[str, Any]) -> Dict[str, Any]:
    cat = (category or "").lower()
    if cat == "diabetes":
        return _classify_diabetes(answers)
    if cat in ("hbp", "high blood pressure", "hypertension"):
        return _classify_hbp(answers)
    if cat in ("weight", "weight management", "obesity"):
        return _classify_weight(answers)
    # Detox has no levels defined; default to mild-like
    return {
        "condition": "detox",
        "level": 1,
        "label": "mild",
        "metrics": {},
        "reasoning": "Detox category: default single-tier guidance.",
    }


def assess_level(category: str, answers: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assess health level for the given category using AI with a deterministic fallback.
    Returns a JSON-friendly dict:
    {
      "condition": "diabetes|hbp|weight|detox",
      "level": 1|2|3,
      "label": "mild|moderate|severe",
      "metrics": {...},
      "reasoning": "..."
    }
    """
    # 1) Try AI with strict JSON, using the explicit rules as guardrails.
    rule_text = (
        "Rules:\n"
        "- Diabetes: Level 1 if FBS 100–125 or HbA1c 5.7–6.4; Level 2 if FBS 126–180 or HbA1c 6.5–7.9; "
        "Level 3 if FBS >180 or HbA1c ≥8. Consider the highest severity when multiple metrics provided.\n"
        "- Hypertension: Level 1 for 130–139/80–89; Level 2 for 140–159/90–99; Level 3 for ≥160/100.\n"
        "- Obesity/Weight: Level 1 for BMI 25–29.9; Level 2 for BMI 30–39.9; Level 3 for BMI ≥40.\n"
        "- Detox: single-tier; treat as Level 1.\n"
        "Output JSON with keys: condition, level (1|2|3), label ('mild'|'moderate'|'severe'), metrics, reasoning."
    )
    system = "You are a medical triage assistant. Follow rules exactly, be safe, and return STRICT JSON."
    user = (
        f"{rule_text}\n\n"
        f"Category: {category}\n"
        f"Answers: {json.dumps(answers, ensure_ascii=False)}\n"
        "Return only JSON: {\"condition\":\"...\",\"level\":1,\"label\":\"mild|moderate|severe\",\"metrics\":{...},\"reasoning\":\"...\"}"
    )
    ai_out = _prompt_json(system, user)
    try:
        if isinstance(ai_out, dict) and "level" in ai_out and ai_out.get("condition"):
            lvl = int(ai_out.get("level"))
            if lvl in (1, 2, 3):
                # Sanitize label
                lbl = str(ai_out.get("label") or "").lower().strip()
                if lbl not in ("mild", "moderate", "severe"):
                    lbl = {1: "mild", 2: "moderate", 3: "severe"}[lvl]
                metrics = ai_out.get("metrics") if isinstance(ai_out.get("metrics"), dict) else {}
                reasoning = str(ai_out.get("reasoning") or "")
                return {
                    "condition": str(ai_out.get("condition")).lower(),
                    "level": lvl,
                    "label": lbl,
                    "metrics": metrics,
                    "reasoning": reasoning,
                }
    except Exception:
        pass

    # 2) Fallback: deterministic rules
    return _deterministic_assessment(category, answers)


# -----------------------
# Diet guidance utilities
# -----------------------
def get_diet_recommendations(category: str, level: int) -> Dict[str, Any]:
    """
    Return diet guidance text (title + bullets) per category/level based on provided spec.
    Purely deterministic. Safe language only (not medical advice).
    """
    cat = (category or "").lower()
    lvl = level if level in (1, 2, 3) else 1

    def pack(title: str, bullets: list[str]) -> Dict[str, Any]:
        return {"title": title, "bullets": bullets}

    if cat == "diabetes":
        if lvl == 1:
            return pack(
                "Diabetes • Level 1 – Mild (Prediabetes)",
                [
                    "Early morning tea; breakfast with vegetables + protein or low‑carb option.",
                    "Lunch: one Nigerian carbohydrate + vegetables + protein.",
                    "Dinner: zero‑carb (protein + vegetables + healthy fat).",
                    "Avoid refined sugar/flour; exercise ~30 mins/day; check blood sugar weekly.",
                ],
            )
        if lvl == 2:
            return pack(
                "Diabetes • Level 2 – Moderate (Controlled/Developing)",
                [
                    "Breakfast and dinner: zero‑carb (protein + vegetables + healthy fat).",
                    "Lunch: one small carbohydrate + vegetables + protein.",
                    "Control portions; avoid fried foods; keep regular mealtimes.",
                ],
            )
        return pack(
            "Diabetes • Level 3 – Severe (Uncontrolled)",
            [
                "Strict zero‑carb breakfast/dinner; lunch is a small carbohydrate + vegetables + protein.",
                "Tight glycemic control focus; aim for remission with clinician oversight.",
            ],
        )

    if cat in ("hbp", "high blood pressure", "hypertension"):
        if lvl == 1:
            return pack(
                "Hypertension • Level 1 – Mild (Prehypertension)",
                [
                    "Reduce salt and processed foods; hydrate (3–4 L/day as tolerated).",
                    "Regular physical activity such as daily walks.",
                ],
            )
        if lvl == 2:
            return pack(
                "Hypertension • Level 2 – Moderate (Stage 1)",
                [
                    "Low‑sodium pattern; include turmeric/probiotic vegetables where possible.",
                    "Tea with meals; monitor blood pressure daily.",
                ],
            )
        return pack(
            "Hypertension • Level 3 – Severe (Stage 2)",
            [
                "Strict low‑sodium, low‑fat plan; avoid canned foods and red meat.",
                "Herbal teas (hibiscus with ginger & cinnamon); regular follow‑up care.",
            ],
        )

    if cat in ("weight", "weight management", "obesity"):
        if lvl == 1:
            return pack(
                "Weight • Level 1 – Mild (Overweight)",
                [
                    "Portion control (~25% reduction); avoid late‑night meals.",
                    "Walk 30–45 mins/day.",
                ],
            )
        if lvl == 2:
            return pack(
                "Weight • Level 2 – Moderate (Obese I–II)",
                [
                    "Eliminate fried foods/sugary drinks; drink warm water before meals.",
                    "Track progress weekly.",
                ],
            )
        return pack(
            "Weight • Level 3 – Severe (Morbid Obesity)",
            [
                "Strict calorie restriction; no sugar/flour/alcohol.",
                "Medical supervision recommended.",
            ],
        )

    # Detox or unknown
    return {
        "title": "Detox • General guidance",
        "bullets": [
            "Emphasis on vegetables, lean proteins, and hydration.",
            "Avoid ultra‑processed foods and excess sugars.",
        ],
    }


def pick_recommended_meals(category: str, level: int, hundred_meals: list[dict[str, Any]], limit: int = 24) -> list[dict[str, Any]]:
    """
    Deterministically pick a stage‑appropriate subset from the 100‑meal catalog.
    Uses tags: 'protein', 'veg'/'vegetables', 'healthy-fat', 'lunch-carb'/'carb', 'zero-carb-suitable'.
    """
    def has_tag(item: dict[str, Any], tag: str) -> bool:
        return tag in [str(t).lower() for t in (item.get("tags") or [])]

    proteins = [it for it in hundred_meals if has_tag(it, "protein")]
    vegs = [it for it in hundred_meals if has_tag(it, "veg") or has_tag(it, "vegetables")]
    fats = [it for it in hundred_meals if has_tag(it, "healthy-fat")]
    carbs = [it for it in hundred_meals if has_tag(it, "lunch-carb") or has_tag(it, "carb")]

    # Carb emphasis decreases with severity
    lvl = level if level in (1, 2, 3) else 1
    carb_quota = 6 if lvl == 1 else (4 if lvl == 2 else 2)
    protein_quota = 8 if lvl >= 2 else 6
    veg_quota = 8
    fat_quota = 4

    # Assemble deterministically (stable order), then trim and dedupe by id
    rec = []
    rec.extend(proteins[:protein_quota])
    rec.extend(vegs[:veg_quota])
    rec.extend(fats[:fat_quota])
    rec.extend(carbs[:carb_quota])

    # Deduplicate by id and keep original order
    seen_ids = set()
    out: list[dict[str, Any]] = []
    for it in rec:
        iid = it.get("id")
        if iid in seen_ids:
            continue
        seen_ids.add(iid)
        out.append({"id": iid, "name": it.get("name"), "tags": it.get("tags")})

    if limit and len(out) > limit:
        out = out[:limit]
    return out


def get_stage_template(
    category: str,
    level: int,
    hundred_meals: list[dict[str, Any]] | None = None,
    answers: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Deterministic stage template text that mirrors the exact structure requested,
    but with vague references (e.g., "as listed previously") resolved into explicit
    Nigerian meal examples tailored to the user's condition and allergies.

    Keys:
      - title
      - early_morning (optional)
      - breakfast
      - lunch
      - snack
      - dinner
      - recommendation (list[str])
    """
    cat = (category or "").lower()
    lvl = level if level in (1, 2, 3) else 1
    items = hundred_meals or []
    ans = answers or {}

    # Allergy handling
    def _allergy_keywords(a: Dict[str, Any]) -> set[str]:
        # Look for any answer field that mentions 'allerg'
        text = ""
        for k, v in a.items():
            if "allerg" in str(k).lower():
                text += f" {v}"
        kws = set()
        for raw in str(text).lower().replace("/", " ").replace("|", " ").replace("&", " ").replace(";", " ").split(","):
            token = raw.strip()
            if not token:
                continue
            # split further by whitespace to capture single words like 'egg', 'fish'
            for w in token.split():
                if len(w) >= 3:
                    kws.add(w)
        return kws

    allergy_kws = _allergy_keywords(ans)

    def _has_tag(it: dict[str, Any], tag: str) -> bool:
        return tag in [str(t).lower() for t in (it.get("tags") or [])]

    def _filter_allergies(pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not allergy_kws:
            return pool
        out: list[dict[str, Any]] = []
        for it in pool:
            name = str(it.get("name") or "").lower()
            if any(kw in name for kw in allergy_kws):
                continue
            out.append(it)
        return out

    def _split_catalog(items: list[dict[str, Any]]):
        proteins = _filter_allergies([it for it in items if _has_tag(it, "protein")])
        vegs = _filter_allergies([it for it in items if _has_tag(it, "veg") or _has_tag(it, "vegetables")])
        fats = _filter_allergies([it for it in items if _has_tag(it, "healthy-fat")])
        carbs = _filter_allergies([it for it in items if _has_tag(it, "lunch-carb") or _has_tag(it, "carb")])
        # Robust fallbacks if filtering removes everything
        if not proteins:
            proteins = [{"name": "Grilled turkey (lean)", "tags": ["protein"]}]
        if not vegs:
            vegs = [{"name": "Steamed spinach (efo)", "tags": ["veg"]}]
        if not fats:
            fats = [{"name": "Olive oil (1 tsp)", "tags": ["healthy-fat"]}]
        if not carbs:
            carbs = [{"name": "Small portion of brown rice", "tags": ["lunch-carb"]}]
        return proteins, carbs, vegs, fats

    proteins, carbs, vegs, fats = _split_catalog(items)

    def _choose(pool: list[dict[str, Any]], i: int) -> str:
        return str(pool[i % len(pool)]["name"])

    def _zero_carb(i: int) -> str:
        p = _choose(proteins, i)
        v = _choose(vegs, i * 2)
        f = _choose(fats, i * 3)
        return f"{p} with {v.lower()} ({f})"

    def _lunch(i: int, portion_prefix: str) -> str:
        c = _choose(carbs, i)
        # normalize carb string to include portion prefix if not present
        if "portion of" not in c.lower():
            c = f"{portion_prefix} {c}"
        p = _choose(proteins, i + 1).lower()
        v = _choose(vegs, i + 2).lower()
        return f"{c} with {p} and {v}"

    def _snack(i: int) -> str:
        fat_item = _choose(fats, i)
        return f"Herbal tea; {fat_item}"

    def pack(title: str,
             breakfast: str,
             lunch: str,
             snack: str,
             dinner: str,
             recommendation: list[str],
             early_morning: str | None = None) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "title": title,
            "breakfast": breakfast,
            "lunch": lunch,
            "snack": snack,
            "dinner": dinner,
            "recommendation": recommendation,
        }
        if early_morning:
            out["early_morning"] = early_morning
        return out

    # Portion strictness rule (used for lunch composition)
    portion_prefix = "moderate portion of" if lvl == 1 else ("small portion of" if lvl >= 2 else "moderate portion of")

    # Diabetes: explicit examples (no vague phrases)
    if cat == "diabetes":
        if lvl == 1:
            return pack(
                "LEVEL 1 — MILD (Pre-diabetes)",
                # Keep provided wording but include a concrete example as prefix
                f"{_zero_carb(0)}; or vegetable smoothie + protein; or a slice of bread with vegetables and protein; low‑carb English breakfast",
                _lunch(0, portion_prefix="moderate portion of"),
                _snack(0),
                _zero_carb(1),
                [
                    "Avoid refined sugar and flour.",
                    "Exercise 30 mins/day.",
                    "Check blood sugar weekly.",
                ],
                early_morning="Early morning hours (6am-8am) a cup of tea",
            )
        if lvl == 2:
            return pack(
                "LEVEL 2 — MODERATE",
                _zero_carb(2),
                _lunch(1, portion_prefix="small portion of"),
                _snack(1),
                _zero_carb(3),
                [
                    "Control carbohydrate portions.",
                    "Avoid fried foods.",
                    "Maintain regular mealtime.",
                ],
            )
        # Level 3
        return pack(
            "LEVEL 3 — SEVERE",
            _zero_carb(4),
            _lunch(2, portion_prefix="small portion of"),
            _snack(2),
            _zero_carb(5),
            [
                "Include 1 day of fasting with vegetable smoothies + protein and vegetable salad weekly.",
                "Strict low-GI diet.",
                "Avoid sugary fruits & processed food.",
                "Regular doctor review.",
            ],
        )

    # Hypertension: breakfast/lunch/snack/dinner align with equivalent diabetes level
    if cat in ("hbp", "high blood pressure", "hypertension"):
        dia = get_stage_template("diabetes", lvl, hundred_meals=items, answers=ans)
        if lvl == 1:
            recs = [
                "Reduce salt and processed foods.",
                "Hydrate well.(3-4liters of water daily)",
                "Engage in regular walks. (90 minutes daily)",
            ]
        elif lvl == 2:
            recs = [
                "Include turmeric probiotics elixir & probiotic vegetable to daily diet",
                "includ tea to each meal",
                "Monitor BP daily.",
            ]
        else:
            recs = [
                "Strict low-sodium, low-fat plan.",
                "Avoid canned foods & red meat.",
                "Include probiotic turmeric elixir and probiotic vegetables.",
                "Tea should be made with Herbiscus, ginger & cinnamon.",
                "Regular follow-up care.",
            ]
        return pack(
            f"LEVEL {lvl} — {'MILD' if lvl==1 else 'MODERATE' if lvl==2 else 'SEVERE'}",
            dia.get("breakfast", _zero_carb(0)),
            dia.get("lunch", _lunch(0, portion_prefix)),
            dia.get("snack", _snack(0)),
            dia.get("dinner", _zero_carb(1)),
            recs,
        )

    # Weight/Obesity: align with equivalent diabetes level for meals
    if cat in ("weight", "weight management", "obesity"):
        dia = get_stage_template("diabetes", lvl, hundred_meals=items, answers=ans)
        if lvl == 1:
            recs = [
                "Portion control (reduce serving size by 25%).",
                "Avoid late-night meals.",
                "Walk 30–45 mins/day.",
            ]
        elif lvl == 2:
            recs = [
                "Eliminate fried foods & sugary drinks.",
                "Drink warm water before meals.",
                "Track weekly progress.",
            ]
        else:
            recs = [
                "Strict calorie restriction.",
                "No sugar, flour, or alcohol.",
                "Medical supervision advised.",
            ]
        # Level 3 spec mentioned snack: Herbal tea; keep explicit
        snack_text = "Herbal tea" if lvl == 3 else dia.get("snack", _snack(0))
        return pack(
            f"LEVEL {lvl} — {'MILD' if lvl==1 else 'MODERATE' if lvl==2 else 'SEVERE'}",
            dia.get("breakfast", _zero_carb(0)),
            dia.get("lunch", _lunch(0, portion_prefix)),
            snack_text,
            dia.get("dinner", _zero_carb(1)),
            recs,
        )

    # Detox or unknown: keep minimal guidance with examples
    return {
        "title": "General wellness template",
        "breakfast": _zero_carb(0),
        "lunch": _lunch(0, portion_prefix="moderate portion of"),
        "snack": _snack(0),
        "dinner": _zero_carb(1),
        "recommendation": ["Hydrate well.", "Avoid ultra-processed foods."],
    }
