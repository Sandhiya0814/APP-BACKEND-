from django.contrib import admin
from django.urls import path

# Splash
from copd.views import SplashAPIView, RegisterAPIView

# Doctor
from doctor.views import *

# Staff
from staff.views import (
    StaffLoginAPIView, StaffSignupAPIView,
    StaffForgotPasswordAPIView, StaffVerifyOTPAPIView,
    StaffResetPasswordAPIView, StaffDashboardAPIView, StaffProfileAPIView
)

# Admin Panel
from admin_panel.views import (
    AdminLoginAPIView, AdminDashboardAPIView,
    AdminProfileAPIView, AdminProfileDetailsAPIView, AdminManageDoctorsAPIView, AdminRemoveDoctorAPIView,
    AdminManageStaffAPIView, AdminRemoveStaffAPIView,
    AdminApprovalsAPIView, AdminApproveRequestAPIView, AdminRejectRequestAPIView,
    AdminApprovalRequestsListAPIView, AdminApproveUserAPIView, AdminRejectUserAPIView,
    AdminDoctorListAPIView, AdminDoctorToggleAPIView, AdminDoctorDetailAPIView, AdminDoctorToggleStatusAPIView,
    AdminStaffListAPIView, AdminStaffToggleStatusAPIView, AdminStaffDetailAPIView,
    AdminSystemStatisticsAPIView
)

# Patients
from patients.views import (
    AddPatientAPIView, PatientListAPIView, PatientDetailAPIView,
    BaselineDetailsAPIView, GoldClassificationAPIView, SpirometryDataAPIView,
    GasExchangeHistoryAPIView, CurrentSymptomsAPIView, VitalsAPIView,
    ABGEntryAPIView, ReassessmentChecklistAPIView
)

# Therapy
from therapy.views import (
    OxygenStatusAPIView, AIAnalysisAPIView, ABGTrendsAPIView,
    TrendAnalysisAPIView, HypoxemiaCauseAPIView, OxygenRequirementAPIView,
    DeviceSelectionAPIView, ReviewRecommendationAPIView,
    TherapyRecommendationAPIView, NIVRecommendationAPIView,
    EscalationCriteriaAPIView, ScheduleReassessmentAPIView, UrgentActionAPIView
)

# Alerts
from alerts.views import DoctorAlertsAPIView, StaffAlertsAPIView, NotificationsAPIView

# Settings App
from settings_app.views import SettingsAPIView, ClinicalGuidelinesAPIView, HelpSupportAPIView

