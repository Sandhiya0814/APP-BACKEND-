from rest_framework import serializers
from .models import *

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'department', 'is_approved')

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password', 'first_name', 'last_name', 'role', 'phone_number', 'department')

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role=validated_data.get('role', 'staff'),
            phone_number=validated_data.get('phone_number', ''),
            department=validated_data.get('department', ''),
            is_approved=False
        )
        return user

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = '__all__'

class SymptomsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Symptoms
        fields = '__all__'

class BaselineDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineDetails
        fields = '__all__'

class SpirometryDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpirometryData
        fields = '__all__'

class ABGDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ABGData
        fields = '__all__'

class VitalsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vitals
        fields = '__all__'

class OxygenRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = OxygenRequirement
        fields = '__all__'

class RecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = '__all__'

class DeviceSelectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceSelection
        fields = '__all__'

class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = '__all__'

class ReassessmentScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReassessmentSchedule
        fields = '__all__'

class ReassessmentChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReassessmentChecklist
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
