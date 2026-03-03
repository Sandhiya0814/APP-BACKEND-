from django.db import models


class Alert(models.Model):
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]
    TARGET_ROLE_CHOICES = [
        ('doctor', 'Doctor'),
        ('staff', 'Staff'),
        ('all', 'All'),
    ]
    STATUS_CHOICES = [
        ('unread', 'Unread'),
        ('read', 'Read'),
        ('acknowledged', 'Acknowledged'),
    ]
    patient_id = models.IntegerField()
    alert_type = models.CharField(max_length=100, help_text="e.g. SpO2 Drop, Escalation Required")
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='info')
    message = models.TextField()
    target_role = models.CharField(max_length=10, choices=TARGET_ROLE_CHOICES, default='all')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='unread')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'alert'
        ordering = ['-created_at']


class Notification(models.Model):
    RECIPIENT_TYPE_CHOICES = [
        ('doctor', 'Doctor'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    ]
    recipient_type = models.CharField(max_length=10, choices=RECIPIENT_TYPE_CHOICES)
    recipient_id = models.IntegerField()
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notification'
        ordering = ['-created_at']
