from rest_framework import serializers
from .models import *

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'department', 'is_approved', 'is_active')

class SignupSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    full_name = serializers.CharField(required=False)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role = serializers.CharField()

    def validate_email(self, value):
        user_exists = CustomUser.objects.filter(email=value).first()
        if user_exists:
            if not user_exists.is_approved:
                raise serializers.ValidationError("Your account is waiting for admin approval")
            
            # If user exists and is approved:
            role = self.initial_data.get('role', 'staff').lower()
            if 'staff' in role or 'clinical' in role:
                raise serializers.ValidationError("Email already registered. Please login or use another email.")
            else:
                raise serializers.ValidationError("Email already registered.")
                
        return value

    def create(self, validated_data):
        # Resolve name
        name = validated_data.get('name') or validated_data.get('full_name', '')
        email = validated_data['email']
        password = validated_data['password']

        # Normalize role
        raw_role = validated_data.get('role', 'staff').lower()
        if 'staff' in raw_role or 'clinical' in raw_role:
            role = 'staff'
        elif 'doctor' in raw_role or 'physician' in raw_role:
            role = 'doctor'
        else:
            role = 'staff'

        # Split full name
        parts = name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

        # 1. Create auth user in users table
        user = CustomUser.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_approved=False,
            is_active=False
        )

        # 2. Also insert into doctor or staff table
        if role == 'doctor':
            Doctor.objects.create(
                user=user,
                name=name,
                email=email,
                specialization='General',
                license_number=f'PENDING-{user.id}',
                phone='',
                status='pending'
            )
        elif role == 'staff':
            Staff.objects.create(
                user=user,
                name=name,
                email=email,
                department='General',
                license_id=f'PENDING-{user.id}',
                phone='',
                status='pending'
            )

        return user

class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ('id', 'name', 'email', 'specialization', 'license_number', 'phone', 'status')

class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = ('id', 'name', 'email', 'department', 'license_id', 'phone', 'status')

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
