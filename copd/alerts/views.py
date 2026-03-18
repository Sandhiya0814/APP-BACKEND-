from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from .models import Alert, Notification


def check_spo2_drop_and_alert(patient_id, new_spo2):
    """
    Compare new_spo2 with the patient's previous SpO2 reading.
    If it dropped, create a doctor alert in the alert table.

    Thresholds:
      - SpO2 < 88 → severity='critical', alert_type='Critical Hypoxemia'
      - SpO2 88-92 AND dropped → severity='warning', alert_type='SpO2 Drop'
      - SpO2 dropped by ≥5 points → severity='critical'
    """
    from patients.models import Patient, Vitals

    try:
        new_spo2_val = float(new_spo2)
    except (ValueError, TypeError):
        return  # Can't compare

    # Fetch patient info
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return

    # Get the previous SpO2 reading (second most recent vital or latest before this update)
    previous_vitals = Vitals.objects.filter(
        patient_id=patient_id,
        spo2__isnull=False
    ).order_by('-created_at')[:2]

    previous_spo2 = None
    if len(previous_vitals) >= 2:
        previous_spo2 = float(previous_vitals[1].spo2)
    elif len(previous_vitals) == 1:
        previous_spo2 = float(previous_vitals[0].spo2)

    # Check for staff checklist previous values too
    if previous_spo2 is None:
        from staff.models import StaffChecklist
        prev_checklist = StaffChecklist.objects.filter(
            patient_id=patient_id,
            spo2__isnull=False
        ).order_by('-created_at').first()
        if prev_checklist:
            previous_spo2 = float(prev_checklist.spo2)

    # Build patient info string
    patient_info = f"{patient.full_name} (Bed {patient.bed_number})"

    # Determine if alert is needed
    alert_type = None
    severity = None
    message = None

    if new_spo2_val < 88:
        # Always critical below 88
        alert_type = "Critical Hypoxemia"
        severity = "critical"
        if previous_spo2 is not None and previous_spo2 > new_spo2_val:
            drop = round(previous_spo2 - new_spo2_val, 1)
            message = f"{patient_info} • SpO₂ dropped to {int(new_spo2_val)}% (↓{drop}%)"
        else:
            message = f"{patient_info} • SpO₂ dropped to {int(new_spo2_val)}%"

    elif previous_spo2 is not None and new_spo2_val < previous_spo2:
        drop = round(previous_spo2 - new_spo2_val, 1)
        if drop >= 5:
            # Significant drop
            alert_type = "SpO2 Drop"
            severity = "critical"
            message = f"{patient_info} • SpO₂ dropped to {int(new_spo2_val)}% (↓{drop}%)"
        elif new_spo2_val <= 92 and drop >= 2:
            # Moderate concern — below safe range and dropped
            alert_type = "SpO2 Drop"
            severity = "warning"
            message = f"{patient_info} • SpO₂ dropped to {int(new_spo2_val)}% (↓{drop}%)"

    if alert_type and message:
        # Avoid duplicate alerts within last 10 minutes for same patient+type
        from datetime import timedelta
        recent_cutoff = timezone.now() - timedelta(minutes=10)
        existing = Alert.objects.filter(
            patient_id=patient_id,
            alert_type=alert_type,
            created_at__gte=recent_cutoff
        ).exists()

        if not existing:
            Alert.objects.create(
                patient_id=patient_id,
                alert_type=alert_type,
                severity=severity,
                message=message,
                target_role='doctor',
                status='unread',
            )
            print(f"[ALERT] Created {severity} alert for patient {patient_id}: {message}")


def _time_ago(dt_value):
    """Return human-readable time ago string."""
    now = timezone.now()
    diff = now - dt_value
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "Just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


