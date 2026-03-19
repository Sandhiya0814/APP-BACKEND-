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

        # Fetch pending reassessments from BOTH tables
        from therapy.models import ScheduleReassessment as ScheduleReassessmentModel
        now = timezone.now()

        reassessment_list = []

        # 1. From reassessment table (staff.models.Reassessment)
        pending_reassessments = Reassessment.objects.filter(
            status='pending'
        ).order_by('due_time')

        for r in pending_reassessments:
            try:
                patient = Patient.objects.get(id=r.patient_id)
            except Patient.DoesNotExist:
                continue

            if r.due_time:
                diff = r.due_time - now
                due_in = int(diff.total_seconds() / 60)
            else:
                due_in = 0

            reassessment_list.append({
                "id": r.id,
                "type": r.type,
                "patient_id": r.patient_id,
                "patient_name": patient.full_name,
                "bed_number": patient.bed_number,
                "ward_no": patient.ward if hasattr(patient, 'ward') else "",
                "due_in": due_in,
                "status": r.status
            })

        # 2. From schedule_reassessment table (therapy.models.ScheduleReassessment)
        # AUTO STATUS UPDATE: pending → due when scheduled_time <= NOW()
        ScheduleReassessmentModel.objects.filter(
            status='pending',
            scheduled_time__lte=now
        ).update(status='due')

        scheduled_pending = ScheduleReassessmentModel.objects.filter(
            status__in=['pending', 'due']
        ).order_by('scheduled_time')

        for sr in scheduled_pending:
            if sr.scheduled_time:
                diff = sr.scheduled_time - now
                due_in = int(diff.total_seconds() / 60)
            else:
                due_in = 0

            # Use stored patient_name/bed_no, fallback to Patient table
            p_name = sr.patient_name
            p_bed = sr.bed_no
            p_ward = sr.ward_no
            if not p_name or not p_bed:
                try:
                    patient = Patient.objects.get(id=sr.patient_id)
                    p_name = p_name or patient.full_name
                    p_bed = p_bed or patient.bed_number
                    p_ward = p_ward or patient.ward
                except Patient.DoesNotExist:
                    p_name = p_name or "Unknown"
                    p_bed = p_bed or "--"

            reassessment_list.append({
                "id": sr.id,
                "type": sr.reassessment_type,  # SpO2 or ABG
                "patient_id": sr.patient_id,
                "patient_name": p_name,
                "bed_number": p_bed,
                "ward_no": p_ward,
                "due_in": due_in,
                "status": sr.status
            })

        # Sort merged list by due_in ascending
        reassessment_list.sort(key=lambda x: x["due_in"])

        pending_count = len(reassessment_list)

        # Fetch latest completed reassessments (for dashboard display)
        completed = Reassessment.objects.filter(
            status='completed'
        ).order_by('-reassessment_time')[:10]

        latest_reassessments = []
        for r in completed:
            try:
                patient = Patient.objects.get(id=r.patient_id)
                p_name = patient.full_name
                p_bed = patient.bed_number
            except Patient.DoesNotExist:
                p_name = "Unknown"
                p_bed = "--"

            latest_reassessments.append({
                "id": r.id,
                "patient_id": r.patient_id,
                "patient_name": p_name,
                "bed_number": p_bed,
                "spo2": r.spo2,
                "respiratory_rate": r.respiratory_rate,
                "heart_rate": r.heart_rate,
                "notes": r.notes,
                "reassessment_time": r.reassessment_time.strftime("%Y-%m-%d %H:%M:%S") if r.reassessment_time else None,
            })

        return Response({
            "staff": staff_info,
            "reassessments": reassessment_list,
            "pending_count": pending_count,
            "latest_reassessments": latest_reassessments
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
        
        old_spo2 = vital.spo2  # Capture previous value before update
        vital.spo2 = request.data.get('spo2', vital.spo2)
        vital.respiratory_rate = request.data.get('respiratory_rate', vital.respiratory_rate)
        vital.heart_rate = request.data.get('heart_rate', vital.heart_rate)
        vital.temperature = request.data.get('temperature', vital.temperature)
        vital.blood_pressure = request.data.get('blood_pressure', vital.blood_pressure)
        vital.save()

        # Check for SpO2 drop and create doctor alert if needed
        new_spo2 = request.data.get('spo2')
        if new_spo2 is not None:
            try:
                from alerts.views import check_spo2_drop_and_alert
                check_spo2_drop_and_alert(patient_id, new_spo2)
            except Exception as e:
                print(f"[StaffUpdateVitals] Alert check error: {e}")

        return Response({"message": "Vitals updated successfully"}, status=status.HTTP_200_OK)


class StaffUpdateAbgAPIView(APIView):
    """
    PUT /api/staff/update-abg/<patient_id>/
    Creates a NEW AbgEntry record for each reassessment so that
    the ABG Trends graph can show how values evolve over time.
    """
    def put(self, request, patient_id):
        from patients.models import AbgEntry

        ph = request.data.get('ph')
        pao2 = request.data.get('pao2')
        paco2 = request.data.get('paco2')
        hco3 = request.data.get('hco3')
        fio2 = request.data.get('fio2')

        # Validate that at least the core fields are present
        if ph is None or paco2 is None:
            return Response(
                {"error": "ph and paco2 are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fall back to the previous entry's values for any missing fields
        prev = AbgEntry.objects.filter(patient_id=patient_id).order_by('-created_at').first()
        if prev:
            pao2 = pao2 if pao2 is not None else prev.pao2
            hco3 = hco3 if hco3 is not None else prev.hco3
            fio2 = fio2 if fio2 is not None else prev.fio2

        AbgEntry.objects.create(
            patient_id=patient_id,
            ph=float(ph),
            pao2=float(pao2) if pao2 is not None else 0,
            paco2=float(paco2),
            hco3=float(hco3) if hco3 is not None else 0,
            fio2=float(fio2) if fio2 is not None else 21,
        )

        return Response({"message": "ABG entry recorded for trend tracking"}, status=status.HTTP_201_CREATED)


class ReassessmentAPIView(APIView):
    """
    POST /api/reassessment/
    Body: { patient_id, spo2, respiratory_rate, heart_rate, notes, reassessment_time }
    Saves reassessment data into sandhiya.reassessment table.

    GET /api/reassessment/?patient_id=<id>
    Returns the latest completed reassessment for the given patient.
    """
    def post(self, request):
        from .models import Reassessment

        patient_id = request.data.get('patient_id')
        spo2 = request.data.get('spo2')
        respiratory_rate = request.data.get('respiratory_rate')
        heart_rate = request.data.get('heart_rate')
        notes = request.data.get('notes', '')
        reassessment_time = request.data.get('reassessment_time')

        # Validate required fields
        if not patient_id:
            return Response({"status": "error", "message": "patient_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if spo2 is None:
            return Response({"status": "error", "message": "spo2 is required"}, status=status.HTTP_400_BAD_REQUEST)
        if respiratory_rate is None:
            return Response({"status": "error", "message": "respiratory_rate is required"}, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone
        from datetime import datetime as dt

        # Parse reassessment_time or use current time
        if reassessment_time:
            try:
                parsed_time = dt.strptime(reassessment_time, "%Y-%m-%d %H:%M:%S")
                from django.utils.timezone import make_aware
                parsed_time = make_aware(parsed_time)
            except (ValueError, TypeError):
                parsed_time = timezone.now()
        else:
            parsed_time = timezone.now()

        try:
            patient_id_int = int(patient_id)
        except (ValueError, TypeError):
            return Response({"status": "error", "message": "Invalid patient_id"}, status=status.HTTP_400_BAD_REQUEST)

        Reassessment.objects.create(
            patient_id=patient_id_int,
            type='SpO2',
            due_time=parsed_time,
            status='completed',
            spo2=float(spo2),
            respiratory_rate=float(respiratory_rate),
            heart_rate=float(heart_rate) if heart_rate else None,
            notes=notes,
            reassessment_time=parsed_time,
        )

        return Response({
            "status": "success",
            "message": "Reassessment saved successfully"
        }, status=status.HTTP_201_CREATED)

    def get(self, request):
        from .models import Reassessment

        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response({"status": "error", "message": "patient_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            patient_id_int = int(patient_id)
        except (ValueError, TypeError):
            return Response({"status": "error", "message": "Invalid patient_id"}, status=status.HTTP_400_BAD_REQUEST)

        latest = Reassessment.objects.filter(
            patient_id=patient_id_int,
            status='completed'
        ).order_by('-reassessment_time').first()

        if not latest:
            return Response({
                "status": "error",
                "message": "No reassessment data found"
            }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "status": "success",
            "data": {
                "id": latest.id,
                "patient_id": latest.patient_id,
                "spo2": latest.spo2,
                "respiratory_rate": latest.respiratory_rate,
                "heart_rate": latest.heart_rate,
                "notes": latest.notes,
                "reassessment_time": latest.reassessment_time.strftime("%Y-%m-%d %H:%M:%S") if latest.reassessment_time else None,
            }
        }, status=status.HTTP_200_OK)


class ScheduleReassessmentAPIView(APIView):
    """
    POST /api/schedule-reassessment/
    Body: { patient_id, patient_name, bed_no, ward_no, reassessment_type, scheduled_time, scheduled_by }
    Saves to sandhiya.schedule_reassessment table.

    GET /api/schedule-reassessment/
    Returns all pending/due scheduled reassessments ordered by scheduled_time ASC.
    Also auto-updates status from 'pending' → 'due' when scheduled_time <= NOW().
    """
    def post(self, request):
        from therapy.models import ScheduleReassessment

        patient_id = request.data.get('patient_id')
        patient_name = request.data.get('patient_name', '')
        bed_no = request.data.get('bed_no', '')
        ward_no = request.data.get('ward_no', '')
        reassessment_type = request.data.get('reassessment_type', 'SpO2')
        scheduled_time_str = request.data.get('scheduled_time', '')
        reassessment_minutes = request.data.get('reassessment_minutes', 60)
        scheduled_by = request.data.get('scheduled_by', 'staff')

        if not patient_id:
            return Response({"status": "error", "message": "patient_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone
        from datetime import datetime as dt

        # Parse scheduled_time
        if scheduled_time_str:
            try:
                parsed_time = dt.strptime(scheduled_time_str, "%Y-%m-%d %H:%M:%S")
                from django.utils.timezone import make_aware
                parsed_time = make_aware(parsed_time)
            except (ValueError, TypeError):
                parsed_time = timezone.now()
        else:
            import datetime
            try:
                minutes = int(reassessment_minutes)
            except (ValueError, TypeError):
                minutes = 60
            parsed_time = timezone.now() + datetime.timedelta(minutes=minutes)

        try:
            patient_id_int = int(patient_id)
        except (ValueError, TypeError):
            return Response({"status": "error", "message": "Invalid patient_id"}, status=status.HTTP_400_BAD_REQUEST)

        # Lookup patient_name, bed_no, ward_no from Patient table if not supplied
        if not patient_name or not bed_no or not ward_no:
            from patients.models import Patient
            try:
                patient = Patient.objects.get(id=patient_id_int)
                if not patient_name:
                    patient_name = patient.full_name
                if not bed_no:
                    bed_no = patient.bed_number or ''
                if not ward_no:
                    ward_no = patient.ward or ''
            except Exception:
                pass

        ScheduleReassessment.objects.create(
            patient_id=patient_id_int,
            patient_name=patient_name,
            bed_no=bed_no,
            ward_no=ward_no,
            reassessment_type=reassessment_type,
            reassessment_minutes=int(reassessment_minutes) if reassessment_minutes else 60,
            scheduled_time=parsed_time,
            status='pending',
            scheduled_by=scheduled_by,
        )

        return Response({
            "status": "success",
            "message": "Scheduled successfully"
        }, status=status.HTTP_201_CREATED)

    def get(self, request):
        from therapy.models import ScheduleReassessment
        from django.utils import timezone

        now = timezone.now()

        # AUTO STATUS UPDATE: pending → due when scheduled_time <= NOW()
        ScheduleReassessment.objects.filter(
            status='pending',
            scheduled_time__lte=now
        ).update(status='due')

        # Fetch pending + due
        records = ScheduleReassessment.objects.filter(
            status__in=['pending', 'due']
        ).order_by('scheduled_time')

        items = []
        for r in records:
            if r.scheduled_time:
                diff = r.scheduled_time - now
                due_in = int(diff.total_seconds() / 60)
            else:
                due_in = 0

            items.append({
                "id": r.id,
                "patient_id": r.patient_id,
                "patient_name": r.patient_name,
                "bed_no": r.bed_no,
                "ward_no": r.ward_no,
                "reassessment_type": r.reassessment_type,
                "scheduled_time": r.scheduled_time.strftime("%Y-%m-%d %H:%M:%S") if r.scheduled_time else None,
                "due_in": due_in,
                "status": r.status,
                "scheduled_by": r.scheduled_by,
            })

        return Response({
            "status": "success",
            "count": len(items),
            "data": items
        }, status=status.HTTP_200_OK)


class StaffChecklistAPIView(APIView):
    """
    POST /api/staff-checklist/
    Supports TWO modes:
      1. Checklist mode (new): Body contains boolean checklist items
         { patient_id, reassessment_id, check_spo2, check_respiratory_rate,
           check_consciousness, check_device_fit, check_repeat_abg, remarks }
      2. Vitals mode (legacy): Body contains numeric vitals
         { patient_id, reassessment_id, spo2, respiratory_rate, heart_rate,
           abg_values, remarks }
    Saves data into staff_checklist table using UPSERT logic.
    Auto-updates reassessment_shedule.status = 'completed' if reassessment_id is provided.
    """
    def post(self, request):
        from .models import StaffChecklist
        from therapy.models import ScheduleReassessment

        patient_id = request.data.get('patient_id')
        reassessment_id = request.data.get('reassessment_id')
        remarks = request.data.get('remarks', '')

        if not patient_id:
            return Response({"status": "error", "message": "patient_id is required"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            patient_id_int = int(patient_id)
        except (ValueError, TypeError):
            return Response({"status": "error", "message": "Invalid patient_id"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Detect mode: checklist (boolean flags) vs vitals (numeric values)
        is_checklist_mode = any(
            request.data.get(key) is not None
            for key in ['check_spo2', 'check_respiratory_rate', 'check_consciousness',
                        'check_device_fit', 'check_repeat_abg']
        )

        spo2_val = None
        rr_val = None
        hr_val = None
        abg_values = request.data.get('abg_values', '')

        if is_checklist_mode:
            # ── Checklist mode: boolean flags ──
            check_spo2 = request.data.get('check_spo2', False)
            check_rr = request.data.get('check_respiratory_rate', False)
            check_consciousness = request.data.get('check_consciousness', False)
            check_device_fit = request.data.get('check_device_fit', False)
            check_abg = request.data.get('check_repeat_abg', False)

            # At least one must be checked
            if not any([check_spo2, check_rr, check_consciousness, check_device_fit, check_abg]):
                return Response({"status": "error", "message": "At least one checklist item must be checked"},
                                status=status.HTTP_400_BAD_REQUEST)

            # Build checklist summary for remarks if not already provided
            if not remarks:
                items = []
                if check_spo2: items.append("SpO2")
                if check_rr: items.append("Respiratory Rate")
                if check_consciousness: items.append("Consciousness/Sensorium")
                if check_device_fit: items.append("Device Fit & Position")
                if check_abg: items.append("Repeat ABG")
                remarks = "Checklist completed: " + ", ".join(items)

            print(f"[StaffChecklist] CHECKLIST MODE: patient={patient_id_int}, "
                  f"spo2={check_spo2}, rr={check_rr}, consciousness={check_consciousness}, "
                  f"device_fit={check_device_fit}, abg={check_abg}")

        else:
            # ── Vitals mode (legacy): numeric values ──
            spo2 = request.data.get('spo2')
            respiratory_rate = request.data.get('respiratory_rate')
            heart_rate = request.data.get('heart_rate')

            if spo2 is None:
                return Response({"status": "error", "message": "spo2 is required"},
                                status=status.HTTP_400_BAD_REQUEST)
            if respiratory_rate is None:
                return Response({"status": "error", "message": "respiratory_rate is required"},
                                status=status.HTTP_400_BAD_REQUEST)

            try:
                spo2_val = float(spo2)
            except (ValueError, TypeError):
                return Response({"status": "error", "message": "Invalid spo2 value"},
                                status=status.HTTP_400_BAD_REQUEST)
            if spo2_val < 0 or spo2_val > 100:
                return Response({"status": "error", "message": "SpO2 must be between 0 and 100"},
                                status=status.HTTP_400_BAD_REQUEST)

            try:
                rr_val = float(respiratory_rate)
            except (ValueError, TypeError):
                return Response({"status": "error", "message": "Invalid respiratory_rate value"},
                                status=status.HTTP_400_BAD_REQUEST)
            if rr_val < 10 or rr_val > 40:
                return Response({"status": "error", "message": "Respiratory Rate must be between 10 and 40 /min"},
                                status=status.HTTP_400_BAD_REQUEST)

            hr_val = None
            if heart_rate is not None and str(heart_rate).strip() != '':
                try:
                    hr_val = float(heart_rate)
                except (ValueError, TypeError):
                    return Response({"status": "error", "message": "Invalid heart_rate value"},
                                    status=status.HTTP_400_BAD_REQUEST)
                if hr_val < 30 or hr_val > 200:
                    return Response({"status": "error", "message": "Heart Rate must be between 30 and 200 bpm"},
                                    status=status.HTTP_400_BAD_REQUEST)

        # Parse reassessment_id
        reassessment_id_int = None
        if reassessment_id:
            try:
                reassessment_id_int = int(reassessment_id)
            except (ValueError, TypeError):
                reassessment_id_int = None

        # ── UPSERT logic: update if exists, else create ──
        created = False
        if reassessment_id_int:
            existing = StaffChecklist.objects.filter(
                reassessment_id=reassessment_id_int
            ).first()

            if existing:
                # UPDATE existing record — overwrite old values
                existing.patient_id = patient_id_int
                existing.spo2 = spo2_val
                existing.respiratory_rate = rr_val
                existing.heart_rate = hr_val
                existing.abg_values = abg_values if abg_values else ''
                existing.remarks = remarks if remarks else ''
                existing.entered_by = 'staff'
                existing.save()
                checklist = existing
                print(f"[StaffChecklist] UPDATED: id={checklist.id}, patient={patient_id_int}, "
                      f"reassessment={reassessment_id_int}")
            else:
                # INSERT new record
                checklist = StaffChecklist.objects.create(
                    patient_id=patient_id_int,
                    reassessment_id=reassessment_id_int,
                    spo2=spo2_val,
                    respiratory_rate=rr_val,
                    heart_rate=hr_val,
                    abg_values=abg_values if abg_values else '',
                    remarks=remarks if remarks else '',
                    entered_by='staff',
                )
                created = True
                print(f"[StaffChecklist] CREATED: id={checklist.id}, patient={patient_id_int}, "
                      f"reassessment={reassessment_id_int}")
        else:
            # No reassessment_id — always insert
            checklist = StaffChecklist.objects.create(
                patient_id=patient_id_int,
                reassessment_id=None,
                spo2=spo2_val,
                respiratory_rate=rr_val,
                heart_rate=hr_val,
                abg_values=abg_values if abg_values else '',
                remarks=remarks if remarks else '',
                entered_by='staff',
            )
            created = True
            print(f"[StaffChecklist] CREATED (no reassessment_id): id={checklist.id}, "
                  f"patient={patient_id_int}")

        # Auto-update BOTH schedule tables status to 'completed'
        if reassessment_id_int:
            # 1. Update reassessment_shedule (therapy.models.ScheduleReassessment)
            try:
                schedule = ScheduleReassessment.objects.get(id=reassessment_id_int)
                schedule.status = 'completed'
                schedule.save()
                print(f"[StaffChecklist] UPDATED reassessment_shedule id={reassessment_id_int} -> 'completed'")
            except ScheduleReassessment.DoesNotExist:
                print(f"[StaffChecklist] reassessment_shedule id={reassessment_id_int} NOT FOUND, trying reassessment_schedule")

            # 2. Also update reassessment_schedule (therapy.models.ReassessmentSchedule)
            try:
                from therapy.models import ReassessmentSchedule
                rs = ReassessmentSchedule.objects.get(id=reassessment_id_int)
                rs.status = 'completed'
                rs.save()
                print(f"[StaffChecklist] UPDATED reassessment_schedule id={reassessment_id_int} -> 'completed'")
            except Exception:
                print(f"[StaffChecklist] reassessment_schedule id={reassessment_id_int} NOT FOUND (ok)")

            # 3. Also update staff.models.Reassessment table if the item came from there
            try:
                from .models import Reassessment
                r_obj = Reassessment.objects.get(id=reassessment_id_int, status='pending')
                r_obj.status = 'completed'
                r_obj.save()
                print(f"[StaffChecklist] UPDATED reassessment id={reassessment_id_int} -> 'completed'")
            except Exception:
                print(f"[StaffChecklist] reassessment id={reassessment_id_int} NOT FOUND or already completed (ok)")

        # Check for SpO2 drop and create doctor alert if needed (only in vitals mode)
        if spo2_val is not None:
            try:
                from alerts.views import check_spo2_drop_and_alert
                check_spo2_drop_and_alert(patient_id_int, spo2_val)
            except Exception as e:
                print(f"[StaffChecklist] Alert check error: {e}")

        return Response({
            "status": "success",
            "message": "Reassessment checklist saved successfully",
            "checklist_id": checklist.id
        }, status=status.HTTP_201_CREATED)


class StaffReassessmentValuesAPIView(APIView):
    """
    GET /api/patient/staff-reassessments/<patient_id>/
    Returns the LATEST staff-entered reassessment values for a patient.
    Deduplicates by reassessment_id — only the most recent entry per
    reassessment_id is returned. Used by Doctor module to view staff entries.
    """
    def get(self, request, patient_id):
        from .models import StaffChecklist
        from therapy.models import ScheduleReassessment
        from patients.models import Patient

        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

        # Fetch all staff checklists for this patient, newest first
        checklists = StaffChecklist.objects.filter(
            patient_id=patient_id
        ).order_by('-created_at')

        # Deduplicate: keep only latest entry per reassessment_id
        seen_reassessment_ids = set()
        unique_entries = []

        for sc in checklists:
            key = sc.reassessment_id if sc.reassessment_id else f"no_rid_{sc.id}"
            if key in seen_reassessment_ids:
                continue
            seen_reassessment_ids.add(key)

            # Try to get linked reassessment schedule info
            schedule_info = None
            if sc.reassessment_id:
                try:
                    rs = ScheduleReassessment.objects.get(id=sc.reassessment_id)
                    schedule_info = {
                        "reassessment_type": rs.reassessment_type,
                        "scheduled_time": rs.scheduled_time.strftime("%Y-%m-%d %H:%M:%S") if rs.scheduled_time else None,
                        "scheduled_by": rs.scheduled_by,
                    }
                except ScheduleReassessment.DoesNotExist:
                    schedule_info = None

            unique_entries.append({
                "id": sc.id,
                "patient_id": sc.patient_id,
                "patient_name": patient.full_name,
                "reassessment_id": sc.reassessment_id,
                "reassessment_type": schedule_info["reassessment_type"] if schedule_info else "SpO2",
                "spo2": sc.spo2,
                "respiratory_rate": sc.respiratory_rate,
                "heart_rate": sc.heart_rate,
                "abg_values": sc.abg_values,
                "remarks": sc.remarks,
                "entered_by": sc.entered_by,
                "created_at": sc.created_at.strftime("%Y-%m-%d %H:%M:%S") if sc.created_at else None,
                "schedule_info": schedule_info,
            })

        return Response({
            "status": "success",
            "patient_id": patient_id,
            "patient_name": patient.full_name,
            "count": len(unique_entries),
            "data": unique_entries
        }, status=status.HTTP_200_OK)

