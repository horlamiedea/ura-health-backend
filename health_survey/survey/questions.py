from typing import Dict, List, Any


# Each question may optionally include:
# - required_when: {"questionId": <int>, "values": [<str>, ...]}
#   Meaning the question is only required when the referenced question's answer matches one of the provided values.


DIABETES_QUESTIONS: List[Dict[str, Any]] = [
    {"id": 1, "question": "Full Name:", "type": "text"},
    {"id": 2, "question": "Age:", "type": "number"},
    {"id": 3, "question": "Sex:", "type": "choice", "options": ["Male", "Female"]},
    {"id": 4, "question": "Date of Birth (DD/MM/YYYY):", "type": "date"},
    {"id": 5, "question": "Marital Status:", "type": "text"},
    {"id": 6, "question": "Occupation:", "type": "text"},
    {"id": 7, "question": "Phone Number:", "type": "text"},
    {"id": 8, "question": "Location:", "type": "text"},
    {"id": 9, "question": "Have you ever been diagnosed with diabetes?", "type": "choice", "options": ["Yes", "No"]},
    # Only required if Q9 == "Yes"
    {"id": 10, "question": "If yes, when? (YYYY-MM-DD)", "type": "date", "required_when": {"questionId": 9, "values": ["Yes"]}},
    {"id": 11, "question": "Type of Diabetes:", "type": "choice", "options": ["Type 1", "Type 2", "Gestational", "Not sure"]},
    {"id": 12, "question": "Family history of diabetes?", "type": "choice", "options": ["Yes", "No"]},
    # Only required if Q12 == "Yes"
    {"id": 13, "question": "If yes, who?", "type": "text", "required_when": {"questionId": 12, "values": ["Yes"]}},
    {"id": 14, "question": "Are you currently on diabetes medications?", "type": "choice", "options": ["Yes", "No"]},
    # Only required if Q14 == "Yes"
    {"id": 15, "question": "If yes, which ones?", "type": "text", "required_when": {"questionId": 14, "values": ["Yes"]}},
    {"id": 16, "question": "Have you ever been on insulin?", "type": "choice", "options": ["Yes", "No"]},
    {"id": 17, "question": "Any other diagnosed health conditions?", "type": "text"},
    {"id": 18, "question": "Allergies (food or drug):", "type": "text"},
    {"id": 19, "question": "Smoking:", "type": "choice", "options": ["Never", "Former smoker", "Current smoker"]},
    {"id": 20, "question": "Alcohol:", "type": "choice", "options": ["None", "Occasionally", "Frequently"]},
    {"id": 21, "question": "Physical activity:", "type": "choice", "options": ["None", "1-2 times/week", "3-4 times/week", "Daily"]},
    {"id": 22, "question": "What type of activity?", "type": "text"},
    {"id": 23, "question": "Sleep patterns:", "type": "choice", "options": ["Poor", "Fair", "Good"]},
    {"id": 24, "question": "Average hours per night:", "type": "number"},
    {"id": 25, "question": "Stress level:", "type": "choice", "options": ["Low", "Moderate", "High"]},
    {"id": 26, "question": "How many meals do you eat per day?", "type": "number"},
    {"id": 27, "question": "Do you eat late at night?", "type": "choice", "options": ["Yes", "No"]},
    {"id": 28, "question": "How often do you eat Rice/Yam/Cassava foods?", "type": "choice", "options": ["Daily", "Weekly", "Rarely"]},
    {"id": 29, "question": "How often do you eat Vegetables/leafy greens?", "type": "choice", "options": ["Daily", "Weekly", "Rarely"]},
    {"id": 30, "question": "How often do you eat Sugary drinks/snacks?", "type": "choice", "options": ["Daily", "Weekly", "Rarely"]},
    {"id": 31, "question": "Symptoms in past 3 months (tick all that apply):", "type": "multiselect", "options": [
        "Frequent urination", "Excessive thirst", "Unexplained weight loss", "Constant hunger",
        "Blurred vision", "Slow-healing wounds", "Tingling or numbness in hands/feet",
        "Fatigue/weakness", "Recurrent infections", "Headaches/dizziness",
        "Sleep disturbances", "Increased irritability or mood swings"
    ]},
    {"id": 32, "question": "Last known blood sugar reading (Fasting):", "type": "text"},
    {"id": 33, "question": "Last known HbA1c (if tested):", "type": "text"},
    {"id": 34, "question": "Current weight (kg):", "type": "number"},
    {"id": 35, "question": "Height (cm):", "type": "number"},
    {"id": 36, "question": "Waist circumference (cm):", "type": "number"},
    {"id": 37, "question": "Blood pressure (last reading, if known):", "type": "text"},
    {"id": 38, "question": "What are your main health goals?", "type": "textarea"},
    {"id": 39, "question": "What challenges do you face in managing your diabetes?", "type": "textarea"},
]