class DoctorAlertsAPIView(APIView):
    """
    GET  /api/doctor/alerts/         — list alerts for doctors (unread first)
    POST /api/doctor/alerts/         — create a new alert or acknowledge one
    """
    def get(self, request):
        from patients.models import Patient

        alerts_qs = Alert.objects.filter(
            target_role__in=['doctor', 'all']
        ).order_by('-created_at')[:50]

        critical_alerts = []
        warning_alerts = []
        info_alerts = []

        for alert in alerts_qs:
            # Look up patient details
            p_name = ""
            p_bed = ""
            p_ward = ""
            try:
                patient = Patient.objects.get(id=alert.patient_id)
                p_name = patient.full_name
                p_bed = patient.bed_number
                p_ward = patient.ward
            except Patient.DoesNotExist:
                pass

            alert_item = {
                "id": alert.id,
                "patient_id": alert.patient_id,
                "patient_name": p_name,
                "bed_number": p_bed,
                "ward_no": p_ward,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "status": alert.status,
                "time_ago": _time_ago(alert.created_at) if alert.created_at else "",
                "created_at": alert.created_at.strftime("%Y-%m-%d %H:%M:%S") if alert.created_at else None,
            }

            if alert.severity == 'critical':
                critical_alerts.append(alert_item)
            elif alert.severity == 'warning':
                warning_alerts.append(alert_item)
            else:
                info_alerts.append(alert_item)

        unread_count = Alert.objects.filter(
            target_role__in=['doctor', 'all'],
            status='unread'
        ).count()

        return Response({
            "unread_count": unread_count,
            "critical_alerts": critical_alerts,
            "warning_alerts": warning_alerts,
            "info_alerts": info_alerts,
        }, status=status.HTTP_200_OK)

    def post(self, request):
        action = request.data.get('action')
        # Acknowledge an alert
        if action == 'acknowledge':
            alert_id = request.data.get('alert_id')
            try:
                alert = Alert.objects.get(id=alert_id)
                alert.status = 'acknowledged'
                alert.save()
                return Response({"message": "Alert acknowledged."}, status=status.HTTP_200_OK)
            except Alert.DoesNotExist:
                return Response({"error": "Alert not found."}, status=status.HTTP_404_NOT_FOUND)
        # Mark as read
        if action == 'mark_read':
            alert_id = request.data.get('alert_id')
            try:
                alert = Alert.objects.get(id=alert_id)
                alert.status = 'read'
                alert.save()
                return Response({"message": "Alert marked as read."}, status=status.HTTP_200_OK)
            except Alert.DoesNotExist:
                return Response({"error": "Alert not found."}, status=status.HTTP_404_NOT_FOUND)
        # Create a new alert
        patient_id = request.data.get('patient_id')
        alert_type = request.data.get('alert_type')
        message = request.data.get('message')
        if not (patient_id and alert_type and message):
            return Response({"error": "patient_id, alert_type, and message are required."}, status=status.HTTP_400_BAD_REQUEST)
        alert = Alert.objects.create(
            patient_id=patient_id,
            alert_type=alert_type,
            severity=request.data.get('severity', 'info'),
            message=message,
            target_role='doctor',
            status='unread',
        )
        return Response({
            "message": "Alert created.",
            "alert_id": alert.id,
            "patient_id": alert.patient_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
        }, status=status.HTTP_201_CREATED)


