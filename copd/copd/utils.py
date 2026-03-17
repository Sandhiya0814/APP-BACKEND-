"""
Shared OTP email utility for Doctor and Staff.

Uses the SINGLE Gmail SMTP configuration from settings.py:
    EMAIL_BACKEND  = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST     = 'smtp.gmail.com'
    EMAIL_PORT     = 587
    EMAIL_USE_TLS  = True
    EMAIL_HOST_USER     = 'sandhiyassenthil1408@gmail.com'
    EMAIL_HOST_PASSWORD = '<Gmail App Password>'
    DEFAULT_FROM_EMAIL  = EMAIL_HOST_USER

Both Doctor and Staff OTP emails are sent through THIS function.
No separate email configuration is needed per role.
"""

from django.core.mail import send_mail
from django.conf import settings


def send_otp_email(recipient_email, recipient_name, otp, role="doctor"):
    """
    Send OTP email to the user's registered email.

    Uses the SAME settings.EMAIL_HOST_USER (Gmail SMTP) as sender
    for BOTH Doctor and Staff roles.

    Args:
        recipient_email (str): User's email from sandhiya.doctor or sandhiya.staff table
        recipient_name  (str): User's name for the greeting
        otp             (str): 6-digit OTP to send
        role            (str): 'doctor' or 'staff' (used only for greeting prefix)

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Use "Dr." prefix only for doctors
    if role == "doctor":
        greeting_name = f"Dr. {recipient_name}"
    else:
        greeting_name = recipient_name

    subject = "Your Login OTP"
    message = (
        f"Dear {greeting_name},\n\n"
        f"Your OTP is: {otp}. It is valid for 5 minutes.\n\n"
        f"If you did not request this, please ignore this email.\n\n"
        f"CDSS COPD Team"
    )

    try:
        # send_mail uses settings.EMAIL_HOST_USER as the sender
        # Recipient is the user's email fetched from sandhiya DB
        send_mail(
            subject,                      # Email subject
            message,                      # Email body
            settings.EMAIL_HOST_USER,     # FROM: single Gmail SMTP sender
            [recipient_email],            # TO: doctor.email or staff.email from DB
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"[OTP Email] Failed to send OTP to {recipient_email}: {e}")
        return False
