from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Alert, Notification


class DoctorAlertsAPIView(APIView):
    """
    GET  /api/doctor/alerts/         — list alerts for doctors (unread first)
    POST /api/doctor/alerts/         — create a new alert or acknowledge one
    """
    def get(self, request):
        alerts = Alert.objects.filter(
            target_role__in=['doctor', 'all']
        ).order_by('-created_at').values(
            'id', 'patient_id', 'alert_type', 'severity', 'message', 'status', 'created_at'
        )
        unread_count = Alert.objects.filter(target_role__in=['doctor', 'all'], status='unread').count()
        return Response({
            "unread_count": unread_count,
            "alerts": list(alerts),
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
    GET  /api/staff/alerts/          — list alerts for staff
    POST /api/staff/alerts/          — create alert or mark as read
    """
    def get(self, request):
        alerts = Alert.objects.filter(
            target_role__in=['staff', 'all']
        ).order_by('-created_at').values(
            'id', 'patient_id', 'alert_type', 'severity', 'message', 'status', 'created_at'
        )
        unread_count = Alert.objects.filter(target_role__in=['staff', 'all'], status='unread').count()
        return Response({
            "unread_count": unread_count,
            "alerts": list(alerts),
        }, status=status.HTTP_200_OK)

    def post(self, request):
        action = request.data.get('action')
        if action == 'mark_read':
            alert_id = request.data.get('alert_id')
            try:
                alert = Alert.objects.get(id=alert_id)
                alert.status = 'read'
                alert.save()
                return Response({"message": "Alert marked as read."}, status=status.HTTP_200_OK)
            except Alert.DoesNotExist:
                return Response({"error": "Alert not found."}, status=status.HTTP_404_NOT_FOUND)
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
            target_role='staff',
            status='unread',
        )
        return Response({
            "message": "Alert created.",
            "alert_id": alert.id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
        }, status=status.HTTP_201_CREATED)


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