class StaffAlertsAPIView(APIView):
    """
    GET  /api/staff/alerts/
    Returns reassessment alerts ONLY from sandhiya.schedule_reassessment
    where scheduled_by='doctor' and status='pending'.
    Categorized by urgency:
      - Overdue → critical
      - Due within 10 mins → moderate
      - Future (>10 mins) → not shown

    POST /api/staff/alerts/
    Body: { "action": "mark_done", "reassessment_id": <id> }
    Marks a scheduled reassessment as 'done'.
    """
    def get(self, request):
        from therapy.models import ScheduleReassessment
        from django.utils import timezone

        now = timezone.now()

        # AUTO STATUS UPDATE: pending → due when scheduled_time <= NOW()
        ScheduleReassessment.objects.filter(
            status='pending',
            scheduled_time__lte=now
        ).update(status='due')

        # Fetch ONLY doctor-scheduled, pending/due reassessments
        pending = ScheduleReassessment.objects.filter(
            scheduled_by='doctor',
            status__in=['pending', 'due']
        ).order_by('scheduled_time')

        critical_alerts = []   # Overdue
        moderate_alerts = []   # Due within 10 mins

        seen_ids = set()  # Prevent duplicates

        for r in pending:
            if r.id in seen_ids:
                continue
            seen_ids.add(r.id)

            if r.scheduled_time:
                diff = r.scheduled_time - now
                due_in_minutes = int(diff.total_seconds() / 60)
            else:
                due_in_minutes = 0

            # Skip future reassessments (>10 mins away)
            if due_in_minutes > 10:
                continue

            # Lookup patient name / bed / ward if missing
            p_name = r.patient_name
            p_bed = r.bed_no
            p_ward = r.ward_no
            if not p_name or not p_bed:
                from patients.models import Patient
                try:
                    patient = Patient.objects.get(id=r.patient_id)
                    p_name = p_name or patient.full_name
                    p_bed = p_bed or patient.bed_number
                    p_ward = p_ward or patient.ward
                except Exception:
                    p_name = p_name or "Unknown"
                    p_bed = p_bed or "--"

            alert_item = {
                "id": r.id,
                "patient_id": r.patient_id,
                "patient_name": p_name,
                "bed_no": p_bed,
                "ward_no": p_ward,
                "reassessment_type": r.reassessment_type,
                "scheduled_time": r.scheduled_time.strftime("%Y-%m-%d %H:%M:%S") if r.scheduled_time else None,
                "due_in": due_in_minutes,
                "status": r.status,
                "scheduled_by": r.scheduled_by,
            }

            if due_in_minutes <= 0:
                # Overdue → critical
                alert_item["severity"] = "critical"
                critical_alerts.append(alert_item)
            else:
                # Due within 10 mins → moderate
                alert_item["severity"] = "moderate"
                moderate_alerts.append(alert_item)

        total_count = len(critical_alerts) + len(moderate_alerts)

        return Response({
            "status": "success",
            "total_count": total_count,
            "critical_count": len(critical_alerts),
            "moderate_count": len(moderate_alerts),
            "critical_alerts": critical_alerts,
            "moderate_alerts": moderate_alerts,
        }, status=status.HTTP_200_OK)

    def post(self, request):
        from therapy.models import ScheduleReassessment

        action = request.data.get('action')

        if action == 'mark_done':
            reassessment_id = request.data.get('reassessment_id')
            if not reassessment_id:
                return Response({"status": "error", "message": "reassessment_id is required"},
                                status=status.HTTP_400_BAD_REQUEST)
            try:
                sr = ScheduleReassessment.objects.get(id=reassessment_id)
                sr.status = 'completed'
                sr.save()
                return Response({"status": "success", "message": "Reassessment marked as completed."},
                                status=status.HTTP_200_OK)
            except ScheduleReassessment.DoesNotExist:
                return Response({"status": "error", "message": "Reassessment not found."},
                                status=status.HTTP_404_NOT_FOUND)

        return Response({"status": "error", "message": "Invalid action."},
                        status=status.HTTP_400_BAD_REQUEST)


class NotificationsAPIView(APIView):
    """
    GET  /api/notifications/?recipient_type=doctor&recipient_id=<id>
    POST /api/notifications/  Body: { recipient_type, recipient_id, title, message }
    PUT  /api/notifications/  Body: { notification_id }  — mark as read
    """
    def get(self, request):
        recipient_type = request.query_params.get('recipient_type')
        recipient_id = request.query_params.get('recipient_id')
        if not (recipient_type and recipient_id):
            return Response({"error": "recipient_type and recipient_id are required."}, status=status.HTTP_400_BAD_REQUEST)
        notifications = Notification.objects.filter(
            recipient_type=recipient_type,
            recipient_id=recipient_id
        ).values('id', 'title', 'message', 'is_read', 'created_at')
        unread = Notification.objects.filter(recipient_type=recipient_type, recipient_id=recipient_id, is_read=False).count()
        return Response({
            "unread_count": unread,
            "notifications": list(notifications),
        }, status=status.HTTP_200_OK)

    def post(self, request):
        recipient_type = request.data.get('recipient_type')
        recipient_id = request.data.get('recipient_id')
        title = request.data.get('title')
        message = request.data.get('message')
        if not (recipient_type and recipient_id and title and message):
            return Response({"error": "recipient_type, recipient_id, title, and message are required."}, status=status.HTTP_400_BAD_REQUEST)
        notif = Notification.objects.create(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            title=title,
            message=message,
        )
        return Response({"message": "Notification sent.", "notification_id": notif.id}, status=status.HTTP_201_CREATED)

    def put(self, request):
        notification_id = request.data.get('notification_id')
        if not notification_id:
            return Response({"error": "notification_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            notif = Notification.objects.get(id=notification_id)
            notif.is_read = True
            notif.save()
            return Response({"message": "Notification marked as read."}, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response({"error": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
