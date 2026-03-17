import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.conf import settings
from copd.utils import send_otp_email

from .models import Doctor, DoctorOTP
from .serializers import (
    DoctorLoginSerializer, DoctorSignupSerializer,
    ForgotPasswordSerializer, VerifyOTPSerializer, ResetPasswordSerializer
)

class DoctorLoginAPIView(APIView):
    """
    POST /api/doctor/login/
    Body: { "email": "...", "password": "..." }

    Unified auth flow:
    1. Validate credentials
    2. Check approval & active status
    3. If is_verified=0 → Generate OTP, send email, return status="otp_sent"
    4. If is_verified=1 → Return status="success" (direct login, skip OTP & Terms)
    """

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"error": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        # SELECT * FROM sandhiya.doctor WHERE email = <email>
        try:
            doctor = Doctor.objects.get(email=email)
        except Doctor.DoesNotExist:
            return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

        # Validate hashed password
        if not doctor.check_password(password):
            return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

        # Check approval status
        if not doctor.is_approved:
            return Response({
                "status": "error",
                "message": "Your account is not approved yet"
            }, status=status.HTTP_403_FORBIDDEN)

        # Check active status
        if not doctor.is_active:
            return Response({
                "status": "error",
                "message": "Your account is disabled by admin"
            }, status=status.HTTP_403_FORBIDDEN)

        # ── STEP 3: CHECK is_verified ──────────────────────────────
        if not doctor.is_verified:
            # FIRST-TIME LOGIN → OTP Required
            from django.utils import timezone

            otp = str(random.randint(100000, 999999))

            # Save OTP directly in doctor table
            doctor.otp = otp
            doctor.otp_created_at = timezone.now()
            doctor.save(update_fields=['otp', 'otp_created_at'])

            # Also save in DoctorOTP table for backward compatibility
            DoctorOTP.objects.create(email=doctor.email, otp=otp)

            # Send OTP to doctor.email using shared SMTP config
            email_sent = send_otp_email(
                recipient_email=doctor.email,
                recipient_name=doctor.name,
                otp=otp,
                role="doctor"
            )

            return Response({
                "status": "otp_sent",
                "message": "OTP sent to registered email" if email_sent else "OTP generated (email delivery failed)",
                "email": doctor.email,
                "role": "doctor",
                "otp": otp,  # Include OTP for dev/testing; remove in production
            }, status=status.HTTP_200_OK)

        else:
            # VERIFIED USER → Direct Login (skip OTP & Terms)
            return Response({
                "status": "success",
                "message": "Login successful",
                "email": doctor.email,
                "role": "doctor",
                "user_id": doctor.id,
                "name": doctor.name,
            }, status=status.HTTP_200_OK)

class DoctorSignupAPIView(APIView):

    def post(self,request):

        name=request.data.get("name")
        email=request.data.get("email")
        password=request.data.get("password")

        if Doctor.objects.filter(email=email).exists():
            return Response({"error":"Email already exists"},status=409)

        doctor=Doctor.objects.create(
            name=name,
            email=email,
            password=password,
            is_approved=False,
            is_active=True
        )

        return Response({
            "message":"Account created. Waiting for admin approval"
        },status=201)


