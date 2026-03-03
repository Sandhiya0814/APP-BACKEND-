from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('doctor', 'Doctor'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    is_approved = models.BooleanField(default=False) # For Admin Approvals

    class Meta:
        db_table = 'users'

class Patient(models.Model):
    STATUS_CHOICES = [
        ('critical', 'Critical'),
        ('warning', 'Warning'),
        ('stable', 'Stable'),
    ]
    full_name = models.CharField(max_length=255)
    dob = models.DateField()
    sex = models.CharField(max_length=10)
    ward = models.CharField(max_length=100)
    bed_number = models.CharField(max_length=50)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='stable')
    assigned_doctor = models.ForeignKey(CustomUser, related_name='patients_doctor', on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, related_name='patients_staff', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'patients'

class Symptoms(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='symptoms')
    mmrc_grade = models.IntegerField()
    cough = models.BooleanField(default=False)
    sputum = models.BooleanField(default=False)
    wheezing = models.BooleanField(default=False)
    fever = models.BooleanField(default=False)
    chest_tightness = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class BaselineDetails(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='baseline')
    has_previous_diagnosis = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class SpirometryData(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='spirometry')
    fev1 = models.FloatField()
    fev1_fvc = models.FloatField()
    gold_stage = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ABGData(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='abg_data')
    ph = models.FloatField()
    pao2 = models.FloatField()
    paco2 = models.FloatField()
    hco3 = models.FloatField()
    fio2 = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

class Vitals(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='vitals')
    spo2 = models.FloatField()
    resp_rate = models.IntegerField()
    heart_rate = models.IntegerField()
    temperature = models.FloatField()
    bp = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

class OxygenRequirement(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='oxygen_req')
    lpm_required = models.FloatField()
    target_spo2 = models.FloatField()
    rationale = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Recommendation(models.Model):
    REC_TYPE_CHOICES = (
        ('therapy', 'Therapy Recommendation'),
        ('niv', 'NIV Recommendation'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('overridden', 'Overridden'),
    )
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='recommendations')
    rec_type = models.CharField(max_length=20, choices=REC_TYPE_CHOICES)
    content = models.TextField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    override_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class DeviceSelection(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='device_selection')
    device_name = models.CharField(max_length=100)
    rationale = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Alert(models.Model):
    SEVERITY_CHOICES = [
        ('normal', 'Normal Alert'),
        ('warning', 'Warning Alert'),
        ('critical', 'Critical Alert'),
    ]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='alerts')
    severity = models.CharField(max_length=15, choices=SEVERITY_CHOICES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class ReassessmentSchedule(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='schedules')
    interval_minutes = models.IntegerField()
    scheduled_at = models.DateTimeField()
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class ReassessmentChecklist(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    spo2_checked = models.BooleanField(default=False)
    resp_rate_checked = models.BooleanField(default=False)
    consciousness_checked = models.BooleanField(default=False)
    device_fit_checked = models.BooleanField(default=False)
    abg_checked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
