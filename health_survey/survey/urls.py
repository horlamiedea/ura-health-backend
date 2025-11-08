from django.urls import path
from .views import (
    GuestStartView,
    QuestionsView,
    SubmitAnswersView,
    SelectMealsView,
    UpgradeToMonthView,
    MealPlanRetrieveView,
    PaystackInitView,
    PaystackVerifyView,
    PaystackWebhookView,
)

urlpatterns = [
    path("guest/start", GuestStartView.as_view(), name="guest-start"),
    path("questions", QuestionsView.as_view(), name="questions"),
    path("submit_answers", SubmitAnswersView.as_view(), name="submit-answers"),
    path("select_meals", SelectMealsView.as_view(), name="select-meals"),
    path("upgrade_to_month", UpgradeToMonthView.as_view(), name="upgrade-to-month"),
    path("meal_plan", MealPlanRetrieveView.as_view(), name="meal-plan-retrieve"),
    path("paystack/init", PaystackInitView.as_view(), name="paystack-init"),
    path("paystack/verify", PaystackVerifyView.as_view(), name="paystack-verify"),
    path("paystack/webhook", PaystackWebhookView.as_view(), name="paystack-webhook"),
]
