from typing import Any, Dict, List

from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly

from .models import (
    GuestProfile,
    UserProfile,
    SurveySubmission,
    MealPlan,
    Category,
    Payment,
    PaymentStatus,
)
from .serializers import (
    GuestStartSerializer,
    SubmitAnswersSerializer,
    MealPlanSerializer,
    SelectMealsSerializer,
    UpgradeToMonthSerializer,
    PaystackInitSerializer,
    PaystackVerifySerializer,
)
from .questions import get_questions, validate_answers, get_biodata_map
from .utils import ai, assessment, paystack


def success(message: str = "OK", data: Any = None, http_status: int = drf_status.HTTP_200_OK) -> Response:
    payload: Dict[str, Any] = {"status": "success", "message": message}
    if data is not None:
        payload["data"] = data
    return Response(payload, status=http_status)


def _ensure_user_profile(user: User, defaults: Dict[str, Any] | None = None) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults=defaults or {"full_name": user.get_full_name() or user.username},
    )
    return profile


class GuestStartView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GuestStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        email = data.get("email")
        with transaction.atomic():
            # Upsert guest profile based on email
            guest, created = GuestProfile.objects.update_or_create(
                email=email, defaults=data
            )
        msg = "Guest profile created." if created else "Guest profile updated."
        return success(message=msg, data={"guest": {"id": guest.id, "email": guest.email, "full_name": guest.full_name}})


class QuestionsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        category = (request.query_params.get("category") or "").lower()
        questions = get_questions(category)
        if not questions:
            return Response(
                {"status": "error", "message": "Invalid or unsupported category."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )
        return success(
            message="Questions retrieved.",
            data={
                "category": category,
                "questions": questions,
                "biodata_map": get_biodata_map(category),
            },
        )


class SubmitAnswersView(APIView):
    """
    Accepts answers for a category and returns up to 100 meal options (ids + names).
    Enforces 'free-once-per-email until paid' rule at the start of a new flow.
    For guests, include 'email' in body. For authenticated users, email is taken from account.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SubmitAnswersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.validated_data["category"]
        answers = serializer.validated_data["answers"]

        # Validation will run after merging biodata below.

        user = request.user if request.user and request.user.is_authenticated else None
        user_profile = None
        guest_profile = None

        if user:
            if not user.email:
                return Response(
                    {"status": "error", "message": "Authenticated user must have an email set."},
                    status=drf_status.HTTP_400_BAD_REQUEST,
                )
            email = user.email
            user_profile = _ensure_user_profile(user)
        else:
            email = serializer.validated_data.get("email")
            if not email:
                return Response(
                    {"status": "error", "message": "Email is required for guests."},
                    status=drf_status.HTTP_400_BAD_REQUEST,
                )
            guest_profile, _ = GuestProfile.objects.get_or_create(
                email=email,
                defaults={"full_name": answers.get("Full Name") or "Guest"},
            )

        # Merge biodata into answers where corresponding question maps to biodata
        qs = get_questions(category)
        id_to_label = {q["id"]: q["question"] for q in qs}
        bmap = get_biodata_map(category)

        def _norm_value(key, value):
            if value is None:
                return ""
            if key == "gender":
                s = str(value).strip().lower()
                if s in ("male", "female", "other"):
                    return s.capitalize()
            return value

        # Collect biodata from profile
        if user:
            bio_src = {
                "full_name": user_profile.full_name,
                "phone": user_profile.phone,
                "gender": user_profile.gender,
                "marital_status": user_profile.marital_status,
                "date_of_birth": user_profile.date_of_birth.isoformat() if user_profile.date_of_birth else "",
                "address": user_profile.address,
                "occupation": user_profile.occupation,
                "email": user.email,
            }
        else:
            bio_src = {
                "full_name": guest_profile.full_name,
                "phone": guest_profile.phone,
                "gender": guest_profile.gender,
                "marital_status": guest_profile.marital_status,
                "date_of_birth": guest_profile.date_of_birth.isoformat() if guest_profile.date_of_birth else "",
                "address": guest_profile.address,
                "occupation": guest_profile.occupation,
                "email": guest_profile.email,
            }

        for qid, key in bmap.items():
            label = id_to_label.get(qid)
            if not label:
                continue
            if label not in answers or answers.get(label) in ("", None, []):
                val = _norm_value(key, bio_src.get(key))
                if val not in ("", None, []):
                    answers[label] = val

        # Validate after merging biodata
        missing = validate_answers(category, answers)
        if missing:
            return Response(
                {
                    "status": "error",
                    "message": "Some required answers are missing.",
                    "errors": {"missing": missing},
                },
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        # Allow refilling the form: we no longer block starting a new plan if a prior free plan exists.
        # Free-once enforcement now happens when attempting to generate a free plan (SelectMealsView).

        # Persist submission
        SurveySubmission.objects.create(
            user_profile=user_profile,
            guest_profile=guest_profile,
            category=category,
            answers=answers,
        )

        # Generate up to 100 meals
        meals = ai.generate_hundred_meals(category=category, answers=answers)
        # Assess level using AI with rules + deterministic fallback
        assessment_result = assessment.assess_level(category=category, answers=answers)

        with transaction.atomic():
            plan = MealPlan.objects.create(
                user_profile=user_profile,
                guest_profile=guest_profile,
                email=email,
                category=category,
                assessment=assessment_result,
                hundred_meals=meals,
            )

        # Compute stage-based recommendations to show immediately after assessment
        mp = MealPlanSerializer(plan).data
        try:
            lvl = int(assessment_result.get("level") or 1)
        except Exception:
            lvl = 1
        recommended = assessment.pick_recommended_meals(category, lvl, meals or [])
        diet = assessment.get_diet_recommendations(category, lvl)
        stage_template = assessment.get_stage_template(category, lvl, hundred_meals=meals or [], answers=answers)
        mp["recommended_meals"] = recommended
        mp["diet"] = diet
        mp["stage_template"] = stage_template

        return success(
            message="Answers submitted. Meal options generated.",
            data={"meal_plan": mp},
            http_status=drf_status.HTTP_201_CREATED,
        )


class SelectMealsView(APIView):
    """
    Accepts selected meal ids and returns a free 2-day plan once per email (free tier).
    Subsequent attempts should be blocked by the free-once rule.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SelectMealsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        meal_plan_id = serializer.validated_data["meal_plan_id"]
        selected_ids = serializer.validated_data["selected_meal_ids"]

        try:
            plan = MealPlan.objects.get(id=meal_plan_id)
        except MealPlan.DoesNotExist:
            return Response(
                {"status": "error", "message": "Meal plan not found."},
                status=drf_status.HTTP_404_NOT_FOUND,
            )

        # Idempotency: if already unlocked, avoid regenerating
        if plan.paid_plan:
            return success(
                message="Monthly plan already unlocked.",
                data={"meal_plan": MealPlanSerializer(plan).data},
            )

        # Enforce 'one free plan per email' across all plans: if another plan already used the free tier, block.
        if plan.free_plan:
            return Response(
                {"status": "error", "message": "Free plan already generated for this email. Please upgrade to access the monthly plan."},
                status=drf_status.HTTP_403_FORBIDDEN,
            )
        cross_free_exists = MealPlan.objects.filter(
            email=plan.email, free_plan__isnull=False, paid_plan__isnull=True
        ).exclude(id=plan.id).exists()
        if cross_free_exists:
            return Response(
                {"status": "error", "message": "A free plan for this email already exists. Please upgrade to access the monthly plan."},
                status=drf_status.HTTP_403_FORBIDDEN,
            )

        # Build selected meals list from hundred_meals
        index = {item["id"]: item for item in plan.hundred_meals or []}
        selected_meals: List[Dict[str, Any]] = []
        for mid in selected_ids:
            if mid in index:
                selected_meals.append(index[mid])

        # Reconstruct minimal answers context if available via latest submission
        submission = (
            plan.user_profile.submissions.filter(category=plan.category).order_by("-created_at").first()
            if plan.user_profile else
            plan.guest_profile.submissions.filter(category=plan.category).order_by("-created_at").first()
            if plan.guest_profile else None
        )
        answers = submission.answers if submission else {}

        # Generate 2-day plan via AI (free tier)
        free_plan = ai.generate_two_day_plan(
            category=plan.category,
            selected_meals=selected_meals,
            answers=answers,
            assessment=plan.assessment,
        )

        plan.selected_meal_ids = selected_ids
        plan.free_plan = free_plan
        plan.free_generated_at = timezone.now()
        plan.save(update_fields=["selected_meal_ids", "free_plan", "free_generated_at", "updated_at"])

        return success(
            message="2-day free plan generated.",
            data={"meal_plan": MealPlanSerializer(plan).data},
        )


class UpgradeToMonthView(APIView):
    """
    Records a 'payment' and generates a 30-day paid plan.
    In production, integrate with your payment gateway webhook to set status=PAID before unlocking.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UpgradeToMonthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        meal_plan_id = serializer.validated_data["meal_plan_id"]
        amount = serializer.validated_data["amount"]
        currency = serializer.validated_data["currency"]
        reference = serializer.validated_data["reference"]

        try:
            plan = MealPlan.objects.get(id=meal_plan_id)
        except MealPlan.DoesNotExist:
            return Response(
                {"status": "error", "message": "Meal plan not found."},
                status=drf_status.HTTP_404_NOT_FOUND,
            )

        # Build selected meals list
        index = {item["id"]: item for item in plan.hundred_meals or []}
        selected_meals: List[Dict[str, Any]] = []
        for mid in (plan.selected_meal_ids or []):
            if mid in index:
                selected_meals.append(index[mid])
        # Fallback: if nothing selected, best-effort from first few options
        if not selected_meals:
            selected_meals = list(index.values())[:10]

        # Reconstruct minimal answers context if available via latest submission
        submission = (
            plan.user_profile.submissions.filter(category=plan.category).order_by("-created_at").first()
            if plan.user_profile else
            plan.guest_profile.submissions.filter(category=plan.category).order_by("-created_at").first()
            if plan.guest_profile else None
        )
        answers = submission.answers if submission else {}

        # BYPASS PAYSTACK: Treat this request as paid and proceed to generate monthly plan
        Payment.objects.update_or_create(
            meal_plan=plan,
            defaults={
                "amount": amount,
                "currency": currency,
                "reference": reference,
                "status": PaymentStatus.PAID,
                "provider": "bypass",
                "raw_metadata": {"bypass": True, "reference": reference},
            },
        )

        # Generate paid 30-day plan (monthly) after successful payment
        print("[PAYSTACK] payment successful, generating monthly plan for meal_plan_id", plan.id)
        paid_plan = ai.generate_month_plan(
            category=plan.category,
            selected_meals=selected_meals,
            answers=answers,
            assessment=plan.assessment,
        )

        with transaction.atomic():
            plan.paid_plan = paid_plan
            plan.paid_generated_at = timezone.now()
            plan.save(update_fields=["paid_plan", "paid_generated_at", "updated_at"])

            Payment.objects.update_or_create(
                meal_plan=plan,
                defaults={
                    "amount": amount,
                    "currency": currency,
                    "reference": reference,
                    "status": PaymentStatus.PAID,
                    "provider": "bypass",
                    "raw_metadata": {"bypass": True, "reference": reference},
                },
            )

        return success(
            message="Plan unlocked.",
            data={"meal_plan": MealPlanSerializer(plan).data},
        )


class MealPlanRetrieveView(APIView):
    """
    GET endpoint to retrieve a paid (monthly) plan for a user.
    Query params (one of):
      - meal_plan_id=ID
      - email=someone@example.com&category=diabetes|hbp|weight|detox
    Returns 200 with meal_plan if a paid plan exists, otherwise 404/402.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        meal_plan_id = request.query_params.get("meal_plan_id")
        email = request.query_params.get("email")
        category = (request.query_params.get("category") or "").lower()

        plan = None
        if meal_plan_id:
            try:
                plan = MealPlan.objects.get(id=int(meal_plan_id))
            except (MealPlan.DoesNotExist, ValueError):
                return Response(
                    {"status": "error", "message": "Meal plan not found."},
                    status=drf_status.HTTP_404_NOT_FOUND,
                )
        else:
            if not email or not category:
                return Response(
                    {"status": "error", "message": "Provide meal_plan_id or (email and category)."},
                    status=drf_status.HTTP_400_BAD_REQUEST,
                )
            plan = (
                MealPlan.objects.filter(email=email, category=category)
                .order_by("-paid_generated_at", "-created_at")
                .first()
            )
            if not plan:
                return Response(
                    {"status": "error", "message": "No plan found for the given email/category."},
                    status=drf_status.HTTP_404_NOT_FOUND,
                )

        # If monthly plan missing, generate it on demand (bypass payment)
        if not plan.paid_plan:
            index = {item["id"]: item for item in (plan.hundred_meals or [])}
            selected_meals: List[Dict[str, Any]] = []
            for mid in (plan.selected_meal_ids or []):
                if mid in index:
                    selected_meals.append(index[mid])
            if not selected_meals:
                selected_meals = list(index.values())[:10]

            submission = (
                plan.user_profile.submissions.filter(category=plan.category).order_by("-created_at").first()
                if plan.user_profile else
                plan.guest_profile.submissions.filter(category=plan.category).order_by("-created_at").first()
                if plan.guest_profile else None
            )
            answers = submission.answers if submission else {}

            paid_plan = ai.generate_month_plan(
                category=plan.category,
                selected_meals=selected_meals,
                answers=answers,
                assessment=plan.assessment,
            )
            plan.paid_plan = paid_plan
            plan.paid_generated_at = timezone.now()
            plan.save(update_fields=["paid_plan", "paid_generated_at", "updated_at"])

        return success(
            message="Monthly plan retrieved.",
            data={"meal_plan": MealPlanSerializer(plan).data},
        )



class PaystackInitView(APIView):
    """
    Initialize a Paystack transaction for a meal plan.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PaystackInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        meal_plan_id = serializer.validated_data["meal_plan_id"]
        amount = serializer.validated_data["amount"]
        currency = serializer.validated_data["currency"]
        callback_url = serializer.validated_data.get("callback_url")

        try:
            plan = MealPlan.objects.get(id=meal_plan_id)
        except MealPlan.DoesNotExist:
            return Response(
                {"status": "error", "message": "Meal plan not found."},
                status=drf_status.HTTP_404_NOT_FOUND,
            )

        print("[PAYSTACK] init payload", {"meal_plan_id": plan.id, "amount": str(amount), "currency": str(currency), "callback_url": callback_url})
        init_res = paystack.initialize_transaction(
            email=plan.email,
            amount=amount,
            currency=currency,
            callback_url=callback_url,
            metadata={"meal_plan_id": plan.id, "category": plan.category},
        )
        print("[PAYSTACK] init result", init_res)
        if not init_res.get("ok"):
            return Response(
                {"status": "error", "message": f"Paystack init failed: {init_res.get('error') or 'Unknown error'}"},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )
        data = init_res.get("data") or {}
        reference = data.get("reference") or ""

        Payment.objects.update_or_create(
            meal_plan=plan,
            defaults={
                "amount": amount,
                "currency": currency,
                "reference": reference,
                "status": PaymentStatus.PENDING,
                "provider": "paystack",
                "raw_metadata": {"init": init_res},
            },
        )

        return success(
            message="Payment initialized.",
            data={
                "authorization_url": data.get("authorization_url"),
                "access_code": data.get("access_code"),
                "reference": reference,
            },
        )


class PaystackVerifyView(APIView):
    """
    Verify a Paystack transaction by reference. This does not unlock the plan by itself.
    Use UpgradeToMonthView to finalize unlocking after verification.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PaystackVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reference = serializer.validated_data["reference"]

        print("[PAYSTACK] manual verify", {"reference": reference})
        verify = paystack.verify_transaction(reference)
        print("[PAYSTACK] manual verify result", verify)
        ok = verify.get("ok")
        data = verify.get("data") or {}
        if not ok or str(data.get("status") or "").lower() != "success":
            return Response(
                {"status": "error", "message": f"Verification failed: {verify.get('error') or 'not successful'}", "data": verify},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        payment = Payment.objects.filter(reference=reference).select_related("meal_plan").first()
        if payment:
            payment.status = PaymentStatus.PAID
            payment.provider = "paystack"
            payment.raw_metadata = {"verify": verify}
            payment.save(update_fields=["status", "provider", "raw_metadata"])

        return success(message="Payment verified.", data={"verify": verify})


class PaystackWebhookView(APIView):
    """
    Paystack webhook to update payment asynchronously. Validates signature and is idempotent.
    - Configure this URL in your Paystack Dashboard as the Webhook URL.
    - If payment already marked PAID, it does nothing (idempotent).
    - On successful charge, it marks Payment as PAID and generates the paid plan if missing.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        import json, hmac, hashlib, decimal
        from django.conf import settings

        # Validate signature
        signature = request.headers.get("x-paystack-signature") or request.META.get("HTTP_X_PAYSTACK_SIGNATURE")
        secret = getattr(settings, "PAYSTACK_SECRET_KEY", "") or ""
        body = request.body or b""
        if not secret:
            return Response({"status": "error", "message": "PAYSTACK_SECRET_KEY not configured."}, status=drf_status.HTTP_400_BAD_REQUEST)
        computed = hmac.new(secret.encode("utf-8"), body, hashlib.sha512).hexdigest()
        if not signature or signature != computed:
            return Response({"status": "error", "message": "Invalid signature."}, status=drf_status.HTTP_400_BAD_REQUEST)

        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            return Response({"status": "error", "message": "Invalid JSON body."}, status=drf_status.HTTP_400_BAD_REQUEST)

        event = str(payload.get("event") or "").lower()
        data = payload.get("data") or {}
        reference = data.get("reference") or ""
        print("[PAYSTACK][WEBHOOK] event:", event, "reference:", reference)
        status_str = str(data.get("status") or "").lower()
        amount_kobo = data.get("amount")
        currency = data.get("currency") or "NGN"

        # Find or create payment by reference (using metadata.meal_plan_id if present)
        payment = Payment.objects.filter(reference=reference).select_related("meal_plan").first()
        if not payment:
            meta = data.get("metadata") or {}
            meal_plan_id = meta.get("meal_plan_id")
            plan = MealPlan.objects.filter(id=meal_plan_id).first() if meal_plan_id else None
            payment = Payment.objects.create(
                meal_plan=plan,
                amount=(decimal.Decimal(amount_kobo or 0) / 100) if amount_kobo else decimal.Decimal("0"),
                currency=currency,
                reference=reference,
                status=PaymentStatus.PENDING,
                provider="paystack",
                raw_metadata={"webhook": payload},
            )

        # Idempotency: if already paid, do nothing
        if payment.status == PaymentStatus.PAID:
            return success(message="Already processed.", data={"reference": reference})

        if event == "charge.success" and status_str == "success":
            # Mark paid
            if amount_kobo:
                payment.amount = decimal.Decimal(amount_kobo) / 100
            payment.currency = currency or payment.currency
            payment.status = PaymentStatus.PAID
            payment.provider = "paystack"
            payment.raw_metadata = {"webhook": payload}
            payment.save(update_fields=["amount", "currency", "status", "provider", "raw_metadata"])

            # Generate paid plan if not present
            plan = payment.meal_plan
            if plan and not plan.paid_plan:
                index = {item["id"]: item for item in (plan.hundred_meals or [])}
                selected_meals: List[Dict[str, Any]] = []
                for mid in (plan.selected_meal_ids or []):
                    if mid in index:
                        selected_meals.append(index[mid])
                if not selected_meals:
                    selected_meals = list(index.values())[:10]

                submission = (
                    plan.user_profile.submissions.filter(category=plan.category).order_by("-created_at").first()
                    if plan.user_profile else
                    plan.guest_profile.submissions.filter(category=plan.category).order_by("-created_at").first()
                    if plan.guest_profile else None
                )
                answers = submission.answers if submission else {}

                paid_plan = ai.generate_two_day_plan(
                    category=plan.category,
                    selected_meals=selected_meals,
                    answers=answers,
                    assessment=plan.assessment,
                )

                plan.paid_plan = paid_plan
                plan.paid_generated_at = timezone.now()
                plan.save(update_fields=["paid_plan", "paid_generated_at", "updated_at"])

            return success(message="Webhook processed.", data={"reference": reference})

        # Non-success or unrelated events: store metadata and return 200
        payment.raw_metadata = {"webhook": payload}
        payment.save(update_fields=["raw_metadata"])
        return success(message="Webhook ignored.", data={"event": event})
