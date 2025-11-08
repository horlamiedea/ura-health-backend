from django.db import models
from django.contrib.auth.models import User


class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"


class Category(models.TextChoices):
    DIABETES = "diabetes", "Diabetes"
    HBP = "hbp", "High Blood Pressure"
    WEIGHT = "weight", "Weight Management"
    DETOX = "detox", "Detox"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    marital_status = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)
    occupation = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"UserProfile({self.user.username})"


class GuestProfile(models.Model):
    # Guests provide biodata before starting the survey
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    marital_status = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)
    occupation = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"GuestProfile({self.email})"


class SurveySubmission(models.Model):
    """
    Stores the answers for a given category. Linked to either a UserProfile or a GuestProfile.
    """
    user_profile = models.ForeignKey(UserProfile, null=True, blank=True, on_delete=models.CASCADE, related_name="submissions")
    guest_profile = models.ForeignKey(GuestProfile, null=True, blank=True, on_delete=models.CASCADE, related_name="submissions")
    category = models.CharField(max_length=20, choices=Category.choices)
    answers = models.JSONField()  # raw answers object from the frontend
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["category", "created_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        who = self.user_profile.user.email if self.user_profile else (self.guest_profile.email if self.guest_profile else "unknown")
        return f"SurveySubmission({who}, {self.category})"


class MealPlan(models.Model):
    """
    Represents a generated meal plan workflow:
    - hundred_meals: list of 100 meals (each item recommended with id and name)
    - selected_meal_ids: list of ids chosen by the user
    - free_plan: generated 2-day plan (visible for free once per email)
    - paid_plan: generated month plan after payment
    The free-once rule is enforced by checking existing records with free_plan present and paid_plan missing for the same email.
    """
    user_profile = models.ForeignKey(UserProfile, null=True, blank=True, on_delete=models.CASCADE, related_name="meal_plans")
    guest_profile = models.ForeignKey(GuestProfile, null=True, blank=True, on_delete=models.CASCADE, related_name="meal_plans")
    # denormalized email for faster lookup and enforcing free limit
    email = models.EmailField(db_index=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    assessment = models.JSONField(null=True, blank=True)           # {"condition":"diabetes|hbp|weight|detox","level":1|2|3,"label":"mild|moderate|severe",...}

    hundred_meals = models.JSONField(null=True, blank=True)        # [{"id": 1, "name": "...", "tags": ["..."]}, ...]
    selected_meal_ids = models.JSONField(null=True, blank=True)    # [1, 5, 22, ...]
    free_plan = models.JSONField(null=True, blank=True)            # {"days": [{"day": 1, breakfast:..., ...}, {"day": 2, ...}]}
    free_generated_at = models.DateTimeField(null=True, blank=True)

    paid_plan = models.JSONField(null=True, blank=True)            # {"days": [... 30 days ...]}
    paid_generated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["email", "category", "created_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"MealPlan({self.email}, {self.category})"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    FAILED = "failed", "Failed"
    CANCELED = "canceled", "Canceled"


class Payment(models.Model):
    meal_plan = models.OneToOneField(MealPlan, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="NGN")
    reference = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    provider = models.CharField(max_length=50, blank=True)  # e.g., "paystack", "stripe"
    raw_metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Payment({self.reference}, {self.status})"
