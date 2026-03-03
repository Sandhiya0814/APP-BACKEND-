from django.db import models


class OxygenStatus(models.Model):
    patient_id = models.IntegerField()
    current_flow_rate = models.FloatField(help_text="L/min")
    delivery_device = models.CharField(max_length=100)
    target_spo2_min = models.FloatField(default=88.0)
    target_spo2_max = models.FloatField(default=92.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'oxygen_status'


class AIAnalysis(models.Model):
    RISK_LEVEL_CHOICES = [
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    patient_id = models.IntegerField()
    risk_score = models.FloatField(help_text="0–100 scale")
    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES)
    deterioration_probability = models.FloatField(help_text="0.0–1.0")
    key_factors = models.TextField(blank=True, null=True, help_text="JSON string of contributing factors")
    recommendations = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_analysis'


class ABGTrend(models.Model):
    patient_id = models.IntegerField()
    trend_summary = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'abg_trend'


class TrendAnalysis(models.Model):
    patient_id = models.IntegerField()
    parameter = models.CharField(max_length=50, help_text="e.g. pH, PaO2, SpO2")
    values_json = models.TextField(help_text="JSON array of values with timestamps")
    analysis_summary = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'trend_analysis'


class HypoxemiaCause(models.Model):
    CAUSE_CHOICES = [
        ('vq_mismatch', 'V/Q Mismatch'),
        ('hypoventilation', 'Hypoventilation'),
        ('diffusion', 'Diffusion Impairment'),
        ('shunt', 'Intrapulmonary Shunt'),
        ('unknown', 'Unknown'),
    ]
    patient_id = models.IntegerField()
    cause = models.CharField(max_length=20, choices=CAUSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'hypoxemia_cause'


class OxygenRequirement(models.Model):
    patient_id = models.IntegerField()
    lpm_required = models.FloatField(help_text="Litres per minute")
    target_spo2 = models.FloatField(help_text="Target SpO2 (%)")
    rationale = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'oxygen_requirement'


class DeviceSelection(models.Model):
    DEVICE_CHOICES = [
        ('venturi', 'Venturi Mask'),
        ('nasal', 'Nasal Cannula'),
        ('high_flow', 'High-Flow Nasal Cannula'),
        ('non_rebreather', 'Non-Rebreather Mask'),
    ]
    patient_id = models.IntegerField()
    device = models.CharField(max_length=20, choices=DEVICE_CHOICES)
    rationale = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'device_selection'


class ReviewRecommendation(models.Model):
    DECISION_CHOICES = [
        ('accept', 'Accept'),
        ('override', 'Override'),
    ]
    patient_id = models.IntegerField()
    decision = models.CharField(max_length=10, choices=DECISION_CHOICES)
    override_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'review_recommendation'


class TherapyRecommendation(models.Model):
    patient_id = models.IntegerField()
    therapy_type = models.CharField(max_length=100)
    flow_rate = models.FloatField(help_text="L/min")
    device = models.CharField(max_length=100)
    duration = models.CharField(max_length=50, blank=True, null=True)
    precautions = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'therapy_recommendation'


class NIVRecommendation(models.Model):
    patient_id = models.IntegerField()
    mode = models.CharField(max_length=50, help_text="e.g. BiPAP, CPAP")
    ipap = models.FloatField(help_text="Inspiratory Positive Airway Pressure (cmH2O)")
    epap = models.FloatField(help_text="Expiratory Positive Airway Pressure (cmH2O)")
    indication = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'niv_recommendation'


class EscalationCriteria(models.Model):
    patient_id = models.IntegerField()
    criteria_met = models.BooleanField(default=False)
    details = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'escalation_criteria'


class ScheduleReassessment(models.Model):
    INTERVAL_CHOICES = [
        ('30m', '30 Minutes'),
        ('1h', '1 Hour'),
        ('2h', '2 Hours'),
        ('4h', '4 Hours'),
    ]
    patient_id = models.IntegerField()
    interval = models.CharField(max_length=5, choices=INTERVAL_CHOICES)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'schedule_reassessment'


class UrgentAction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]
    patient_id = models.IntegerField()
    action_type = models.CharField(max_length=100, help_text="e.g. ICU Transfer, Call Doctor")
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'urgent_action'