urlpatterns = [
    path('admin/', admin.site.urls),

    # ──────────────────────────────────────────────────
    # Splash
    # ──────────────────────────────────────────────────
    path('api/splash/', SplashAPIView.as_view(), name='splash'),
    path('api/register/', RegisterAPIView.as_view(), name='register'),

    # ──────────────────────────────────────────────────
    # Doctor Auth
    # ──────────────────────────────────────────────────
    path('api/doctor/login/', DoctorLoginAPIView.as_view(), name='doctor-login'),
    path('api/doctor/signup/', DoctorSignupAPIView.as_view(), name='doctor-signup'),
    path('api/doctor/forgot-password/', DoctorForgotPasswordAPIView.as_view(), name='doctor-forgot-password'),
    path('api/doctor/verify-otp/', DoctorVerifyOTPAPIView.as_view(), name='doctor-verify-otp'),
    path('api/doctor/reset-password/', DoctorResetPasswordAPIView.as_view(), name='doctor-reset-password'),
    path('api/doctor/dashboard/', DoctorDashboardAPIView.as_view(), name='doctor-dashboard'),
    path('api/doctor/profile/', DoctorProfileAPIView.as_view(), name='doctor-profile'),
    path('api/doctor/alerts/', DoctorAlertsAPIView.as_view(), name='doctor-alerts'),

    # ──────────────────────────────────────────────────
    # Staff Auth
    # ──────────────────────────────────────────────────
    path('api/staff/login/', StaffLoginAPIView.as_view(), name='staff-login'),
    path('api/staff/signup/', StaffSignupAPIView.as_view(), name='staff-signup'),
    path('api/staff/forgot-password/', StaffForgotPasswordAPIView.as_view(), name='staff-forgot-password'),
    path('api/staff/verify-otp/', StaffVerifyOTPAPIView.as_view(), name='staff-verify-otp'),
    path('api/staff/reset-password/', StaffResetPasswordAPIView.as_view(), name='staff-reset-password'),
    path('api/staff/dashboard/', StaffDashboardAPIView.as_view(), name='staff-dashboard'),
    path('api/staff/profile/', StaffProfileAPIView.as_view(), name='staff-profile'),
    path('api/staff/alerts/', StaffAlertsAPIView.as_view(), name='staff-alerts'),

    # ──────────────────────────────────────────────────
    # Admin Panel
    # ──────────────────────────────────────────────────
       path('api/admin/login/', AdminLoginAPIView.as_view(), name='admin-login'),
    path('api/admin/profile/', AdminProfileDetailsAPIView.as_view(), name='admin-profile-details'),

    # Dashboard Statistics (ADDED FIX)
    path('api/system-statistics/', AdminSystemStatisticsAPIView.as_view(), name='system-statistics'),

    path('api/admin-user/dashboard/', AdminDashboardAPIView.as_view(), name='admin-dashboard'),
    path('api/admin-user/profile/', AdminProfileAPIView.as_view(), name='admin-profile'),

    path('api/admin-user/doctors/', AdminManageDoctorsAPIView.as_view(), name='admin-doctors'),
    path('api/admin-user/doctors/<int:doctor_id>/remove/', AdminRemoveDoctorAPIView.as_view(), name='admin-doctor-remove'),

    path('api/admin-user/staff/', AdminManageStaffAPIView.as_view(), name='admin-staff'),
    path('api/admin-user/staff/<int:staff_id>/remove/', AdminRemoveStaffAPIView.as_view(), name='admin-staff-remove'),

    path('api/admin-user/approvals/', AdminApprovalsAPIView.as_view(), name='admin-approvals'),
    path('api/admin-user/approvals/<int:request_id>/approve/', AdminApproveRequestAPIView.as_view(), name='admin-approve'),
    path('api/admin-user/approvals/<int:request_id>/reject/', AdminRejectRequestAPIView.as_view(), name='admin-reject'),

    path('api/admin/approval-requests/', AdminApprovalRequestsListAPIView.as_view(), name='admin-approval-requests-list'),
    path('api/admin/approve-user/', AdminApproveUserAPIView.as_view(), name='admin-approve-user'),
    path('api/admin/reject-user/', AdminRejectUserAPIView.as_view(), name='admin-reject-user'),

    path('api/admin/doctors/', AdminDoctorListAPIView.as_view(), name='admin-doctor-list'),
    path('api/admin/doctors/<int:pk>/toggle/', AdminDoctorToggleAPIView.as_view(), name='admin-doctor-toggle'),
    path('api/admin/doctors/toggle-status/', AdminDoctorToggleStatusAPIView.as_view(), name='admin-doctor-toggle-status'),
    path('api/admin/doctors/<int:pk>/', AdminDoctorDetailAPIView.as_view(), name='admin-doctor-detail'),

    path('api/admin/staff/', AdminStaffListAPIView.as_view(), name='admin-staff-list'),
    path('api/admin/staff/toggle-status/', AdminStaffToggleStatusAPIView.as_view(), name='admin-staff-toggle-status'),
    path('api/admin/staff/<int:pk>/', AdminStaffDetailAPIView.as_view(), name='admin-staff-detail'),


    # ──────────────────────────────────────────────────
    # Patient Management
    # ──────────────────────────────────────────────────
    path('api/patients/', PatientListAPIView.as_view(), name='patient-list'),
    path('api/patients/add/', AddPatientAPIView.as_view(), name='patient-add'),
    path('api/patients/<int:patient_id>/', PatientDetailAPIView.as_view(), name='patient-detail'),
    path('api/patients/<int:patient_id>/baseline/', BaselineDetailsAPIView.as_view(), name='patient-baseline'),
    path('api/patients/<int:patient_id>/gold-classification/', GoldClassificationAPIView.as_view(), name='patient-gold'),
    path('api/patients/<int:patient_id>/spirometry/', SpirometryDataAPIView.as_view(), name='patient-spirometry'),
    path('api/patients/<int:patient_id>/gas-exchange/', GasExchangeHistoryAPIView.as_view(), name='patient-gas-exchange'),
    path('api/patients/<int:patient_id>/symptoms/', CurrentSymptomsAPIView.as_view(), name='patient-symptoms'),
    path('api/patients/<int:patient_id>/vitals/', VitalsAPIView.as_view(), name='patient-vitals'),
    path('api/patients/<int:patient_id>/abg-entry/', ABGEntryAPIView.as_view(), name='patient-abg'),
    path('api/patients/<int:patient_id>/reassessment-checklist/', ReassessmentChecklistAPIView.as_view(), name='patient-reassessment-checklist'),
    path('api/system-statistics/', AdminSystemStatisticsAPIView.as_view(), name='system-statistics'),

    # ──────────────────────────────────────────────────
    # Oxygen Therapy & AI Analysis
    # ──────────────────────────────────────────────────
    path('api/patients/<int:patient_id>/oxygen-status/', OxygenStatusAPIView.as_view(), name='patient-oxygen-status'),
    path('api/patients/<int:patient_id>/ai-analysis/', AIAnalysisAPIView.as_view(), name='patient-ai-analysis'),
    path('api/patients/<int:patient_id>/abg-trends/', ABGTrendsAPIView.as_view(), name='patient-abg-trends'),
    path('api/patients/<int:patient_id>/trend-analysis/', TrendAnalysisAPIView.as_view(), name='patient-trend-analysis'),
    path('api/patients/<int:patient_id>/hypoxemia-cause/', HypoxemiaCauseAPIView.as_view(), name='patient-hypoxemia-cause'),
    path('api/patients/<int:patient_id>/oxygen-requirement/', OxygenRequirementAPIView.as_view(), name='patient-oxygen-req'),
    path('api/patients/<int:patient_id>/device-selection/', DeviceSelectionAPIView.as_view(), name='patient-device-selection'),
    path('api/patients/<int:patient_id>/review-recommendation/', ReviewRecommendationAPIView.as_view(), name='patient-review-recommendation'),
    path('api/patients/<int:patient_id>/therapy-recommendation/', TherapyRecommendationAPIView.as_view(), name='patient-therapy'),
    path('api/patients/<int:patient_id>/niv-recommendation/', NIVRecommendationAPIView.as_view(), name='patient-niv'),
    path('api/patients/<int:patient_id>/escalation-criteria/', EscalationCriteriaAPIView.as_view(), name='patient-escalation'),
    path('api/patients/<int:patient_id>/schedule-reassessment/', ScheduleReassessmentAPIView.as_view(), name='patient-schedule-reassessment'),
    path('api/patients/<int:patient_id>/urgent-action/', UrgentActionAPIView.as_view(), name='patient-urgent-action'),

    # ──────────────────────────────────────────────────
    # Notifications
    # ──────────────────────────────────────────────────
    path('api/notifications/', NotificationsAPIView.as_view(), name='notifications'),

    # ──────────────────────────────────────────────────
    # Settings
    # ──────────────────────────────────────────────────
    path('api/settings/', SettingsAPIView.as_view(), name='settings'),
    path('api/clinical-guidelines/', ClinicalGuidelinesAPIView.as_view(), name='clinical-guidelines'),
    path('api/help-support/', HelpSupportAPIView.as_view(), name='help-support'),
]
