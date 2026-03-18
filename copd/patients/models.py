from django.db import models


class Patient(models.Model):
    STATUS_CHOICES = [
        ('critical', 'Critical'),
        ('warning', 'Warning'),
        ('stable', 'Stable'),
    ]
    SEX_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    full_name = models.CharField(max_length=255)
    dob = models.DateField()
    sex = models.CharField(max_length=10, choices=SEX_CHOICES)
    ward = models.CharField(max_length=100)
    bed_number = models.CharField(max_length=50)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='stable')
    assigned_doctor_id = models.IntegerField(null=True, blank=True)
    created_by_staff_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

    class Meta:
        db_table = 'patient'
        ordering = ['-created_at']


class BaselineDetails(models.Model):
    patient_id = models.IntegerField()
    copd_history = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'baseline_details'


class GoldClassification(models.Model):
    patient_id = models.IntegerField()
    gold_stage = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gold_classification'


class SpirometryData(models.Model):
    patient_id = models.IntegerField()
    fev1_percent = models.FloatField()
    fev1_fvc_ratio = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'spirometry_data'


class GasExchangeHistory(models.Model):
    patient_id = models.IntegerField()
    chronic_hypoxemia = models.CharField(max_length=20)
    home_oxygen_use = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gas_exchange_history'


class CurrentSymptoms(models.Model):
    patient_id = models.IntegerField()
    mmrc_score = models.IntegerField()
    increased_cough = models.BooleanField(default=False)
    increased_sputum = models.BooleanField(default=False)
    wheezing = models.BooleanField(default=False)
    fever = models.BooleanField(default=False)
    chest_tightness = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'current_symptoms'


class Vitals(models.Model):
    patient_id = models.IntegerField()
    spo2 = models.IntegerField()
    respiratory_rate = models.IntegerField()
    heart_rate = models.IntegerField()
    temperature = models.FloatField()
    blood_pressure = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vitals'


class AbgEntry(models.Model):
    patient_id = models.IntegerField()
    ph = models.FloatField()
    pao2 = models.FloatField()
    paco2 = models.FloatField()
    hco3 = models.FloatField()
    fio2 = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'abg_entry'


# NOTE: reassessment_checklist table is now managed by staff.models.StaffChecklist
# It stores actual vitals values (spo2, respiratory_rate, heart_rate, remarks)
# instead of boolean check fields.

