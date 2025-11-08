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
