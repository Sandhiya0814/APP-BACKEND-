from django.db import models


class OxygenStatus(models.Model):
    patient_id = models.IntegerField()
    current_flow_rate = models.FloatField()
    delivery_device = models.CharField(max_length=100)
    target_spo2_min = models.FloatField(default=88.0)
    target_spo2_max = models.FloatField(default=92.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'oxygen_status'


class AIAnalysis(models.Model):
    patient_id = models.IntegerField()
    risk_score = models.FloatField(default=50.0)
    risk_level = models.CharField(max_length=20, default='moderate')
    deterioration_probability = models.FloatField(default=0.5)
    key_factors = models.TextField(default='')
    recommendations = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_analysis'


class ABGTrend(models.Model):
    patient_id = models.IntegerField()
    ph = models.FloatField()
    pao2 = models.FloatField()
    paco2 = models.FloatField()
    hco3 = models.FloatField()
    fio2 = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'abg_trend'


class TrendAnalysis(models.Model):
    patient_id = models.IntegerField()
    spo2_trend = models.TextField(default='')
    vitals_trend = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'trend_analysis'


class HypoxemiaCause(models.Model):
    patient_id = models.IntegerField()
    cause = models.CharField(max_length=50, default='unknown')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'hypoxemia_cause'


class OxygenRequirement(models.Model):
    patient_id = models.IntegerField()
    spo2 = models.FloatField(default=0.0)
    hypoxemia_level = models.CharField(max_length=50, default='')
    symptoms_level = models.CharField(max_length=50, default='')
    oxygen_required = models.CharField(max_length=20, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'oxygen_requirement'


class DeviceSelection(models.Model):
    patient_id = models.IntegerField()
    device = models.CharField(max_length=50, default='venturi')
    flow_range = models.CharField(max_length=50, default='')
    rationale = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'device_selection'


class ReviewRecommendation(models.Model):
    patient_id = models.IntegerField()
    decision = models.CharField(max_length=20, default='accept')
    override_reason = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'review_recommendation'


class TherapyRecommendation(models.Model):
    patient_id = models.IntegerField()
    therapy_type = models.CharField(max_length=100, default='Controlled Oxygen Therapy')
    flow_rate = models.FloatField(default=2.0)
    device = models.CharField(max_length=50, default='venturi')
    duration = models.CharField(max_length=50, default='Continuous')
    precautions = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'therapy_recommendation'


class NIVRecommendation(models.Model):
    patient_id = models.IntegerField()
    mode = models.CharField(max_length=20, default='BiPAP')
    ipap = models.FloatField(default=14.0)
    epap = models.FloatField(default=4.0)
    indication = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'niv_recommendation'


class EscalationCriteria(models.Model):
    patient_id = models.IntegerField()
    criteria_met = models.BooleanField(default=False)
    details = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'escalation_criteria'


class ScheduleReassessment(models.Model):
    patient_id = models.IntegerField()
    interval = models.CharField(max_length=10, default='1h')
    scheduled_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'schedule_reassessment'


class UrgentAction(models.Model):
    patient_id = models.IntegerField()
    action_type = models.CharField(max_length=100)
    description = models.TextField(default='')
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'urgent_action'