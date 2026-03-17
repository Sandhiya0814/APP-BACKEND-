import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.conf import settings
from copd.utils import send_otp_email

from .models import Staff, StaffOTP
from .serializers import (
    StaffLoginSerializer, StaffSignupSerializer,
    StaffForgotPasswordSerializer, StaffVerifyOTPSerializer, StaffResetPasswordSerializer
)


class StaffLoginAPIView(APIView):
    """
    POST /api/staff/login/
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
            return Response({
                "status": "error",
                "message": "Your account is not approved yet"
            }, status=status.HTTP_403_FORBIDDEN)

        # Check active status (admin may disable account after approval)
        if not staff.is_active:
            return Response({
                "status": "error",
                "message": "Your account is disabled by admin"
            }, status=status.HTTP_403_FORBIDDEN)

        # ── STEP 3: CHECK is_verified ──────────────────────────────
        if not staff.is_verified:
            # FIRST-TIME LOGIN → OTP Required
            from django.utils import timezone

            otp = str(random.randint(100000, 999999))

            # Save OTP directly in staff table
            staff.otp = otp
            staff.otp_created_at = timezone.now()
            staff.save(update_fields=['otp', 'otp_created_at'])

            # Also save in StaffOTP table for backward compatibility
            StaffOTP.objects.create(email=staff.email, otp=otp)

            # Send OTP to staff.email using shared SMTP config
            email_sent = send_otp_email(
                recipient_email=staff.email,
                recipient_name=staff.name,
                otp=otp,
                role="staff"
            )

            return Response({
                "status": "otp_sent",
                "message": "OTP sent to registered email" if email_sent else "OTP generated (email delivery failed)",
                "email": staff.email,
                "role": "staff",
                "otp": otp,  # Include OTP for dev/testing; remove in production
            }, status=status.HTTP_200_OK)

        else:
            # VERIFIED USER → check terms_accepted
            if not staff.terms_accepted:
                # Terms not yet accepted → show Terms screen
                return Response({
                    "status": "terms_required",
                    "message": "Please accept Terms & Conditions",
                    "email": staff.email,
                    "role": "staff",
                }, status=status.HTTP_200_OK)
            else:
                # FULLY VERIFIED → Direct Dashboard (skip OTP & Terms)
                return Response({
                    "status": "success",
                    "message": "Login successful",
                    "email": staff.email,
                    "role": "staff",
                    "user_id": staff.id,
                    "name": staff.name,
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

    Verifies OTP and sets is_verified = 1 in staff table.
    After verification, user proceeds to Terms screen (first login only).
    """
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        if not email or not otp:
            return Response({"status": "error", "message": "Email and OTP are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate OTP against staff table first
        try:
            staff = Staff.objects.get(email=email)
        except Staff.DoesNotExist:
            return Response({"status": "error", "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check OTP expiry (5 minutes)
        from django.utils import timezone
        import datetime

        if staff.otp and staff.otp_created_at:
            time_diff = timezone.now() - staff.otp_created_at
            if time_diff > datetime.timedelta(minutes=5):
                # Clear expired OTP
                staff.otp = None
                staff.otp_created_at = None
                staff.save(update_fields=['otp', 'otp_created_at'])
                return Response({"status": "error", "message": "OTP has expired. Please login again."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate OTP
        otp_valid = False

        # Check against staff table's otp field
        if staff.otp and staff.otp == otp:
            otp_valid = True

        # Fallback: check StaffOTP table
        if not otp_valid:
            otp_record = StaffOTP.objects.filter(email=email, otp=otp, is_used=False).order_by('-created_at').first()
            if otp_record:
                otp_record.is_used = True
                otp_record.save()
                otp_valid = True

        if otp_valid:
            # Update staff: set is_verified = 1, clear OTP
            staff.is_verified = True
            staff.otp = None
            staff.otp_created_at = None
            staff.save(update_fields=['is_verified', 'otp', 'otp_created_at'])

            # Check if terms are accepted
            if not staff.terms_accepted:
                return Response({
                    "status": "terms_required",
                    "message": "OTP verified. Please accept Terms & Conditions",
                    "verified": True,
                    "role": "staff",
                    "email": staff.email,
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "status": "success",
                    "message": "Login successful",
                    "verified": True,
                    "role": "staff",
                    "email": staff.email,
                }, status=status.HTTP_200_OK)

        return Response({"status": "error", "message": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)


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
    GET /api/staff/dashboard/?email=<email>
    Returns staff info + pending reassessments from database.
    """
    def get(self, request):
        from patients.models import Patient
        from .models import Reassessment
        from django.utils import timezone

        email = request.query_params.get('email')
        if not email:
            return Response(
                {"error": "email query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch logged-in staff details
        try:
            staff = Staff.objects.get(email=email)
        except Staff.DoesNotExist:
            return Response(
                {"error": "Staff not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Build staff info (name only)
        staff_info = {
            "name": staff.name
        }

        # Fetch pending reassessments joined with patient
        now = timezone.now()
        pending_reassessments = Reassessment.objects.filter(
            status='pending'
        ).order_by('due_time')

        reassessment_list = []
        for r in pending_reassessments:
            # Get patient details
            try:
                patient = Patient.objects.get(id=r.patient_id)
            except Patient.DoesNotExist:
                continue

            # Calculate due_in in minutes (negative = overdue)
            diff = r.due_time - now
            due_in = int(diff.total_seconds() / 60)

            reassessment_list.append({
                "id": r.id,
                "type": r.type,
                "patient_name": patient.full_name,
                "bed_number": patient.bed_number,
                "due_in": due_in
            })

        pending_count = Reassessment.objects.filter(status='pending').count()

        return Response({
            "staff": staff_info,
            "reassessments": reassessment_list,
            "pending_count": pending_count
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
