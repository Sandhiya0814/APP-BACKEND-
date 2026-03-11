from rest_framework import serializers


class DoctorLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(
        error_messages={"required": "Email is required.", "invalid": "Enter a valid email address."}
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        error_messages={"required": "Password is required."}
    )


class DoctorSignupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, error_messages={"required": "Full name is required."})
    email = serializers.EmailField(error_messages={"required": "Email is required.", "invalid": "Enter a valid email."})
    password = serializers.CharField(
        write_only=True,
        min_length=6,
        style={'input_type': 'password'},
        error_messages={"required": "Password is required.", "min_length": "Password must be at least 6 characters."}
    )
    specialization = serializers.CharField(max_length=255, required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    license_number = serializers.CharField(max_length=100, required=False, allow_blank=True)


class DoctorListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    specialization = serializers.CharField()
    license_number = serializers.CharField()
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return "active" if obj.is_active else "disabled"


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(error_messages={"required": "Email is required.", "invalid": "Enter a valid email."})


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(error_messages={"required": "Email is required."})
    otp = serializers.CharField(max_length=6, error_messages={"required": "OTP is required."})


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(error_messages={"required": "Email is required."})
    new_password = serializers.CharField(
        write_only=True,
        min_length=6,
        error_messages={"required": "New password is required.", "min_length": "Password must be at least 6 characters."}
    )
class DoctorDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.EmailField()
    specialization = serializers.CharField()
    license_number = serializers.CharField()
    phone = serializers.CharField(source='phone_number')
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return "active" if obj.is_active else "disabled"
