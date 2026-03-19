from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import *
from .serializers import *
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class AdminProfileDetailsAPIView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        User = get_user_model()
        try:
            admin = User.objects.get(id=7)
            return Response({
                "admin_id": admin.id,
                "username": admin.username,
                "name": admin.username,
                "email": admin.email,
                "role": "Super Admin",
                "permissions": "Full System Access"
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Admin not found"}, status=status.HTTP_404_NOT_FOUND)

# --- AUTHENTICATION & USERS ---
class SignupAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        print(f"DEBUG Signup Request Data: {request.data}")
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            print(f"DEBUG Signup Success: User {user.email} created with role {user.role}")
            return Response({"message": "Signup successful. Waiting for admin approval."}, status=status.HTTP_201_CREATED)
        
        # Pull out custom error messages if they hit validate_email logic
        if 'email' in serializer.errors and isinstance(serializer.errors['email'], list):
            return Response({"message": serializer.errors['email'][0]}, status=status.HTTP_400_BAD_REQUEST)
            
        print(f"DEBUG Signup Errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        print(f"DEBUG Login Request Data: {request.data}")
        # Accept both 'username' and 'email' as login identifiers
        username = request.data.get('username') or request.data.get('email')
        password = request.data.get('password')

        if not username or not password:
            print("ERROR Login: Missing username or password")
            return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        # First try direct username auth
        user = authenticate(username=username, password=password)

        # If that fails, try finding them by email and authenticating by their stored username
        if user is None:
            try:
                from .models import CustomUser
                user_by_email = CustomUser.objects.get(email=username)
                user = authenticate(username=user_by_email.username, password=password)
            except Exception:
                pass
        if user is None:
            print(f"ERROR Login: Invalid credentials for user {username}")
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
            
        if not user.is_active:
            print(f"ERROR Login: Account disabled for user {username}")
            return Response({"error": "Your account is waiting for admin approval"}, status=status.HTTP_403_FORBIDDEN)
            
        if not user.is_approved and user.role != 'admin':
            print(f"ERROR Login: Account not approved for user {username}")
            return Response({"error": "Your account is waiting for admin approval"}, status=status.HTTP_403_FORBIDDEN)

        # Check if doctor/staff account is disabled by admin after approval
        if user.role == 'doctor':
            try:
                doc_profile = user.doctor_profile
                if doc_profile.status == 'disabled':
                    return Response({"error": "Can't able to access. Your account is disabled by admin."}, status=status.HTTP_403_FORBIDDEN)
            except Exception:
                pass
        elif user.role == 'staff':
            try:
                staff_profile = user.staff_profile
                if staff_profile.status == 'disabled':
                    return Response({"error": "Can't able to access. Your account is disabled by admin."}, status=status.HTTP_403_FORBIDDEN)
            except Exception:
                pass
            
        tokens = get_tokens_for_user(user)
        print(f"SUCCESS Login: User {username} authenticated")
        return Response({
            "access": tokens['access'],
            "refresh": tokens['refresh'],
            "role": user.role,
            "user_id": user.id
        })

class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(CustomUserSerializer(request.user).data)
    def put(self, request):
        serializer = CustomUserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- ADMIN MODULE ---
class AdminDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if request.user.role != 'admin': return Response(status=403)
        return Response({
            "total_doctors": CustomUser.objects.filter(role='doctor').count(),
            "total_staff": CustomUser.objects.filter(role='staff').count(),
            "pending_approvals": CustomUser.objects.filter(is_approved=False).exclude(role='admin').count()
        })

class AdminDoctorListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if request.user.role != 'admin': return Response(status=403)
        doctors = CustomUser.objects.filter(role='doctor')
        return Response(CustomUserSerializer(doctors, many=True).data)

class AdminDoctorDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        if request.user.role != 'admin': return Response(status=403)
        try:
            doc = CustomUser.objects.get(id=pk, role='doctor')
            return Response(CustomUserSerializer(doc).data)
        except CustomUser.DoesNotExist:
            return Response(status=404)

class AdminStaffListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if request.user.role != 'admin': return Response(status=403)
        staff = CustomUser.objects.filter(role='staff')
        return Response(CustomUserSerializer(staff, many=True).data)

class AdminStaffDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        if request.user.role != 'admin': return Response(status=403)
        try:
            staff = CustomUser.objects.get(id=pk, role='staff')
            return Response(CustomUserSerializer(staff).data)
        except CustomUser.DoesNotExist:
            return Response(status=404)

class ApprovalRequestsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if request.user.role != 'admin': return Response(status=403)
        # Return all unapproved users (including is_active=False newly signed-up ones)
        pending_users = CustomUser.objects.filter(is_approved=False).exclude(role='admin')
        data = []
        for u in pending_users:
            profile_name = u.username
            license_val = "N/A"
            if u.role == 'doctor':
                try: 
                    doc = u.doctor_profile
                    profile_name = doc.name
                    license_val = doc.license_number
                except: pass
            elif u.role == 'staff':
                try: 
                    stf = u.staff_profile
                    profile_name = stf.name
                    license_val = stf.license_id
                except: pass
            
            data.append({
                "id": u.id,
                "name": profile_name,
                "email": u.email,
                "role": u.role,
                "user_type": u.role,
                "license": license_val,
                "status": "pending"
            })
        return Response(data)

class AdminApproveUserAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if request.user.role != 'admin': return Response(status=403)
        user_id = request.data.get('user_id')
        try:
            u = CustomUser.objects.get(id=user_id)
            u.is_approved = True
            u.is_active = True   # Activate so they can log in
            u.save()
            
            if u.role == 'doctor':
                try:
                    doc = u.doctor_profile
                    if doc:
                        doc.status = 'active'
                        doc.is_active = True # Set doctor profile to active
                        doc.save()
                except getattr(CustomUser, 'doctor_profile').RelatedObjectDoesNotExist:
                    pass
                except Exception:
                    pass
                    
            elif u.role == 'staff':
                try:
                    staff = u.staff_profile
                    if staff:
                        staff.status = 'active'
                        staff.save()
                except getattr(CustomUser, 'staff_profile').RelatedObjectDoesNotExist:
                    pass
                except Exception:
                    pass
            
            return Response({"message": "Approved"})
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

class AdminRejectUserAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if request.user.role != 'admin': return Response(status=403)
        user_id = request.data.get('user_id')
        try:
            u = CustomUser.objects.get(id=user_id)
            u.is_active = False # Rejecting effectively disables the registration
            u.save()
            if u.role == 'doctor' and hasattr(u, 'doctor_profile'):
                u.doctor_profile.status = 'rejected'
                u.doctor_profile.is_active = False # Set doctor profile to inactive
                u.doctor_profile.save()
            elif u.role == 'staff' and hasattr(u, 'staff_profile'):
                u.staff_profile.status = 'rejected'
                u.staff_profile.save()
            return Response({"message": "Rejected"})
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

# --- PATIENTS MODULE (STAFF & DOCTOR) ---
class PatientListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        patients = Patient.objects.all()
        return Response(PatientSerializer(patients, many=True).data)

    def post(self, request):
        serializer = PatientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PatientDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        try:
            p = Patient.objects.get(pk=pk)
            return Response(PatientSerializer(p).data)
        except Patient.DoesNotExist:
            return Response(status=404)

# --- CLINICAL DATA & AI EXECUTORS ---
class VitalsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        try: p = Patient.objects.get(pk=pk)
        except: return Response(status=404)
        
        serializer = VitalsSerializer(data=request.data)
        if serializer.is_valid():
            vitals = serializer.save(patient=p)
            
            # AI LOGIC: SpO2
            spo2 = vitals.spo2
            if spo2 < 88:
                Alert.objects.create(patient=p, severity='critical', message=f'Critical SpO2 Drop: {spo2}%')
                p.status = 'critical'
                # Notify Doctors
                for doc in CustomUser.objects.filter(role='doctor'):
                    Notification.objects.create(user=doc, title='Critical Alert', message=f'Patient {p.full_name} SpO2 < 88%')
            elif 88 <= spo2 <= 92:
                Alert.objects.create(patient=p, severity='warning', message=f'Warning SpO2: {spo2}%')
                p.status = 'warning'
            else:
                Alert.objects.create(patient=p, severity='normal', message=f'Normal SpO2: {spo2}%')
                p.status = 'stable'
            p.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ABGDataAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        try: p = Patient.objects.get(pk=pk)
        except: return Response(status=404)
        abg = ABGData.objects.filter(patient=p).order_by('-created_at')
        return Response(ABGDataSerializer(abg, many=True).data)

    def post(self, request, pk):
        try: p = Patient.objects.get(pk=pk)
        except: return Response(status=404)
        
        serializer = ABGDataSerializer(data=request.data)
        if serializer.is_valid():
            abg = serializer.save(patient=p)
            
            # AI LOGIC: PaCO2 > 45 -> NIV
            if abg.paco2 > 45:
                Recommendation.objects.create(
                    patient=p, 
                    rec_type='niv', 
                    content='PaCO2 > 45 mmHg detected. Recommend considering NIV.'
                )
                for doc in CustomUser.objects.filter(role='doctor'):
                    Notification.objects.create(user=doc, title='NIV Recommendation', message=f'NIV Recommended for {p.full_name}')

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SpirometryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        try: p = Patient.objects.get(pk=pk)
        except: return Response(status=404)
        
        serializer = SpirometryDataSerializer(data=request.data)
        if serializer.is_valid():
            fev1 = serializer.validated_data.get('fev1', 0)
            gold_stage = 4
            # AI LOGIC: GOLD Classification
            if fev1 >= 80: gold_stage = 1
            elif 50 <= fev1 <= 79: gold_stage = 2
            elif 30 <= fev1 <= 49: gold_stage = 3
            else: gold_stage = 4
            
            serializer.save(patient=p, gold_stage=gold_stage)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Basic CRUD implementations for remaining Models
class SymptomsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        p = Patient.objects.get(pk=pk)
        serializer = SymptomsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(patient=p)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

class BaselineDetailsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        p = Patient.objects.get(pk=pk)
        serializer = BaselineDetailsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(patient=p)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

class AlertListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        alerts = Alert.objects.all().order_by('-created_at')
        return Response(AlertSerializer(alerts, many=True).data)

class RecommendationAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        p = Patient.objects.get(pk=pk)
        recs = Recommendation.objects.filter(patient=p)
        return Response(RecommendationSerializer(recs, many=True).data)

# Doctor Overrides
class HandleRecommendationAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, rec_id):
        try:
            rec = Recommendation.objects.get(id=rec_id)
            action = request.data.get('action') # "accept" or "override"
            if action == 'override':
                rec.status = 'overridden'
                rec.override_reason = request.data.get('reason')
            else:
                rec.status = 'accepted'
            rec.save()
            return Response({"message": "Recommendation updated."})
        except Recommendation.DoesNotExist:
            return Response(status=404)

class OxygenRequirementAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        p = Patient.objects.get(pk=pk)
        serializer = OxygenRequirementSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(patient=p)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
        
class ReassessmentAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        p = Patient.objects.get(pk=pk)
        serializer = ReassessmentChecklistSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(patient=p)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

class NotificationAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        notifs = Notification.objects.filter(user=request.user)
        return Response(NotificationSerializer(notifs, many=True).data)

# --- ADMIN MANAGEMENT: DOCTOR TABLE APIs ---
class ManageDoctorListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if request.user.role != 'admin': return Response(status=status.HTTP_403_FORBIDDEN)
        # Show all approved doctors (both active and disabled) so admin can manage their status
        doctors = Doctor.objects.filter(user__is_approved=True)
        return Response(DoctorSerializer(doctors, many=True).data)

class ManageDoctorDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        if request.user.role != 'admin': return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            doc = Doctor.objects.get(id=pk)
            return Response(DoctorSerializer(doc).data)
        except Doctor.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
            
    def delete(self, request, pk):
        if request.user.role != 'admin': return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            doc = Doctor.objects.get(id=pk)
            user = doc.user
            doc.delete()
            if user:
                user.is_active = False # Revoke login access
                user.save()
            return Response({"message": "Doctor removed successfully"})
        except Doctor.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class ToggleDoctorStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, pk):
        if request.user.role != 'admin': return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            doc = Doctor.objects.get(id=pk)
            if doc.status == 'active':
                doc.status = 'disabled'
            else:
                doc.status = 'active'
            doc.save()
            
            # Sync with auth_user
            if doc.user:
                doc.user.is_active = (doc.status == 'active')
                doc.user.save()
                
            return Response({"message": "Doctor status updated successfully"})
        except Doctor.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

# POST /api/admin/doctors/toggle-status/  — accepts {doctor_id, is_active}
class ToggleDoctorStatusByIdAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if request.user.role != 'admin': return Response(status=status.HTTP_403_FORBIDDEN)
        doctor_id = request.data.get('doctor_id')
        is_active = request.data.get('is_active')
        if doctor_id is None or is_active is None:
            return Response({"error": "doctor_id and is_active are required"}, status=400)
        try:
            doc = Doctor.objects.get(id=doctor_id)
            doc.status = 'active' if is_active else 'disabled'
            doc.is_active = bool(is_active)
            doc.save()
            # Keep auth user in sync, but DON'T revoke is_approved
            if doc.user:
                doc.user.is_active = bool(is_active)
                doc.user.save()
            return Response({"message": "Doctor status updated successfully"})
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor not found"}, status=404)

# --- ADMIN MANAGEMENT: STAFF TABLE APIs ---
class ManageStaffListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if request.user.role != 'admin': return Response(status=status.HTTP_403_FORBIDDEN)
        # Show all approved staff (active + disabled) so admin can manage status
        staff = Staff.objects.filter(user__is_approved=True)
        return Response(StaffSerializer(staff, many=True).data)

class ManageStaffDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        if request.user.role != 'admin': return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            staff = Staff.objects.get(id=pk)
            return Response(StaffSerializer(staff).data)
        except Staff.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
            
    def delete(self, request, pk):
        if request.user.role != 'admin': return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            staff = Staff.objects.get(id=pk)
            user = staff.user
            staff.delete()
            if user:
                user.is_active = False # Revoke login access
                user.save()
            return Response({"message": "Staff removed successfully"})
        except Staff.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class ToggleStaffStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, pk):
        if request.user.role != 'admin': return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            staff = Staff.objects.get(id=pk)
            if staff.status == 'active':
                staff.status = 'disabled'
            else:
                staff.status = 'active'
            staff.save()
            
            # Sync with auth_user
            if staff.user:
                staff.user.is_active = (staff.status == 'active')
                staff.user.save()
                
            return Response({"message": "Staff status updated successfully"})
        except Staff.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

