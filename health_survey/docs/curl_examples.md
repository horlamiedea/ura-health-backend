# cURL Examples for Health Survey API

Base URL (dev):
```sh
BASE="http://localhost:8000"
```

Common header:
```sh
JSON="-H Content-Type:application/json"
```

Response contract:
- Success
```json
{ "status":"success", "message":"...", "data": { ... } }
```
- Error
```json
{ "status":"error", "message":"...", "errors": { "field":"details" } }
```

Environment (AI):
```sh
# required for AI endpoints to return meals/plans
export OPENAI_API_KEY="sk-xxxx"
# optional: override the default model (defaults to gpt-4.1-mini)
export OPENAI_MODEL="gpt-4.1-nano"
```

---

## Auth (JWT)

Obtain access/refresh tokens:
```sh
curl -sS -X POST "$BASE/api/auth/token/" $JSON \
  -d '{"username":"admin","password":"adminpass"}'
```

Refresh access token:
```sh
curl -sS -X POST "$BASE/api/auth/token/refresh/" $JSON \
  -d '{"refresh":"<REFRESH_TOKEN>"}'
```

Use access token in subsequent requests:
```sh
AUTH="-H Authorization:Bearer $ACCESS_TOKEN"
```

---

## Guest biodata (guest users)

Create/Update a guest profile (before answering questions):
```sh
curl -sS -X POST "$BASE/api/guest/start" $JSON \
  -d '{
    "email":"guest@example.com",
    "full_name":"Guest User",
    "phone":"+2348012345678",
    "gender":"male",
    "marital_status":"single",
    "date_of_birth":"1990-05-01",
    "address":"Lagos",
    "occupation":"Engineer"
  }'
```

Expected success:
```json
{
  "status": "success",
  "message": "Guest profile created.",
  "data": {
    "guest": { "id": 1, "email": "guest@example.com", "full_name": "Guest User" }
  }
}
```

---

## Fetch questions

Supported categories: diabetes | hbp | weight | detox

```sh
curl -sS "$BASE/api/questions?category=diabetes"
```

Possible error (invalid category):
```json
{ "status": "error", "message": "Invalid or unsupported category." }
```

---

## Submit answers and get 100 meals

Guest flow (email required):
```sh
curl -sS -X POST "$BASE/api/submit_answers" $JSON \
  -d '{
    "email":"guest@example.com",
    "category":"diabetes",
    "answers":{
      "Full Name":"Guest User",
      "Age":35,
      "Sex":"Male",
      "Do you eat late at night?":"Yes",
      "What are your main health goals?":"Weight loss"
    }
  }'
```

Authenticated flow (no email field; include token):
```sh
curl -sS -X POST "$BASE/api/submit_answers" $AUTH $JSON \
  -d '{
    "category":"weight",
    "answers":{ "Full Name":"Jane Doe", "Age":30, "Gender":"Female" }
  }'
```

Success (example):
```json
{
  "status": "success",
  "message": "Answers submitted. Meal options generated.",
  "data": {
    "meal_plan": {
      "id": 1,
      "email": "guest@example.com",
      "category": "diabetes",
      "hundred_meals": [
        { "id": 1, "name": "Oatmeal with nuts and berries", "tags": ["breakfast","fiber"] }
      ],
      "selected_meal_ids": null,
      "free_plan": null,
      "paid_plan": null,
      "created_at": "...",
      "updated_at": "..."
    }
  }
}
```

Errors:
- Missing guest email:
```json
{ "status":"error", "message":"Email is required for guests." }
```

---

## Select meals -> generate free 2-day plan

Pick 10–20 meal IDs from `hundred_meals` and send them:
```sh
curl -sS -X POST "$BASE/api/select_meals" $JSON \
  -d '{
    "meal_plan_id": 1,
    "selected_meal_ids": [1,2,3,4,5,6,7,8,9,10]
  }'
```

Success:
```json
{
  "status": "success",
  "message": "2-day free plan generated.",
  "data": {
    "meal_plan": {
      "id": 1,
      "selected_meal_ids": [1,2,3,4,5,6,7,8,9,10],
      "free_plan": {
        "days": [
          { "day": 1, "breakfast": "...", "lunch": "...", "dinner": "...", "snacks": ["..."] },
          { "day": 2, "breakfast": "...", "lunch": "...", "dinner": "...", "snacks": ["..."] }
        ]
      }
    }
  }
}
```

Error (already generated free plan):
```json
{ "status":"error", "message":"Free plan already generated for this email. Please upgrade to access the monthly plan." }
```

---

## Upgrade to 1‑month plan (after payment)

This records payment as PAID and generates a 30‑day plan:
```sh
curl -sS -X POST "$BASE/api/upgrade_to_month" $JSON \
  -d '{
    "meal_plan_id": 1,
    "amount": "5000.00",
    "currency": "NGN",
    "reference": "REF-123456"
  }'
```

Success:
```json
{
  "status": "success",
  "message": "Monthly plan unlocked.",
  "data": {
    "meal_plan": {
      "id": 1,
      "paid_plan": { "days": [ { "day":1, "breakfast":"...", "lunch":"...", "dinner":"...", "snacks":["..."] }, { "day":2, ... } ] }
    }
  }
}
```

---

## Tips

- Ensure `OPENAI_API_KEY` is set before calling AI-backed endpoints.
- Free-once rule is enforced at the select_meals (2-day plan) endpoint per email across categories when a free plan exists without a paid plan; submit_answers is not blocked and can be called multiple times per email/category.
- For authenticated users, ensure the Django `User.email` field is set; otherwise `submit_answers` will reject.
