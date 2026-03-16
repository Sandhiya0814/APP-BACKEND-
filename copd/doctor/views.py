import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.conf import settings

from .models import Doctor, DoctorOTP
from .serializers import (
    DoctorLoginSerializer, DoctorSignupSerializer,
    ForgotPasswordSerializer, VerifyOTPSerializer, ResetPasswordSerializer
)

class DoctorLoginAPIView(APIView):

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
            return Response({"error": "Waiting for admin approval"}, status=status.HTTP_403_FORBIDDEN)

        # Check active status
        if not doctor.is_active:
            return Response({"error": "Your account is disabled by admin"}, status=status.HTTP_403_FORBIDDEN)

        # Generate 6-digit OTP and store in DoctorOTP table
        otp = str(random.randint(100000, 999999))
        DoctorOTP.objects.create(email=doctor.email, otp=otp)

        # Send OTP to registered email via Django email backend
        try:
            subject = "Doctor Login OTP"
            message = (
                f"Dear Dr. {doctor.name},\n\n"
                f"Your OTP for login is {otp}.\n"
                f"It is valid for 5 minutes.\n\n"
                f"If you did not request this, please ignore this email.\n\n"
                f"CDSS COPD Team"
            )
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [doctor.email],
                fail_silently=False,
            )
        except Exception as e:
            return Response(
                {"error": f"OTP generated but email could not be sent: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            "message": "OTP sent to registered email",
            "doctor_email": doctor.email,
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
        from patients.models import Patient, Vitals
        
        patients = Patient.objects.all().exclude(full_name='Jane Doe')
        total_patients = patients.count()
        
        critical_count = 0
        warning_count = 0
        stable_count = 0
        needs_attention = []

        for p in patients:
            # Fetch latest vitals
            latest_vital = Vitals.objects.filter(patient_id=p.id).order_by('-created_at').first()
            
            spo2_val = latest_vital.spo2 if latest_vital and latest_vital.spo2 is not None else None
            rr_val = latest_vital.respiratory_rate if latest_vital and latest_vital.respiratory_rate is not None else None
            
            display_status = p.status # Default fallback
            
            if spo2_val is not None:
                if spo2_val < 88:
                    display_status = 'critical'
                    critical_count += 1
                elif spo2_val <= 92:
                    display_status = 'warning'
                    warning_count += 1
                else:
                    display_status = 'stable'
                    stable_count += 1
            else:
                # If no vitals, use the status in DB for classification in counts
                if p.status == 'critical':
                    critical_count += 1
                elif p.status == 'warning':
                    warning_count += 1
                else:
                    stable_count += 1

            # Add to Needs Attention list if Critical or Warning
            if display_status in ['critical', 'warning']:
                needs_attention.append({
                    "name": p.full_name,
                    "patient_id": p.id,
                    "room": p.bed_number,
                    "room_number": p.bed_number, # Adding both as per instructions/example
                    "spo2": spo2_val if spo2_val is not None else "--",
                    "respiratory_rate": rr_val if rr_val is not None else "--",
                    "status": display_status.upper()
                })

        return Response({
            "total_patients": total_patients,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "stable_count": stable_count,
            "needs_attention_patients": needs_attention,
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
