from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class Staff(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    staff_role = models.CharField(max_length=255, default="Staff")
    staff_id = models.CharField(max_length=50, blank=True, null=True)
    shift_start = models.TimeField(null=True, blank=True)
    shift_end = models.TimeField(null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    terms_accepted = models.BooleanField(default=False)
    reset_token = models.CharField(max_length=64, blank=True, null=True)
    token_created_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'staff'


class StaffOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = 'staff_otp'

    def __str__(self):
        return f"OTP for {self.email}"


class Reassessment(models.Model):
    TYPE_CHOICES = [
        ('SpO2', 'SpO2'),
        ('ABG', 'ABG'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ]

    patient_id = models.IntegerField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='SpO2')
    due_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    spo2 = models.FloatField(null=True, blank=True)
    respiratory_rate = models.FloatField(null=True, blank=True)
    heart_rate = models.FloatField(null=True, blank=True)
    notes = models.TextField(default='', blank=True)
    reassessment_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reassessment'

    def __str__(self):
        return f"{self.type} reassessment for patient {self.patient_id}"