HBP_QUESTIONS: List[Dict[str, Any]] = [
    {"id": 1, "question": "Full Name:", "type": "text"},
    {"id": 2, "question": "Date of Birth (DD/MM/YYYY):", "type": "date"},
    {"id": 3, "question": "Age:", "type": "number"},
    {"id": 4, "question": "Gender:", "type": "choice", "options": ["Male", "Female", "Other"]},
    {"id": 5, "question": "Marital Status:", "type": "text"},
    {"id": 6, "question": "Address:", "type": "text"},
    {"id": 7, "question": "Phone Number:", "type": "text"},
    {"id": 8, "question": "Email:", "type": "email"},
    {"id": 9, "question": "Occupation:", "type": "text"},
    {"id": 10, "question": "Do you have a history of high blood pressure (hypertension)?", "type": "choice", "options": ["Yes", "No"]},
    # Only required if Q10 == "Yes"
    {"id": 11, "question": "If yes, for how long?", "type": "text", "required_when": {"questionId": 10, "values": ["Yes"]}},
    {"id": 12, "question": "Family history of high blood pressure?", "type": "choice", "options": ["Yes", "No"]},
    # Only required if Q12 == "Yes"
    {"id": 13, "question": "If yes, indicate relation:", "type": "text", "required_when": {"questionId": 12, "values": ["Yes"]}},
    {"id": 14, "question": "Other family health conditions:", "type": "textarea"},
    {"id": 15, "question": "Personal medical history:", "type": "textarea"},
    {"id": 16, "question": "Do you take medication for high blood pressure?", "type": "choice", "options": ["Yes", "No"]},
    # Only required if Q16 == "Yes"
    {"id": 17, "question": "If yes, please list:", "type": "textarea", "required_when": {"questionId": 16, "values": ["Yes"]}},
    {"id": 18, "question": "Any herbal remedies or supplements currently used?", "type": "choice", "options": ["Yes", "No"]},
    # Only required if Q18 == "Yes"
    {"id": 19, "question": "If yes, specify:", "type": "textarea", "required_when": {"questionId": 18, "values": ["Yes"]}},
    {"id": 20, "question": "How often do you eat fruits/vegetables?", "type": "choice", "options": ["Daily", "Occasionally", "Rarely"]},
    {"id": 21, "question": "Salt intake:", "type": "choice", "options": ["Low", "Moderate", "High"]},
    {"id": 22, "question": "Do you eat processed/fast food regularly?", "type": "choice", "options": ["Yes", "No"]},
    {"id": 23, "question": "Alcohol consumption:", "type": "choice", "options": ["None", "Occasionally", "Frequently"]},
    {"id": 24, "question": "Do you exercise?", "type": "choice", "options": ["Yes", "No"]},
    # Only required if Q24 == "Yes"
    {"id": 25, "question": "If yes, what type and how often?", "type": "textarea", "required_when": {"questionId": 24, "values": ["Yes"]}},
    {"id": 26, "question": "Do you smoke?", "type": "choice", "options": ["Yes", "No"]},
    # Only required if Q26 == "Yes"
    {"id": 27, "question": "If yes, how many sticks per day?", "type": "text", "required_when": {"questionId": 26, "values": ["Yes"]}},
    {"id": 28, "question": "How would you rate your daily stress?", "type": "choice", "options": ["Low", "Moderate", "High"]},
    {"id": 29, "question": "Common stress triggers:", "type": "textarea"},
    {"id": 30, "question": "Hours of sleep per night:", "type": "number"},
    {"id": 31, "question": "Sleep quality:", "type": "choice", "options": ["Good", "Fair", "Poor"]},
    {"id": 32, "question": "Symptoms (tick all that apply):", "type": "multiselect", "options": [
        "Headaches", "Dizziness", "Blurred vision", "Chest pain", "Shortness of breath",
        "Irregular heartbeat", "Nosebleeds", "Fatigue or weakness", "Swelling in legs, ankles, or feet",
        "Difficulty sleeping", "Frequent urination at night"
    ]},
    {"id": 33, "question": "Current Blood Pressure Reading:", "type": "text"},
    {"id": 34, "question": "Heart Rate (Pulse):", "type": "number"},
    {"id": 35, "question": "Weight (kg):", "type": "number"},
    {"id": 36, "question": "Height (cm):", "type": "number"},
    {"id": 37, "question": "Body Mass Index (BMI):", "type": "text"},
    {"id": 38, "question": "Waist Circumference (cm):", "type": "number"},
    {"id": 39, "question": "What do you hope to achieve by managing your blood pressure?", "type": "textarea"},
]

