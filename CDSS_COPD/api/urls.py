from django.urls import path
from .views import *
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Auth
    path('auth/signup/', SignupAPIView.as_view(), name='signup'),
    path('auth/login/', LoginAPIView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', ProfileAPIView.as_view(), name='profile'),
    
    # Admin
    path('admin-panel/dashboard/', AdminDashboardAPIView.as_view(), name='admin_dashboard'),
    path('admin-panel/doctors/', AdminDoctorListAPIView.as_view(), name='admin_doctors'),
    path('admin-panel/staff/', AdminStaffListAPIView.as_view(), name='admin_staff'),
    path('admin-panel/approve/<int:user_id>/', AdminApproveUserAPIView.as_view(), name='admin_approve'),

    # Patients (Staff & Doctor)
    path('patients/', PatientListCreateAPIView.as_view(), name='patients_list_create'),
    path('patients/<int:pk>/', PatientDetailAPIView.as_view(), name='patient_detail'),
    
    # Clinical Data
    path('patients/<int:pk>/symptoms/', SymptomsAPIView.as_view(), name='patient_symptoms'),
    path('patients/<int:pk>/baseline/', BaselineDetailsAPIView.as_view(), name='patient_baseline'),
    path('patients/<int:pk>/vitals/', VitalsAPIView.as_view(), name='patient_vitals'),
    path('patients/<int:pk>/abg/', ABGDataAPIView.as_view(), name='patient_abg'),
    path('patients/<int:pk>/spirometry/', SpirometryAPIView.as_view(), name='patient_spirometry'),
    path('patients/<int:pk>/oxygen-req/', OxygenRequirementAPIView.as_view(), name='patient_oxygen_req'),
    path('patients/<int:pk>/reassessment/', ReassessmentAPIView.as_view(), name='patient_reassessment'),

    # Doctor Alerts & Recommendations
    path('alerts/', AlertListAPIView.as_view(), name='alerts_list'),
    path('patients/<int:pk>/recommendations/', RecommendationAPIView.as_view(), name='patient_recommendations'),
    path('recommendations/<int:rec_id>/handle/', HandleRecommendationAPIView.as_view(), name='handle_recommendation'),
    path('notifications/', NotificationAPIView.as_view(), name='notifications'),
]
