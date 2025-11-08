from django.contrib import admin
from .models import UserProfile, GuestProfile, SurveySubmission, MealPlan, Payment, Category


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "full_name", "phone", "gender", "created_at")
    search_fields = ("user__username", "user__email", "full_name", "phone")
    list_filter = ("gender", "created_at")
    ordering = ("-created_at",)


@admin.register(GuestProfile)
class GuestProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "full_name", "phone", "gender", "created_at")
    search_fields = ("email", "full_name", "phone")
    list_filter = ("gender", "created_at")
    ordering = ("-created_at",)


@admin.register(SurveySubmission)
class SurveySubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "get_email", "category", "created_at")
    search_fields = ("guest_profile__email", "user_profile__user__email")
    list_filter = ("category", "created_at")
    ordering = ("-created_at",)

    @admin.display(description="email")
    def get_email(self, obj):
        if obj.user_profile and obj.user_profile.user and obj.user_profile.user.email:
            return obj.user_profile.user.email
        if obj.guest_profile:
            return obj.guest_profile.email
        return "-"


@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "category", "free_generated_at", "paid_generated_at", "created_at")
    search_fields = ("email",)
    list_filter = ("category", "created_at")
    ordering = ("-created_at",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "reference", "amount", "currency", "status", "meal_plan", "created_at")
    search_fields = ("reference",)
    list_filter = ("status", "currency", "created_at")
    ordering = ("-created_at",)
