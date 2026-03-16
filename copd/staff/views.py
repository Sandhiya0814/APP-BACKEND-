import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.conf import settings

from .models import Staff, StaffOTP
from .serializers import (
    StaffLoginSerializer, StaffSignupSerializer,
    StaffForgotPasswordSerializer, StaffVerifyOTPSerializer, StaffResetPasswordSerializer
)


class StaffLoginAPIView(APIView):
    """
    POST /api/staff/login/
    Body: { "email": "...", "password": "..." }

    Fetches staff from sandhiya.staff table:
        SELECT * FROM sandhiya.staff WHERE email = <email>;
    Validates password, checks is_approved + is_active,
    generates OTP and sends it to the staff's registered email.
    """
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Email and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # SELECT * FROM sandhiya.staff WHERE email = <email>
        try:
            staff = Staff.objects.get(email=email)
        except Staff.DoesNotExist:
            return Response(
                {"error": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Validate hashed password stored in sandhiya.staff
        if not staff.check_password(password):
            return Response(
                {"error": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Check admin approval
        if not staff.is_approved:
            return Response(
                {"error": "Waiting for admin approval"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check active status (admin may disable account after approval)
        if not staff.is_active:
            return Response(
                {"error": "Your account is disabled by admin"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Generate 6-digit OTP and store in StaffOTP table
        otp = str(random.randint(100000, 999999))
        StaffOTP.objects.create(email=staff.email, otp=otp)

        # Send OTP to the staff's registered email
        try:
            subject = "Staff Login OTP"
            message = (
                f"Dear {staff.name},\n\n"
                f"Your OTP for login is {otp}.\n"
                f"It will expire in 5 minutes.\n\n"
                f"If you did not request this, please ignore this email.\n\n"
                f"CDSS COPD Team"
            )
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [staff.email],
                fail_silently=False,
            )
        except Exception as e:
            return Response(
                {"error": f"OTP generated but email could not be sent: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            "message": "Login successful. OTP sent to email",
            "staff_email": staff.email,
        }, status=status.HTTP_200_OK)

class StaffSignupAPIView(APIView):

    """
    POST /api/staff/signup/
    Body: { "name":"...", "email":"...", "password":"...", "phone_number":"...", "department":"..." }
    """
    def post(self, request):
        serializer = StaffSignupSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            if Staff.objects.filter(email=email).exists():
                return Response({"error": "An account with this email already exists."}, status=status.HTTP_409_CONFLICT)
            staff = Staff.objects.create(
                name=serializer.validated_data['name'],
                email=email,
                password=serializer.validated_data['password'],
                phone_number=serializer.validated_data.get('phone_number', ''),
                department=serializer.validated_data.get('department', ''),
                staff_role=serializer.validated_data.get('staff_role', 'Staff'),
                staff_id=serializer.validated_data.get('staff_id', ''),
                is_approved=False,
            )
            return Response({
                "message": "Account created successfully. Awaiting admin approval.",
                "staff_id": staff.id,
                "name": staff.name,
                "email": staff.email,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StaffForgotPasswordAPIView(APIView):
    """
    POST /api/staff/forgot-password/
    Body: { "email": "..." }
    """
    def post(self, request):
        serializer = StaffForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            if not Staff.objects.filter(email=email).exists():
                return Response({"error": "No account found with this email."}, status=status.HTTP_404_NOT_FOUND)
            otp_code = str(random.randint(100000, 999999))
            StaffOTP.objects.create(email=email, otp=otp_code)
            return Response({
                "message": "Password reset OTP sent to your email.",
                "otp": otp_code,  # Remove in production
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StaffVerifyOTPAPIView(APIView):
    """
    POST /api/staff/verify-otp/
    Body: { "email": "...", "otp": "123456" }
    """
    def post(self, request):
        serializer = StaffVerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            otp_record = StaffOTP.objects.filter(email=email, otp=otp, is_used=False).order_by('-created_at').first()
            if otp_record:
                otp_record.is_used = True
                otp_record.save()
                return Response({"message": "OTP verified successfully.", "verified": True}, status=status.HTTP_200_OK)
            return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StaffResetPasswordAPIView(APIView):
    """
    POST /api/staff/reset-password/
    Body: { "email": "...", "new_password": "..." }
    """
    def post(self, request):
        serializer = StaffResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            new_password = serializer.validated_data['new_password']
            try:
                staff = Staff.objects.get(email=email)
                staff.password = make_password(new_password)
                staff.save()
                return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)
            except Staff.DoesNotExist:
                return Response({"error": "No account found with this email."}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StaffDashboardAPIView(APIView):
    """
    GET /api/staff/dashboard/?staff_id=<id>
    """
    def get(self, request):
        from patients.models import Patient
        total = Patient.objects.count()
        critical = Patient.objects.filter(status='critical').count()
        warning = Patient.objects.filter(status='warning').count()
        stable = Patient.objects.filter(status='stable').count()
        recent_patients = Patient.objects.all().exclude(full_name='Jane Doe').order_by('-created_at')[:5].values(
            'id', 'full_name', 'ward', 'bed_number', 'status', 'created_at'
        )
        return Response({
            "total_patients": total,
            "critical_patients": critical,
            "warning_patients": warning,
            "stable_patients": stable,
            "recent_patients": list(recent_patients),
        }, status=status.HTTP_200_OK)


class StaffProfileAPIView(APIView):
    """
    GET  /api/staff/profile/?staff_id=<id>
    POST /api/staff/profile/  Body: { "staff_id":..., "name":..., "phone_number":..., "department":... }
    """
    def get(self, request):
        staff_id = request.query_params.get('staff_id')
        if not staff_id:
            return Response({"error": "staff_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            staff = Staff.objects.get(id=staff_id)
            return Response({
                "staff_id": staff.id,
                "name": staff.name,
                "email": staff.email,
                "department": staff.department,
                "staff_role": staff.staff_role,
                "staff_id_number": staff.staff_id,
                "phone_number": staff.phone_number,
                "is_approved": staff.is_approved,
                "created_at": staff.created_at,
            }, status=status.HTTP_200_OK)
        except Staff.DoesNotExist:
            return Response({"error": "Staff not found."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        staff_id = request.data.get('staff_id')
        if not staff_id:
            return Response({"error": "staff_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            staff = Staff.objects.get(id=staff_id)
            staff.name = request.data.get('name', staff.name)
            staff.phone_number = request.data.get('phone_number', staff.phone_number)
            staff.department = request.data.get('department', staff.department)
            staff.save()
            return Response({"message": "Profile updated successfully."}, status=status.HTTP_200_OK)
        except Staff.DoesNotExist:
            return Response({"error": "Staff not found."}, status=status.HTTP_404_NOT_FOUND)

class StaffPatientsAPIView(APIView):
    """
    GET /api/staff/patients/
    Return fields: id, name, age, ward / room, spo2, respiratory_rate, status
    """
    def get(self, request):
        from patients.models import Patient, Vitals
        from datetime import date
        patients = Patient.objects.all().exclude(full_name='Jane Doe')
        data = []
        for p in patients:
            
            # Fetch the single latest vitals record
            latest_vital = Vitals.objects.filter(patient_id=p.id).order_by('-created_at').first()
            
            spo2_val = latest_vital.spo2 if latest_vital and latest_vital.spo2 is not None else None
            spo2_str = str(spo2_val) if spo2_val is not None else "--"
            rr_str = str(latest_vital.respiratory_rate) if latest_vital and latest_vital.respiratory_rate is not None else "--"
            
            # Dynamic status based on SpO2
            if spo2_val is not None:
                if spo2_val < 88:
                    display_status = 'critical'
                elif spo2_val <= 92:
                    display_status = 'warning'
                else:
                    display_status = 'stable'
            else:
                display_status = p.status

            data.append({
                "id": p.id,
                "name": p.full_name,
                "ward_no": p.ward,
                "room_no": p.bed_number,
                "spo2": spo2_str,
                "respiratory_rate": rr_str,
                "status": display_status
            })
            
        # Sorting: Critical -> Warning -> Stable
        status_priority = {'critical': 0, 'warning': 1, 'stable': 2}
        data.sort(key=lambda x: status_priority.get(x['status'].lower(), 3))
        
        return Response(data, status=status.HTTP_200_OK)


class StaffUpdateVitalsAPIView(APIView):
    """
    PUT /api/staff/update-vitals/<patient_id>/
    """
    def put(self, request, patient_id):
        from patients.models import Vitals
        vital = Vitals.objects.filter(patient_id=patient_id).order_by('-created_at').first()
        if not vital:
            return Response({"error": "No existing vitals found to update"}, status=status.HTTP_404_NOT_FOUND)
        
        vital.spo2 = request.data.get('spo2', vital.spo2)
        vital.respiratory_rate = request.data.get('respiratory_rate', vital.respiratory_rate)
        vital.heart_rate = request.data.get('heart_rate', vital.heart_rate)
        vital.temperature = request.data.get('temperature', vital.temperature)
        vital.blood_pressure = request.data.get('blood_pressure', vital.blood_pressure)
        vital.save()
        
        return Response({"message": "Vitals updated successfully"}, status=status.HTTP_200_OK)


class StaffUpdateAbgAPIView(APIView):
    """
    PUT /api/staff/update-abg/<patient_id>/
    """
    def put(self, request, patient_id):
        from patients.models import AbgEntry
        abg = AbgEntry.objects.filter(patient_id=patient_id).order_by('-created_at').first()
        if not abg:
            return Response({"error": "No existing ABG entry found to update"}, status=status.HTTP_404_NOT_FOUND)
            
        abg.ph = request.data.get('ph', abg.ph)
        abg.pao2 = request.data.get('pao2', abg.pao2)
        abg.paco2 = request.data.get('paco2', abg.paco2)
        abg.hco3 = request.data.get('hco3', abg.hco3)
        abg.fio2 = request.data.get('fio2', abg.fio2)
        abg.save()
        
        return Response({"message": "ABG updated successfully"}, status=status.HTTP_200_OK)
