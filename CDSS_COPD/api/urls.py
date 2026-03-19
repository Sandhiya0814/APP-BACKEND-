from django.urls import path
from django.http import HttpResponse
from .views import *
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Diagnostic Endpoints
    path('ping/', lambda r: HttpResponse("API is online"), name='ping'),
    path('system-statistics/', AdminDashboardStatsAPIView.as_view(), name='admin_dashboard_metrics'),
    
    # Auth
    path('doctor/signup/', SignupAPIView.as_view(), name='doctor_signup'),
    path('staff/signup/', SignupAPIView.as_view(), name='staff_signup'),
    path('doctor/login/', DoctorDirectLoginAPIView.as_view(), name='doctor_login'),
    path('staff/login/', StaffDirectLoginAPIView.as_view(), name='staff_login'),
    path('auth/signup/', SignupAPIView.as_view(), name='signup'),
    path('register/', SignupAPIView.as_view(), name='register'),  # Alias for signup
    path('auth/login/', LoginAPIView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', ProfileAPIView.as_view(), name='profile'),
    
    # Admin Panel (Classic)
    path('admin-panel/doctors/', AdminDoctorListAPIView.as_view(), name='admin_doctors'),
    path('admin-panel/doctors/<int:pk>/', AdminDoctorDetailAPIView.as_view(), name='admin_doctor_detail'),
    path('admin-panel/staff/', AdminStaffListAPIView.as_view(), name='admin_staff'),
    path('admin-panel/staff/<int:pk>/', AdminStaffDetailAPIView.as_view(), name='admin_staff_detail'),
    path('admin/approval-requests/', ApprovalRequestsAPIView.as_view(), name='admin_approval_requests'),
    path('admin/approve-user/', AdminApproveUserAPIView.as_view(), name='admin_approve_user'),
    path('admin/reject-user/', AdminRejectUserAPIView.as_view(), name='admin_reject_user'),
    path('admin/profile/', AdminProfileDetailsAPIView.as_view(), name='admin_profile_details'),

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
    
    # Admin Doctor Management API
    path('admin/doctors/', ManageDoctorListAPIView.as_view(), name='manage_doctors_list'),
    path('admin/doctors/toggle-status/', ToggleDoctorStatusByIdAPIView.as_view(), name='toggle_doctor_status_by_id'),
    path('admin/doctors/<int:pk>/', ManageDoctorDetailAPIView.as_view(), name='manage_doctor_detail_delete'),
    path('admin/doctors/<int:pk>/toggle/', ToggleDoctorStatusAPIView.as_view(), name='toggle_doctor_status'),
    
    # Admin Staff Management API
    path('admin/staff/', ManageStaffListAPIView.as_view(), name='manage_staff_list'),
    path('admin/staff/<int:pk>/', ManageStaffDetailAPIView.as_view(), name='manage_staff_detail_delete'),
    path('admin/staff/<int:pk>/toggle/', ToggleStaffStatusAPIView.as_view(), name='toggle_staff_status'),

    # Forgot / Reset Password (Doctor + Staff)
    path('forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot_password'),
    path('reset-password/<str:token>/', ResetPasswordAPIView.as_view(), name='reset_password'),

    # Universal Profile Update
    path('update-profile/', UpdateProfileAPIView.as_view(), name='update_profile'),
]
