import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import check_password, make_password

from .models import Doctor, DoctorOTP
from .serializers import (
    DoctorLoginSerializer, DoctorSignupSerializer,
    ForgotPasswordSerializer, VerifyOTPSerializer, ResetPasswordSerializer
)


class DoctorLoginAPIView(APIView):
    """
    POST /api/doctor/login/
    Body: { "email": "...", "password": "..." }
    """
    def post(self, request):
        serializer = DoctorLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            try:
                doctor = Doctor.objects.get(email=email)
                if not doctor.is_active:
                    return Response({"error": "Your account has been deactivated."}, status=status.HTTP_403_FORBIDDEN)
                if doctor.check_password(password):
                    return Response({
                        "message": "Login successful",
                        "role": "doctor",
                        "doctor_id": doctor.id,
                        "name": doctor.name,
                        "email": doctor.email,
                        "specialization": doctor.specialization,
                        "is_approved": doctor.is_approved,
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "Invalid password."}, status=status.HTTP_401_UNAUTHORIZED)
            except Doctor.DoesNotExist:
                return Response({"error": "No account found with this email."}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DoctorSignupAPIView(APIView):
    """
    POST /api/doctor/signup/
    Body: { "name": "...", "email": "...", "password": "...", "specialization": "...", "phone_number": "..." }
    """
    def post(self, request):
        serializer = DoctorSignupSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            if Doctor.objects.filter(email=email).exists():
                return Response({"error": "An account with this email already exists."}, status=status.HTTP_409_CONFLICT)
            doctor = Doctor.objects.create(
                name=serializer.validated_data['name'],
                email=email,
                password=serializer.validated_data['password'],
                specialization=serializer.validated_data.get('specialization', ''),
                phone_number=serializer.validated_data.get('phone_number', ''),
                is_approved=False,
            )
            return Response({
                "message": "Account created successfully. Awaiting admin approval.",
                "doctor_id": doctor.id,
                "name": doctor.name,
                "email": doctor.email,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
    """
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            otp_record = DoctorOTP.objects.filter(email=email, otp=otp, is_used=False).order_by('-created_at').first()
            if otp_record:
                otp_record.is_used = True
                otp_record.save()
                return Response({"message": "OTP verified successfully.", "verified": True}, status=status.HTTP_200_OK)
            return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
    GET /api/doctor/dashboard/?doctor_id=<id>
    Returns summary stats for the doctor dashboard.
    """
    def get(self, request):
        from patients.models import Patient
        total = Patient.objects.count()
        critical = Patient.objects.filter(status='critical').count()
        warning = Patient.objects.filter(status='warning').count()
        stable = Patient.objects.filter(status='stable').count()
        recent_patients = Patient.objects.order_by('-created_at')[:5].values(
            'id', 'full_name', 'ward', 'bed_number', 'status', 'created_at'
        )
        return Response({
            "total_patients": total,
            "critical_patients": critical,
            "warning_patients": warning,
            "stable_patients": stable,
            "recent_patients": list(recent_patients),
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
