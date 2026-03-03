from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import *
from .serializers import *

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

# --- AUTHENTICATION & USERS ---
class SignupAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "User registered successfully, pending admin approval."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        role = request.data.get('role')

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.role != role:
                return Response({"error": "Role mismatch"}, status=status.HTTP_403_FORBIDDEN)
            if not user.is_approved and user.role != 'admin':
                return Response({"error": "Account pending approval"}, status=status.HTTP_403_FORBIDDEN)
            tokens = get_tokens_for_user(user)
            return Response({"tokens": tokens, "user": CustomUserSerializer(user).data})
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

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

class AdminStaffListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if request.user.role != 'admin': return Response(status=403)
        staff = CustomUser.objects.filter(role='staff')
        return Response(CustomUserSerializer(staff, many=True).data)

class AdminApproveUserAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, user_id):
        if request.user.role != 'admin': return Response(status=403)
        try:
            u = CustomUser.objects.get(id=user_id)
            u.is_approved = True
            u.save()
            return Response({"message": "Approved"})
        except CustomUser.DoesNotExist:
            return Response(status=404)

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