# --- ADMIN PANEL: Real-time Dashboard Metrics ---
class AdminDashboardStatsAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        try:
            # 1. Total Doctors from 'doctor' table
            total_doctors = Doctor.objects.count()
            
            # 2. Total Staff from 'staff' table
            total_staff = Staff.objects.count()
            
            # 3. Pending Approvals (Users where is_approved=False)
            # Excluding admin to count only registration requests
            pending_requests = CustomUser.objects.filter(
                is_approved=False
            ).exclude(role='admin').count()

            data = {
                "total_doctors": total_doctors,
                "total_staff": total_staff,
                "pending_requests": pending_requests
            }
            print(f"DEBUG Dashboard: {data}")
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"ERROR Dashboard: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─── Direct DB Login Views (read from sandhiya.staff / sandhiya.doctor) ─────

import random
from django.db import connection
from django.contrib.auth.hashers import check_password as dj_check_password
from django.core.mail import send_mail
from django.conf import settings


class StaffDirectLoginAPIView(APIView):
    """
    POST /api/staff/login/
    SELECT * FROM sandhiya.staff WHERE email = <email>;
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email    = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"error": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, email, password, is_approved, is_active FROM staff WHERE email = %s LIMIT 1",
                [email]
            )
            row = cursor.fetchone()

        if row is None:
            return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

        staff_id, name, staff_email, hashed_pw, is_approved, is_active = row

        if not dj_check_password(password, hashed_pw):
            return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

        if not is_approved:
            return Response({"error": "Waiting for admin approval"}, status=status.HTTP_403_FORBIDDEN)

        if not is_active:
            return Response({"error": "Your account is disabled by admin"}, status=status.HTTP_403_FORBIDDEN)

        otp = str(random.randint(100000, 999999))
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO staff_otp (email, otp, is_used, created_at) VALUES (%s, %s, 0, NOW())",
                [staff_email, otp]
            )

        try:
            send_mail(
                subject="Staff Login OTP",
                message=(
                    f"Dear {name},\n\n"
                    f"Your OTP for login is {otp}.\n"
                    f"It will expire in 5 minutes.\n\n"
                    f"CDSS COPD Team"
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[staff_email],
                fail_silently=False,
            )
        except Exception as e:
            return Response({"error": f"OTP generated but email could not be sent: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Login successful. OTP sent to email", "staff_email": staff_email, "name": name}, status=status.HTTP_200_OK)


class DoctorDirectLoginAPIView(APIView):
    """
    POST /api/doctor/login/
    SELECT * FROM sandhiya.doctor WHERE email = <email>;
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email    = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"error": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, email, password, is_approved, is_active FROM doctor WHERE email = %s LIMIT 1",
                [email]
            )
            row = cursor.fetchone()

        if row is None:
            return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

        doctor_id, name, doctor_email, hashed_pw, is_approved, is_active = row

        if not dj_check_password(password, hashed_pw):
            return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

        if not is_approved:
            return Response({"error": "Waiting for admin approval"}, status=status.HTTP_403_FORBIDDEN)

        if not is_active:
            return Response({"error": "Your account is disabled by admin"}, status=status.HTTP_403_FORBIDDEN)

        otp = str(random.randint(100000, 999999))
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO doctor_otp (email, otp, is_used, created_at) VALUES (%s, %s, 0, NOW())",
                [doctor_email, otp]
            )

        try:
            send_mail(
                subject="Doctor Login OTP",
                message=(
                    f"Dear Dr. {name},\n\n"
                    f"Your OTP for login is {otp}.\n"
                    f"It will expire in 5 minutes.\n\n"
                    f"CDSS COPD Team"
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[doctor_email],
                fail_silently=False,
            )
        except Exception as e:
            return Response({"error": f"OTP generated but email could not be sent: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "OTP sent to registered email", "doctor_email": doctor_email, "name": name}, status=status.HTTP_200_OK)


# ─── Forgot Password & Reset Password (Doctor + Staff) ──────────────────────

import secrets
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.hashers import make_password


# ── Change this to your actual server/tunnel URL ──────────────────────────────
SERVER_BASE_URL = "https://3dxz8qrz-8000.inc1.devtunnels.ms"


class ForgotPasswordAPIView(APIView):
    """
    POST /api/forgot-password/
    Body: { "email": "..." }

    Checks sandhiya.doctor and sandhiya.staff for the email.
    Generates a secure reset token, stores it, and emails the reset link.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Check sandhiya.doctor table
        role = None
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM doctor WHERE email = %s LIMIT 1", [email])
            if cursor.fetchone():
                role = "doctor"

        # Check sandhiya.staff table if not found in doctor
        if role is None:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM staff WHERE email = %s LIMIT 1", [email])
                if cursor.fetchone():
                    role = "staff"

        if role is None:
            # Return same message to prevent email enumeration
            return Response(
                {"message": "If that email exists, a reset link has been sent."},
                status=status.HTTP_200_OK
            )

        # Invalidate old unused tokens for this email
        from .models import PasswordResetToken
        PasswordResetToken.objects.filter(email=email, is_used=False).update(is_used=True)

        # Generate secure token (48 chars URL-safe)
        token = secrets.token_urlsafe(48)
        expires_at = timezone.now() + timedelta(minutes=30)

        PasswordResetToken.objects.create(
            email=email,
            role=role,
            token=token,
            is_used=False,
            expires_at=expires_at
        )

        reset_link = f"{SERVER_BASE_URL}/api/reset-password/{token}/"

        try:
            send_mail(
                subject="Password Reset Request",
                message=(
                    f"Hello,\n\n"
                    f"You requested a password reset for your CDSS COPD account.\n\n"
                    f"Click the link below to reset your password:\n"
                    f"{reset_link}\n\n"
                    f"This link is valid for 30 minutes.\n\n"
                    f"If you did not request this, please ignore this email.\n\n"
                    f"CDSS COPD Team"
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            return Response(
                {"error": f"Token generated but email could not be sent: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {"message": "If that email exists, a reset link has been sent."},
            status=status.HTTP_200_OK
        )


class ResetPasswordAPIView(APIView):
    """
    POST /api/reset-password/<token>/
    Body: { "new_password": "..." }

    Validates the token, identifies doctor or staff,
    and updates the password in sandhiya.doctor or sandhiya.staff.
    """
    permission_classes = [AllowAny]

    def post(self, request, token):
        new_password = request.data.get("new_password", "").strip()
        if not new_password:
            return Response({"error": "new_password is required"}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 6:
            return Response({"error": "Password must be at least 6 characters"}, status=status.HTTP_400_BAD_REQUEST)

        from .models import PasswordResetToken

        try:
            reset_token = PasswordResetToken.objects.get(token=token, is_used=False)
        except PasswordResetToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

        # Check expiry
        if timezone.now() > reset_token.expires_at:
            reset_token.is_used = True
            reset_token.save()
            return Response({"error": "Token has expired. Please request a new reset link."}, status=status.HTTP_400_BAD_REQUEST)

        # Hash the new password securely
        hashed_password = make_password(new_password)

        # Update the correct table based on role
        if reset_token.role == "doctor":
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE doctor SET password = %s WHERE email = %s",
                    [hashed_password, reset_token.email]
                )
        elif reset_token.role == "staff":
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE staff SET password = %s WHERE email = %s",
                    [hashed_password, reset_token.email]
                )

        # Mark token as used
        reset_token.is_used = True
        reset_token.save()

        return Response({"message": "Password reset successfully"}, status=status.HTTP_200_OK)


class UpdateProfileAPIView(APIView):
    """
    POST /api/update-profile/
    Body: { "email": "...", "role": "...", "name": "...", "new_email": "..." }
    Updates name (and optionally email) for doctor or staff.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        role = request.data.get("role")
        name = request.data.get("name")
        new_email = request.data.get("new_email", email)

        if not email or not role or not name:
            return Response({"error": "email, role, and name are required"}, status=400)

        if role == "doctor":
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE doctor SET name = %s, email = %s WHERE email = %s",
                    [name, new_email, email]
                )
        elif role == "staff":
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE staff SET name = %s, email = %s WHERE email = %s",
                    [name, new_email, email]
                )
        else:
            return Response({"error": "Invalid role"}, status=400)

        return Response({"message": "Profile updated successfully"}, status=200)