WEIGHT_QUESTIONS: List[Dict[str, Any]] = [
    {"id": 1, "question": "Full Name:", "type": "text"},
    {"id": 2, "question": "Date of Birth (DD/MM/YYYY):", "type": "date"},
    {"id": 3, "question": "Age:", "type": "number"},
    {"id": 4, "question": "Gender:", "type": "choice", "options": ["Male", "Female", "Other"]},
    {"id": 5, "question": "Marital Status:", "type": "text"},
    {"id": 6, "question": "Address:", "type": "text"},
    {"id": 7, "question": "Phone Number:", "type": "text"},
    {"id": 8, "question": "Email:", "type": "email"},
    {"id": 9, "question": "Occupation:", "type": "text"},
    {"id": 10, "question": "Family history of obesity?", "type": "choice", "options": ["Yes", "No"]},
    # Only required if Q10 == "Yes"
    {"id": 11, "question": "If yes, indicate relation:", "type": "text", "required_when": {"questionId": 10, "values": ["Yes"]}},
    {"id": 12, "question": "Family history of related health conditions:", "type": "textarea"},
    {"id": 13, "question": "Personal medical history:", "type": "textarea"},
    {"id": 14, "question": "Are you currently on medication?", "type": "choice", "options": ["Yes", "No"]},
    # Only required if Q14 == "Yes"
    {"id": 15, "question": "If yes, list:", "type": "textarea", "required_when": {"questionId": 14, "values": ["Yes"]}},
    {"id": 16, "question": "Any herbal remedies, teas, or supplements used for weight management?", "type": "choice", "options": ["Yes", "No"]},
    # Only required if Q16 == "Yes"
    {"id": 17, "question": "If yes, specify:", "type": "textarea", "required_when": {"questionId": 16, "values": ["Yes"]}},
    {"id": 18, "question": "Meals per day:", "type": "number"},
    {"id": 19, "question": "Do you eat breakfast daily?", "type": "choice", "options": ["Yes", "No"]},
    {"id": 20, "question": "Portion sizes:", "type": "choice", "options": ["Small", "Moderate", "Large"]},
    {"id": 21, "question": "Snacking habits:", "type": "choice", "options": ["Rarely", "Sometimes", "Often"]},
    {"id": 22, "question": "Fast food/processed food intake:", "type": "choice", "options": ["Rarely", "Sometimes", "Often"]},
    {"id": 23, "question": "Sugary drink intake:", "type": "choice", "options": ["Rarely", "Sometimes", "Often"]},
    {"id": 24, "question": "Alcohol consumption:", "type": "choice", "options": ["None", "Occasionally", "Frequently"]},
    {"id": 25, "question": "Do you exercise regularly?", "type": "choice", "options": ["Yes", "No"]},
    # Only required if Q25 == "Yes"
    {"id": 26, "question": "If yes, what type and how often?", "type": "textarea", "required_when": {"questionId": 25, "values": ["Yes"]}},
    # Only required if Q25 == "No"
    {"id": 27, "question": "If no, main barriers:", "type": "textarea", "required_when": {"questionId": 25, "values": ["No"]}},
    {"id": 28, "question": "Smoking:", "type": "choice", "options": ["Current smoker", "Former smoker", "Never smoked"]},
    {"id": 29, "question": "Hours of sleep per night:", "type": "number"},
    {"id": 30, "question": "Sleep quality:", "type": "choice", "options": ["Good", "Fair", "Poor"]},
    {"id": 31, "question": "Daily stress:", "type": "choice", "options": ["Low", "Moderate", "High"]},
    {"id": 32, "question": "Common stress triggers:", "type": "textarea"},
    {"id": 33, "question": "Tick all that apply:", "type": "multiselect", "options": [
        "Excessive weight gain", "Difficulty losing weight", "Constant fatigue",
        "Shortness of breath", "Snoring", "Joint pain", "Swelling in legs/ankles",
        "Emotional eating", "Depression", "Low self-esteem", "Irregular menstrual cycle",
        "Erectile dysfunction"
    ]},
    {"id": 34, "question": "Current Weight (kg):", "type": "number"},
    {"id": 35, "question": "Height (cm):", "type": "number"},
    {"id": 36, "question": "Body Mass Index (BMI):", "type": "text"},
    {"id": 37, "question": "Waist Circumference (cm):", "type": "number"},
    {"id": 38, "question": "Hip Circumference (cm):", "type": "number"},
    {"id": 39, "question": "Waist-to-Hip Ratio:", "type": "text"},
    {"id": 40, "question": "Blood Pressure:", "type": "text"},
    {"id": 41, "question": "Heart Rate:", "type": "number"},
    {"id": 42, "question": "What are your main goals in managing obesity?", "type": "textarea"},
]

