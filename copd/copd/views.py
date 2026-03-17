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


class UnifiedLoginAPIView(APIView):
    """
    POST /api/login/
    Body: { "email": "...", "password": "...", "role": "doctor" or "staff" }

    Unified login endpoint for both Doctor and Staff.
    Response cases:
    (A) NOT APPROVED       → { "status": "error", "message": "Not approved" }
    (B) FIRST LOGIN (OTP)  → { "status": "otp_sent", "message": "OTP sent to email" }
    (C) SUCCESS LOGIN      → { "status": "success", "role": "doctor" }
    """
    def post(self, request):
        import random
        from copd.utils import send_otp_email

        email = request.data.get("email")
        password = request.data.get("password")
        role = request.data.get("role", "").lower()

        if not email or not password:
            return Response({"status": "error", "message": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        if role not in ["doctor", "staff"]:
            return Response({"status": "error", "message": "Role must be 'doctor' or 'staff'"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch user from the appropriate table
        if role == "doctor":
            from doctor.models import Doctor, DoctorOTP
            try:
                user = Doctor.objects.get(email=email)
            except Doctor.DoesNotExist:
                return Response({"status": "error", "message": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            from staff.models import Staff, StaffOTP
            try:
                user = Staff.objects.get(email=email)
            except Staff.DoesNotExist:
                return Response({"status": "error", "message": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

        # Validate password
        if not user.check_password(password):
            return Response({"status": "error", "message": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

        # Check approval
        if not user.is_approved:
            return Response({"status": "error", "message": "Your account is not approved yet"}, status=status.HTTP_403_FORBIDDEN)

        # Check active
        if not user.is_active:
            return Response({"status": "error", "message": "Your account is disabled by admin"}, status=status.HTTP_403_FORBIDDEN)

        # Check is_verified
        if not user.is_verified:
            # FIRST-TIME LOGIN → OTP
            from django.utils import timezone

            otp = str(random.randint(100000, 999999))
            user.otp = otp
            user.otp_created_at = timezone.now()
            user.save(update_fields=['otp', 'otp_created_at'])

            # Save in OTP table too
            if role == "doctor":
                DoctorOTP.objects.create(email=user.email, otp=otp)
            else:
                StaffOTP.objects.create(email=user.email, otp=otp)

            # Send OTP to user.email using shared SMTP config
            email_sent = send_otp_email(
                recipient_email=user.email,
                recipient_name=user.name,
                otp=otp,
                role=role
            )

            return Response({
                "status": "otp_sent",
                "message": "OTP sent to email" if email_sent else "OTP generated (email delivery failed)",
                "email": user.email,
                "role": role,
                "otp": otp,  # Dev/testing only; remove in production
            }, status=status.HTTP_200_OK)

        else:
            # VERIFIED USER → Direct Login
            return Response({
                "status": "success",
                "message": "Login successful",
                "email": user.email,
                "role": role,
                "user_id": user.id,
                "name": user.name,
            }, status=status.HTTP_200_OK)
