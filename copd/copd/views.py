from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from django.contrib.auth.hashers import make_password


class SplashAPIView(APIView):
    """
    API endpoint for the Splash Activity.
    Returns basic application configuration and version information.
    """
    def get(self, request, *args, **kwargs):
        data = {
            'app_name': 'COPD CDSS',
            'subtitle': 'AI-Assisted Oxygen Therapy',
            'version': 'v1.0.0',
            'usage_note': 'Clinical Use Only',
            'status': 'active',
            'maintenance_mode': False
        }
        return Response(data, status=status.HTTP_200_OK)


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    role = serializers.CharField(max_length=50)
    password = serializers.CharField(write_only=True, min_length=8)


class RegisterAPIView(APIView):
    """
    POST /api/register/
    Unified signup endpoint for Doctor, Clinical Staff, and Admin.
    Body: { "full_name": "...", "email": "...", "role": "Doctor|Clinical Staff|Admin", "password": "..." }
    """
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        full_name = serializer.validated_data['full_name']
        email = serializer.validated_data['email']
        role = serializer.validated_data['role']
        password = serializer.validated_data['password']

        if role == 'Doctor':
            from doctor.models import Doctor
            if Doctor.objects.filter(email=email).exists():
                return Response({"error": "An account with this email already exists."}, status=status.HTTP_409_CONFLICT)
            Doctor.objects.create(
                name=full_name,
                email=email,
                password=password,
                is_approved=False,
                is_active=True
            )
            return Response({
                "message": "Account created successfully. Waiting for admin approval."
            }, status=status.HTTP_201_CREATED)

        elif role == 'Clinical Staff':
            from staff.models import Staff
            if Staff.objects.filter(email=email).exists():
                return Response({"error": "An account with this email already exists."}, status=status.HTTP_409_CONFLICT)
            Staff.objects.create(
                name=full_name,
                email=email,
                password=password,
                is_approved=False,
                is_active=True
            )
            return Response({
                "message": "Account created successfully. Waiting for admin approval."
            }, status=status.HTTP_201_CREATED)

        elif role == 'Admin':
            from admin_panel.models import Admin
            if Admin.objects.filter(email=email).exists():
                return Response({"error": "An admin account with this email already exists."}, status=status.HTTP_409_CONFLICT)
            Admin.objects.create(
                name=full_name,
                email=email,
                password=password,
                is_active=True
            )
            return Response({
                "message": "Admin account created successfully."
            }, status=status.HTTP_201_CREATED)

        else:
            return Response({"error": "Invalid role. Must be Doctor, Clinical Staff, or Admin."}, status=status.HTTP_400_BAD_REQUEST)
