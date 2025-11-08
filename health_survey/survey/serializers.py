from typing import List, Optional
from rest_framework import serializers
from .models import GuestProfile, SurveySubmission, MealPlan, Category, Payment


class GuestStartSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestProfile
        fields = [
            "email",
            "full_name",
            "phone",
            "gender",
            "marital_status",
            "date_of_birth",
            "address",
            "occupation",
        ]


class SubmitAnswersSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=Category.choices)
    answers = serializers.DictField(child=serializers.JSONField())
    # For guests when unauthenticated
    email = serializers.EmailField(required=False)


class HundredMealsItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField(), required=False)


class MealPlanSerializer(serializers.ModelSerializer):
    hundred_meals = HundredMealsItemSerializer(many=True, required=False)
    selected_meal_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    assessment = serializers.JSONField(required=False)
    free_plan = serializers.JSONField(required=False)
    paid_plan = serializers.JSONField(required=False)

    class Meta:
        model = MealPlan
        fields = [
            "id",
            "email",
            "category",
            "assessment",
            "hundred_meals",
            "selected_meal_ids",
            "free_plan",
            "paid_plan",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class SelectMealsSerializer(serializers.Serializer):
    meal_plan_id = serializers.IntegerField()
    selected_meal_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)

    def validate(self, attrs):
        meal_plan_id = attrs.get("meal_plan_id")
        try:
            plan = MealPlan.objects.get(id=meal_plan_id)
        except MealPlan.DoesNotExist:
            raise serializers.ValidationError({"meal_plan_id": "Meal plan not found."})
        if not plan.hundred_meals:
            raise serializers.ValidationError("Meal options have not been generated for this plan.")
        ids = set(attrs.get("selected_meal_ids", []))
        valid_ids = {item["id"] for item in plan.hundred_meals}
        invalid = ids - valid_ids
        if invalid:
            raise serializers.ValidationError({"selected_meal_ids": f"Invalid IDs: {sorted(list(invalid))}"})
        return attrs


class UpgradeToMonthSerializer(serializers.Serializer):
    meal_plan_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=10, default="NGN")
    reference = serializers.CharField(max_length=128)

    def validate_meal_plan_id(self, value):
        if not MealPlan.objects.filter(id=value).exists():
            raise serializers.ValidationError("Meal plan not found.")
        return value


class PaystackInitSerializer(serializers.Serializer):
    meal_plan_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=10, default="NGN")
    callback_url = serializers.CharField(max_length=512, required=False, allow_blank=True)

    def validate_meal_plan_id(self, value):
        if not MealPlan.objects.filter(id=value).exists():
            raise serializers.ValidationError("Meal plan not found.")
        return value


class PaystackVerifySerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=128)
