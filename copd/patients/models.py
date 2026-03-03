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
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='baseline')
    has_previous_diagnosis = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'baseline_details'


class GoldClassification(models.Model):
    GOLD_CHOICES = [
        (1, 'GOLD 1 - Mild'),
        (2, 'GOLD 2 - Moderate'),
        (3, 'GOLD 3 - Severe'),
        (4, 'GOLD 4 - Very Severe'),
    ]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='gold_classifications')
    gold_stage = models.IntegerField(choices=GOLD_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gold_classification'


class SpirometryData(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='spirometry_data')
    fev1 = models.FloatField(help_text="FEV1 in litres")
    fev1_fvc = models.FloatField(help_text="FEV1/FVC ratio (%)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'spirometry_data'


class GasExchangeHistory(models.Model):
    HYPOXEMIA_CHOICES = [
        ('yes', 'Yes'),
        ('no', 'No'),
        ('unknown', 'Unknown'),
    ]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='gas_exchange_history')
    has_hypoxemia = models.CharField(max_length=10, choices=HYPOXEMIA_CHOICES, default='unknown')
    on_oxygen_therapy = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gas_exchange_history'


class CurrentSymptoms(models.Model):
    MMRC_CHOICES = [
        (0, 'Grade 0'),
        (1, 'Grade 1'),
        (2, 'Grade 2'),
        (3, 'Grade 3'),
        (4, 'Grade 4'),
    ]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='symptoms')
    mmrc_grade = models.IntegerField(choices=MMRC_CHOICES)
    cough = models.BooleanField(default=False)
    sputum = models.BooleanField(default=False)
    wheezing = models.BooleanField(default=False)
    fever = models.BooleanField(default=False)
    chest_tightness = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'current_symptoms'


class Vitals(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='vitals')
    spo2 = models.FloatField(help_text="SpO2 (%)")
    resp_rate = models.IntegerField(help_text="Respiratory rate (breaths/min)")
    heart_rate = models.IntegerField(help_text="Heart rate (bpm)")
    temperature = models.FloatField(help_text="Temperature (°C)")
    bp = models.CharField(max_length=20, help_text="Blood pressure e.g. 120/80")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vitals'


class ABGEntry(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='abg_entries')
    ph = models.FloatField(help_text="pH (7.35–7.45 normal)")
    pao2 = models.FloatField(help_text="PaO2 in mmHg")
    paco2 = models.FloatField(help_text="PaCO2 in mmHg")
    hco3 = models.FloatField(help_text="HCO3 in mEq/L")
    fio2 = models.FloatField(help_text="FiO2 fraction (0.21–1.0)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'abg_entry'


class ReassessmentChecklist(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='reassessments')
    spo2_checked = models.BooleanField(default=False)
    resp_rate_checked = models.BooleanField(default=False)
    consciousness_checked = models.BooleanField(default=False)
    device_fit_checked = models.BooleanField(default=False)
    abg_checked = models.BooleanField(default=False)
    all_clear = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reassessment_checklist'