class DoctorForgotPasswordAPIView(APIView):
    """
    POST /api/doctor/forgot-password/
    Body: { "email": "..." }
    Generates and stores a 6-digit OTP.
    """
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            if not Doctor.objects.filter(email=email).exists():
                return Response({"error": "No account found with this email."}, status=status.HTTP_404_NOT_FOUND)
            otp_code = str(random.randint(100000, 999999))
            DoctorOTP.objects.create(email=email, otp=otp_code)
            # In production, send email. For development, return OTP in response.
            return Response({
                "message": "Password reset OTP sent to your email.",
                "otp": otp_code,  # Remove in production
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DoctorVerifyOTPAPIView(APIView):
    """
    POST /api/doctor/verify-otp/
    Body: { "email": "...", "otp": "123456" }

    Verifies OTP and sets is_verified = 1 in doctor table.
    After verification, user proceeds to Terms screen (first login only).
    """
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        if not email or not otp:
            return Response({"status": "error", "message": "Email and OTP are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate OTP against doctor table first
        try:
            doctor = Doctor.objects.get(email=email)
        except Doctor.DoesNotExist:
            return Response({"status": "error", "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check OTP expiry (5 minutes)
        from django.utils import timezone
        import datetime

        if doctor.otp and doctor.otp_created_at:
            time_diff = timezone.now() - doctor.otp_created_at
            if time_diff > datetime.timedelta(minutes=5):
                # Clear expired OTP
                doctor.otp = None
                doctor.otp_created_at = None
                doctor.save(update_fields=['otp', 'otp_created_at'])
                return Response({"status": "error", "message": "OTP has expired. Please login again."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate OTP
        otp_valid = False

        # Check against doctor table's otp field
        if doctor.otp and doctor.otp == otp:
            otp_valid = True

        # Fallback: check DoctorOTP table
        if not otp_valid:
            otp_record = DoctorOTP.objects.filter(email=email, otp=otp, is_used=False).order_by('-created_at').first()
            if otp_record:
                otp_record.is_used = True
                otp_record.save()
                otp_valid = True

        if otp_valid:
            # Update doctor: set is_verified = 1, clear OTP
            doctor.is_verified = True
            doctor.otp = None
            doctor.otp_created_at = None
            doctor.save(update_fields=['is_verified', 'otp', 'otp_created_at'])

            return Response({
                "status": "success",
                "message": "OTP verified successfully",
                "verified": True,
                "role": "doctor"
            }, status=status.HTTP_200_OK)

        return Response({"status": "error", "message": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)


class DoctorResetPasswordAPIView(APIView):
    """
    POST /api/doctor/reset-password/
    Body: { "email": "...", "new_password": "..." }
    """
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            new_password = serializer.validated_data['new_password']
            try:
                doctor = Doctor.objects.get(email=email)
                doctor.password = make_password(new_password)
                doctor.save()
                return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)
            except Doctor.DoesNotExist:
                return Response({"error": "No account found with this email."}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DoctorDashboardAPIView(APIView):
    """
    GET /api/doctor/dashboard/?email=<email>
    Returns doctor name, summary counts, and needs-attention patient list.
    """
    def get(self, request):
        from patients.models import Patient, Vitals

        email = request.query_params.get('email')
        if not email:
            return Response(
                {"error": "email query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch active doctor by email
        try:
            doctor = Doctor.objects.get(email=email, is_active=True)
        except Doctor.DoesNotExist:
            return Response(
                {"error": "Doctor not found or inactive"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Build patient data with latest vitals
        patients = Patient.objects.all().exclude(full_name='Jane Doe')
        total_patients = patients.count()

        critical_count = 0
        warning_count = 0
        needs_attention = []

        for p in patients:
            latest_vital = Vitals.objects.filter(patient_id=p.id).order_by('-created_at').first()
            spo2_val = latest_vital.spo2 if latest_vital and latest_vital.spo2 is not None else None

            if spo2_val is not None:
                if spo2_val < 90:
                    critical_count += 1
                elif spo2_val <= 94:
                    warning_count += 1

                # Needs attention: spo2 < 95
                if spo2_val < 95:
                    needs_attention.append({
                        "id": p.id,
                        "name": p.full_name,
                        "room": p.bed_number,
                        "spo2": spo2_val
                    })

        # Sort by SpO2 ascending (most critical first)
        needs_attention.sort(key=lambda x: x['spo2'])

        return Response({
            "doctor": {
                "name": doctor.name
            },
            "summary": {
                "total_patients": total_patients,
                "critical": critical_count,
                "warning": warning_count
            },
            "patients": needs_attention
        }, status=status.HTTP_200_OK)


class DoctorProfileAPIView(APIView):
    """
    GET  /api/doctor/profile/?doctor_id=<id>
    POST /api/doctor/profile/  Body: { "doctor_id":..., "name":..., "phone_number":..., "specialization":... }
    """
    def get(self, request):
        doctor_id = request.query_params.get('doctor_id')
        if not doctor_id:
            return Response({"error": "doctor_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            doctor = Doctor.objects.get(id=doctor_id)
            return Response({
                "doctor_id": doctor.id,
                "name": doctor.name,
                "email": doctor.email,
                "specialization": doctor.specialization,
                "phone_number": doctor.phone_number,
                "is_approved": doctor.is_approved,
                "created_at": doctor.created_at,
            }, status=status.HTTP_200_OK)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        doctor_id = request.data.get('doctor_id')
        if not doctor_id:
            return Response({"error": "doctor_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            doctor = Doctor.objects.get(id=doctor_id)
            doctor.name = request.data.get('name', doctor.name)
            doctor.phone_number = request.data.get('phone_number', doctor.phone_number)
            doctor.specialization = request.data.get('specialization', doctor.specialization)
            doctor.save()
            return Response({"message": "Profile updated successfully."}, status=status.HTTP_200_OK)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)