DETOX_QUESTIONS: List[Dict[str, Any]] = [
    {"id": 1, "question": "Full Name:", "type": "text"},
    {"id": 2, "question": "Date of Birth (DD/MM/YYYY):", "type": "date"},
    {"id": 3, "question": "Age:", "type": "number"},
    {"id": 4, "question": "Gender:", "type": "choice", "options": ["Male", "Female", "Other"]},
    {"id": 5, "question": "Marital Status:", "type": "text"},
    {"id": 6, "question": "Address:", "type": "text"},
    {"id": 7, "question": "Phone Number:", "type": "text"},
    {"id": 8, "question": "Email:", "type": "email"},
    {"id": 9, "question": "Occupation:", "type": "text"},
    {"id": 10, "question": "Do you consider yourself generally healthy?", "type": "choice", "options": ["Yes", "No"]},
    # Only required if Q10 == "No"
    {"id": 11, "question": "If no, explain:", "type": "textarea", "required_when": {"questionId": 10, "values": ["No"]}},
    {"id": 12, "question": "Family history of chronic illnesses:", "type": "textarea"},
    {"id": 13, "question": "Personal medical history:", "type": "textarea"},
    {"id": 14, "question": "Current medications or supplements:", "type": "textarea"},
    {"id": 15, "question": "Meals per day:", "type": "number"},
    {"id": 16, "question": "Water intake (glasses per day):", "type": "number"},
    {"id": 17, "question": "Fruits/vegetables:", "type": "choice", "options": ["Daily", "Occasionally", "Rarely"]},
    {"id": 18, "question": "Processed/packaged food intake:", "type": "choice", "options": ["Rarely", "Sometimes", "Often"]},
    {"id": 19, "question": "Salt intake:", "type": "choice", "options": ["Low", "Moderate", "High"]},
    {"id": 20, "question": "Sugar/sweet drinks:", "type": "choice", "options": ["Rarely", "Sometimes", "Often"]},
    {"id": 21, "question": "Alcohol:", "type": "choice", "options": ["None", "Occasionally", "Frequently"]},
    {"id": 22, "question": "Caffeine:", "type": "choice", "options": ["None", "Occasionally", "Daily"]},
    {"id": 23, "question": "Do you exercise regularly?", "type": "choice", "options": ["Yes", "No"]},
    # Only required if Q23 == "Yes"
    {"id": 24, "question": "If yes, type and frequency:", "type": "textarea", "required_when": {"questionId": 23, "values": ["Yes"]}},
    {"id": 25, "question": "Average hours of sleep:", "type": "number"},
    {"id": 26, "question": "Sleep quality:", "type": "choice", "options": ["Good", "Fair", "Poor"]},
    {"id": 27, "question": "Daily stress:", "type": "choice", "options": ["Low", "Moderate", "High"]},
    {"id": 28, "question": "Stress management methods:", "type": "textarea"},
    {"id": 29, "question": "Smoking:", "type": "choice", "options": ["Never", "Former smoker", "Current smoker"]},
    {"id": 30, "question": "Recreational drugs:", "type": "choice", "options": ["Never", "Occasionally", "Frequently"]},
    {"id": 31, "question": "Past 6 months symptoms (tick all that apply):", "type": "multiselect", "options": [
        "Fatigue", "Frequent headaches", "Digestive problems", "Skin breakouts",
        "Brain fog", "Joint or muscle aches", "Unexplained weight gain/loss",
        "Irregular menstrual cycle", "Mood swings", "Poor sleep", "Frequent colds or infections"
    ]},
    {"id": 32, "question": "Weight (kg):", "type": "number"},
    {"id": 33, "question": "Height (cm):", "type": "number"},
    {"id": 34, "question": "BMI:", "type": "text"},
    {"id": 35, "question": "Waist circumference (cm):", "type": "number"},
    {"id": 36, "question": "Blood pressure:", "type": "text"},
    {"id": 37, "question": "Resting heart rate:", "type": "number"},
    {"id": 38, "question": "What do you want to achieve with a detox & prevention plan?", "type": "textarea"},
]


