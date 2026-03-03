from rest_framework import serializers


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(
        error_messages={"required": "Email is required.", "invalid": "Enter a valid email address."}
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        error_messages={"required": "Password is required."}
    )


class AdminSignupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, error_messages={"required": "Full name is required."})
    email = serializers.EmailField(error_messages={"required": "Email is required.", "invalid": "Enter a valid email."})
    password = serializers.CharField(
        write_only=True,
        min_length=6,
        style={'input_type': 'password'},
        error_messages={"required": "Password is required.", "min_length": "Password must be at least 6 characters."}
    )
