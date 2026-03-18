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
    RISK_LEVEL_CHOICES = [
        ('LOW', 'Low'),
        ('MODERATE', 'Moderate'),
        ('HIGH', 'High'),
    ]

    patient_id = models.IntegerField()
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, default='LOW')
    confidence_score = models.IntegerField(default=0)
    acidosis = models.IntegerField(default=0)
    hypercapnia = models.IntegerField(default=0)
    recorded_at = models.DateTimeField(auto_now_add=True)

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
    overall_status = models.CharField(max_length=50, default='')
    paco2_status = models.CharField(max_length=50, default='')
    ph_status = models.CharField(max_length=50, default='')
    spo2_status = models.CharField(max_length=50, default='')
    recorded_at = models.DateTimeField(auto_now_add=True)

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
    device = models.CharField(max_length=100, default='')
    fio2 = models.CharField(max_length=50, default='')
    flow_rate = models.CharField(max_length=50, default='')
    decision = models.CharField(max_length=20, default='accepted')
    override_reason = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'review_recommendation'


class TherapyRecommendation(models.Model):
    patient_id = models.IntegerField()
    device = models.CharField(max_length=100, default='')
    fio2 = models.CharField(max_length=50, default='')
    flow_rate = models.CharField(max_length=50, default='')
    target_spo2 = models.CharField(max_length=50, default='')
    next_abg = models.CharField(max_length=50, default='')
    rationale = models.TextField(default='')
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
    patient_name = models.CharField(max_length=100, default='')
    bed_no = models.CharField(max_length=20, default='')
    ward_no = models.CharField(max_length=20, default='')
    reassessment_type = models.CharField(max_length=50, default='SpO2')
    reassessment_minutes = models.IntegerField(default=60)
    scheduled_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending')
    scheduled_by = models.CharField(max_length=20, default='staff')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reassessment_shedule'



class UrgentAction(models.Model):
    patient_id = models.IntegerField()
    action_type = models.CharField(max_length=100)
    description = models.TextField(default='')
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'urgent_action'


class RecommendationLog(models.Model):
    patient_id = models.IntegerField()
    recommended_device = models.CharField(max_length=100, default='')
    fio2 = models.CharField(max_length=50, default='')
    flow_rate = models.CharField(max_length=50, default='')
    accepted = models.IntegerField(default=1)
    override_reason = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'recommendation_log'


class TherapyPlan(models.Model):
    patient_id = models.IntegerField()
    device = models.CharField(max_length=100, default='')
    fio2 = models.CharField(max_length=50, default='')
    flow_rate = models.CharField(max_length=50, default='')
    target_spo2 = models.CharField(max_length=50, default='')
    next_abg_time = models.CharField(max_length=50, default='')
    rationale = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'therapy_plan'


class ReassessmentSchedule(models.Model):
    patient_id = models.IntegerField()
    reassessment_time_minutes = models.IntegerField(default=60)
    due_time = models.DateTimeField()
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reassessment_schedule'