def get_questions(category: str) -> List[Dict[str, Any]]:
    cat = (category or "").lower()
    if cat == "diabetes":
        return DIABETES_QUESTIONS
    if cat in ("hbp", "high blood pressure", "hypertension"):
        return HBP_QUESTIONS
    if cat in ("weight", "weight management", "obesity"):
        return WEIGHT_QUESTIONS
    if cat == "detox":
        return DETOX_QUESTIONS
    return []


def get_biodata_map(category: str) -> Dict[int, str]:
    """
    Map question IDs to biodata keys so the frontend can prefill or skip.
    Available biodata keys: full_name, email, phone, gender, marital_status,
    date_of_birth, address, occupation.
    Age is intentionally not mapped to avoid inference from DOB.
    """
    cat = (category or "").lower()
    if cat == "diabetes":
        # Q1 Full Name, Q3 Sex, Q4 DOB, Q5 Marital, Q6 Occupation, Q7 Phone, Q8 Location->address
        return {1: "full_name", 3: "gender", 4: "date_of_birth", 5: "marital_status", 6: "occupation", 7: "phone", 8: "address"}
    if cat in ("hbp", "high blood pressure", "hypertension"):
        # Q1 Full Name, Q2 DOB, Q4 Gender, Q5 Marital, Q6 Address, Q7 Phone, Q8 Email, Q9 Occupation
        return {1: "full_name", 2: "date_of_birth", 4: "gender", 5: "marital_status", 6: "address", 7: "phone", 8: "email", 9: "occupation"}
    if cat in ("weight", "weight management", "obesity"):
        # Q1 Full Name, Q2 DOB, Q4 Gender, Q5 Marital, Q6 Address, Q7 Phone, Q8 Email, Q9 Occupation
        return {1: "full_name", 2: "date_of_birth", 4: "gender", 5: "marital_status", 6: "address", 7: "phone", 8: "email", 9: "occupation"}
    if cat == "detox":
        # Q1 Full Name, Q2 DOB, Q4 Gender, Q5 Marital, Q6 Address, Q7 Phone, Q8 Email, Q9 Occupation
        return {1: "full_name", 2: "date_of_birth", 4: "gender", 5: "marital_status", 6: "address", 7: "phone", 8: "email", 9: "occupation"}
    return {}


def _get_answer_by_question_id(questions: List[Dict[str, Any]], answers: Dict[str, Any], ref_id: int):
    mapping = {q["id"]: q["question"] for q in questions}
    label = mapping.get(ref_id)
    if not label:
        return None
    return answers.get(label)


def _value_is_filled(qtype: str, val: Any) -> bool:
    if qtype in ("text", "email", "date", "textarea", "choice"):
        return isinstance(val, str) and val.strip() != ""
    if qtype == "number":
        if val in ("", None):
            return False
        try:
            float(val)
            return True
        except Exception:
            return False
    if qtype == "multiselect":
        return isinstance(val, list) and len(val) > 0
    return val is not None and val != ""


def is_required(question: Dict[str, Any], answers: Dict[str, Any], questions: List[Dict[str, Any]]) -> bool:
    """
    A question is required if:
    - it has no 'required_when' (default required), or
    - it has 'required_when' and the referenced question's answer is one of the specified values.
    Otherwise it's optional.
    """
    cond = question.get("required_when")
    if not cond:
        return True
    ref_id = cond.get("questionId")
    values = cond.get("values") or []
    ref_val = _get_answer_by_question_id(questions, answers, ref_id)
    return ref_val in values


def validate_answers(category: str, answers: Dict[str, Any]) -> List[str]:
    """
    Validates required answers for a given category using conditional logic.
    Returns a list of missing question labels.
    """
    qs = get_questions(category)
    missing: List[str] = []
    for q in qs:
        req = is_required(q, answers, qs)
        if not req:
            continue  # optional due to prior answer
        label = q["question"]
        val = answers.get(label)
        if not _value_is_filled(q.get("type", "text"), val):
            missing.append(label)
    return missing
