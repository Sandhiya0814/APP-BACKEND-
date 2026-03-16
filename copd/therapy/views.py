from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from .models import (
    OxygenStatus, AIAnalysis, ABGTrend, TrendAnalysis, HypoxemiaCause,
    OxygenRequirement, DeviceSelection, ReviewRecommendation,
    TherapyRecommendation, NIVRecommendation, EscalationCriteria,
    ScheduleReassessment, UrgentAction
)


def get_patient_or_404(patient_id):
    from patients.models import Patient
    try:
        return Patient.objects.get(id=patient_id), None
    except Patient.DoesNotExist:
        return None, Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)


class OxygenStatusAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/oxygen-status/
    POST /api/patients/<patient_id>/oxygen-status/
    Body: { current_flow_rate, delivery_device, target_spo2_min, target_spo2_max }
    """
    def get(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        records = OxygenStatus.objects.filter(patient_id=patient_id).order_by('-created_at').values()
        return Response({"patient_id": patient_id, "oxygen_status": list(records)}, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        flow_rate = request.data.get('current_flow_rate')
        device = request.data.get('delivery_device')
        if not flow_rate or not device:
            return Response({"error": "current_flow_rate and delivery_device are required."}, status=status.HTTP_400_BAD_REQUEST)
        record = OxygenStatus.objects.create(
            patient_id=patient_id,
            current_flow_rate=float(flow_rate),
            delivery_device=device,
            target_spo2_min=request.data.get('target_spo2_min', 88.0),
            target_spo2_max=request.data.get('target_spo2_max', 92.0),
        )
        return Response({
            "message": "Oxygen status saved.",
            "patient_id": patient_id,
            "current_flow_rate": record.current_flow_rate,
            "delivery_device": record.delivery_device,
            "target_spo2_min": record.target_spo2_min,
            "target_spo2_max": record.target_spo2_max,
            "recorded_at": record.created_at,
        }, status=status.HTTP_201_CREATED)


class AIAnalysisAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/ai-analysis/
    POST /api/patients/<patient_id>/ai-analysis/
    GET returns the latest AI analysis, which is auto-computed from patient vitals and ABG.
    POST saves a manual/computed AI analysis result.
    """
    def get(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        from patients.models import Vitals, ABGEntry
        latest_vitals = Vitals.objects.filter(patient_id=patient_id).order_by('-created_at').first()
        latest_abg = ABGEntry.objects.filter(patient_id=patient_id).order_by('-created_at').first()

        # Auto-compute risk based on clinical thresholds
        risk_score = 50.0
        risk_level = 'moderate'
        key_factors = []
        recommendations = []

        if latest_vitals:
            if latest_vitals.spo2 < 88:
                risk_score = min(risk_score + 30, 100)
                key_factors.append("Critical SpO2 < 88%")
                recommendations.append("Immediate oxygen therapy adjustment required.")
            elif latest_vitals.spo2 < 92:
                risk_score = min(risk_score + 15, 100)
                key_factors.append("SpO2 below target range (88–92%)")
                recommendations.append("Increase oxygen flow rate.")
            if latest_vitals.resp_rate > 30:
                risk_score = min(risk_score + 20, 100)
                key_factors.append("Tachypnoea: RR > 30 breaths/min")
                recommendations.append("Consider NIV support.")
            elif latest_vitals.resp_rate > 25:
                risk_score = min(risk_score + 10, 100)
                key_factors.append("Elevated respiratory rate (25–30 breaths/min)")

        if latest_abg:
            if latest_abg.ph < 7.25:
                risk_score = min(risk_score + 25, 100)
                key_factors.append("Severe acidosis: pH < 7.25")
                recommendations.append("Urgent medical review and NIV consideration.")
            elif latest_abg.ph < 7.35:
                risk_score = min(risk_score + 10, 100)
                key_factors.append("Acidosis: pH < 7.35")
            if latest_abg.paco2 > 60:
                risk_score = min(risk_score + 20, 100)
                key_factors.append("Hypercapnia: PaCO2 > 60 mmHg")
                recommendations.append("Monitor for CO2 narcosis.")

        if risk_score >= 80:
            risk_level = 'critical'
        elif risk_score >= 60:
            risk_level = 'high'
        elif risk_score >= 40:
            risk_level = 'moderate'
        else:
            risk_level = 'low'

        deterioration_probability = round(min(risk_score / 100, 1.0), 2)
        if not recommendations:
            recommendations.append("Continue current oxygen therapy and monitor closely.")

        return Response({
            "patient_id": patient_id,
            "risk_score": round(risk_score, 1),
            "risk_level": risk_level,
            "deterioration_probability": deterioration_probability,
            "key_factors": key_factors,
            "recommendations": recommendations,
            "based_on": {
                "vitals_recorded_at": latest_vitals.created_at if latest_vitals else None,
                "abg_recorded_at": latest_abg.created_at if latest_abg else None,
            }
        }, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        record = AIAnalysis.objects.create(
            patient_id=patient_id,
            risk_score=request.data.get('risk_score', 50.0),
            risk_level=request.data.get('risk_level', 'moderate'),
            deterioration_probability=request.data.get('deterioration_probability', 0.5),
            key_factors=str(request.data.get('key_factors', [])),
            recommendations=str(request.data.get('recommendations', [])),
        )
        return Response({"message": "AI analysis saved.", "id": record.id}, status=status.HTTP_201_CREATED)


class ABGTrendsAPIView(APIView):
    """
    GET /api/patients/<patient_id>/abg-trends/
    Returns all ABG entries in chronological order for trend display.
    """
    def get(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        from patients.models import ABGEntry
        entries = ABGEntry.objects.filter(patient_id=patient_id).order_by('created_at').values(
            'id', 'ph', 'pao2', 'paco2', 'hco3', 'fio2', 'created_at'
        )
        return Response({
            "patient_id": patient_id,
            "abg_trend_data": list(entries),
            "total_entries": len(list(entries)),
        }, status=status.HTTP_200_OK)


class TrendAnalysisAPIView(APIView):
    """
    GET /api/patients/<patient_id>/trend-analysis/
    Returns SpO2 and Vitals trend data for chart display.
    """
    def get(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        from patients.models import Vitals
        vitals = Vitals.objects.filter(patient_id=patient_id).order_by('created_at').values(
            'spo2', 'resp_rate', 'heart_rate', 'temperature', 'created_at'
        )
        return Response({
            "patient_id": patient_id,
            "vitals_trend": list(vitals),
        }, status=status.HTTP_200_OK)


class HypoxemiaCauseAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/hypoxemia-cause/
    POST /api/patients/<patient_id>/hypoxemia-cause/
    Body: { cause: "vq_mismatch"|"hypoventilation"|"diffusion"|"shunt"|"unknown" }
    """
    VALID_CAUSES = ['V/Q Mismatch', 'Alveolar Hypoventilation', 'Diffusion Impairment', 'Intrapulmonary Shunt', 'Unknown']

    def get(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        latest = HypoxemiaCause.objects.filter(patient_id=patient_id).order_by('-created_at').first()
        if latest:
            return Response({"patient_id": patient_id, "cause": latest.cause, "recorded_at": latest.created_at}, status=status.HTTP_200_OK)
        return Response({"patient_id": patient_id, "cause": None}, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        cause = request.data.get('cause')
        if cause not in self.VALID_CAUSES:
            return Response({"error": f"cause must be one of: {', '.join(self.VALID_CAUSES)}"}, status=status.HTTP_400_BAD_REQUEST)
        record = HypoxemiaCause.objects.create(patient_id=patient_id, cause=cause)
        return Response({"message": "Cause saved successfully", "patient_id": patient_id, "cause": record.cause}, status=status.HTTP_201_CREATED)


class OxygenRequirementAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/oxygen-requirement/
    POST /api/patients/<patient_id>/oxygen-requirement/
    Body: { lpm_required, target_spo2, rationale }
    """
    def get(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        latest = OxygenRequirement.objects.filter(patient_id=patient_id).order_by('-created_at').first()
        if latest:
            return Response({
                "patient_id": patient_id,
                "spo2": latest.spo2,
                "hypoxemia_level": latest.hypoxemia_level,
                "symptoms_level": latest.symptoms_level,
                "oxygen_required": latest.oxygen_required,
                "recorded_at": latest.created_at,
            }, status=status.HTTP_200_OK)
        # Auto-compute from patient data
        from patients.models import Vitals, ABGEntry
        latest_vitals = Vitals.objects.filter(patient_id=patient_id).order_by('-created_at').first()
        hypoxemia_level = 'Moderate'
        symptoms_level = 'Moderate'
        oxygen_required = 'Yes'
        if latest_vitals:
            if latest_vitals.spo2 < 88:
                hypoxemia_level = 'Severe'
                symptoms_level = 'Severe'
            elif latest_vitals.spo2 < 92:
                hypoxemia_level = 'Moderate'
                symptoms_level = 'Moderate'
        return Response({
            "patient_id": patient_id,
            "spo2": latest_vitals.spo2 if latest_vitals else 0.0,
            "hypoxemia_level": hypoxemia_level,
            "symptoms_level": symptoms_level,
            "oxygen_required": oxygen_required,
        }, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        spo2 = request.data.get('spo2')
        if spo2 is None:
            return Response({"error": "spo2 is required."}, status=status.HTTP_400_BAD_REQUEST)
        record = OxygenRequirement.objects.create(
            patient_id=patient_id,
            spo2=float(spo2),
            hypoxemia_level=request.data.get('hypoxemia_level', ''),
            symptoms_level=request.data.get('symptoms_level', ''),
            oxygen_required=request.data.get('oxygen_required', ''),
        )
        return Response({
            "message": "Oxygen requirement saved.", 
            "patient_id": patient_id, 
            "spo2": record.spo2
        }, status=status.HTTP_201_CREATED)

class CustomOxygenRequirementAPIView(APIView):
    """
    POST /api/patient/oxygen-requirement/
    Body: { "patient_id": 5, "spo2": 86, "hypoxemia_level": "Severe", "symptoms_level": "Moderate", "oxygen_required": "Yes" }
    """
    def post(self, request):
        patient_id = request.data.get('patient_id')
        if not patient_id:
             return Response({"error": "patient_id is required."}, status=status.HTTP_400_BAD_REQUEST)
             
        try:
            from patients.models import Patient
            patient = Patient.objects.get(id=patient_id)
        except Exception:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

        spo2 = request.data.get('spo2')
        record = OxygenRequirement.objects.create(
            patient_id=patient_id,
            spo2=float(spo2) if spo2 is not None else 0.0,
            hypoxemia_level=request.data.get('hypoxemia_level', ''),
            symptoms_level=request.data.get('symptoms_level', ''),
            oxygen_required=request.data.get('oxygen_required', '')
        )
        return Response({"message": "Oxygen requirement saved successfully"}, status=status.HTTP_201_CREATED)


class CustomHypoxemiaCauseAPIView(APIView):
    """
    POST /api/patient/hypoxemia-cause/
    Body: { "patient_id": 3, "cause": "V/Q Mismatch" }
    """
    VALID_CAUSES = ['V/Q Mismatch', 'Alveolar Hypoventilation', 'Diffusion Impairment', 'Intrapulmonary Shunt', 'Unknown']

    def post(self, request):
        patient_id = request.data.get('patient_id')
        cause = request.data.get('cause')
        
        if not patient_id:
            return Response({"error": "patient_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from patients.models import Patient
            patient = Patient.objects.get(id=patient_id)
        except Exception:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
            
        if cause not in self.VALID_CAUSES:
            return Response({"error": f"cause must be one of: {', '.join(self.VALID_CAUSES)}"}, status=status.HTTP_400_BAD_REQUEST)
            
        record = HypoxemiaCause.objects.create(patient_id=patient_id, cause=cause)
        return Response({
            "message": "Cause saved successfully"
        }, status=status.HTTP_201_CREATED)


class DeviceSelectionAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/device-selection/
    POST /api/patients/<patient_id>/device-selection/
    Body: { device: "venturi"|"nasal"|"high_flow"|"non_rebreather", rationale }
    """
    VALID_DEVICES = ['venturi', 'nasal', 'high_flow', 'non_rebreather']

    def get(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        latest = DeviceSelection.objects.filter(patient_id=patient_id).order_by('-created_at').first()
        if latest:
            return Response({"patient_id": patient_id, "device": latest.device, "rationale": latest.rationale, "recorded_at": latest.created_at}, status=status.HTTP_200_OK)
        return Response({"patient_id": patient_id, "device": None}, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        device = request.data.get('device')
        if device not in self.VALID_DEVICES:
            return Response({"error": f"device must be one of: {', '.join(self.VALID_DEVICES)}"}, status=status.HTTP_400_BAD_REQUEST)
        record = DeviceSelection.objects.create(
            patient_id=patient_id,
            device=device,
            rationale=request.data.get('rationale', ''),
        )
        return Response({"message": "Device selection saved.", "patient_id": patient_id, "device": record.device}, status=status.HTTP_201_CREATED)


class ReviewRecommendationAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/review-recommendation/
    POST /api/patients/<patient_id>/review-recommendation/
    Body: { decision: "accept"|"override", override_reason }
    """
    def get(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        latest = ReviewRecommendation.objects.filter(patient_id=patient_id).order_by('-created_at').first()
        if latest:
            return Response({"patient_id": patient_id, "decision": latest.decision, "override_reason": latest.override_reason, "recorded_at": latest.created_at}, status=status.HTTP_200_OK)
        return Response({"patient_id": patient_id, "decision": None}, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        decision = request.data.get('decision')
        if decision not in ['accept', 'override']:
            return Response({"error": "decision must be 'accept' or 'override'."}, status=status.HTTP_400_BAD_REQUEST)
        override_reason = request.data.get('override_reason', '')
        if decision == 'override' and not override_reason:
            return Response({"error": "override_reason is required when decision is 'override'."}, status=status.HTTP_400_BAD_REQUEST)
        record = ReviewRecommendation.objects.create(patient_id=patient_id, decision=decision, override_reason=override_reason)
        return Response({"message": f"Recommendation {decision}ed.", "patient_id": patient_id, "decision": record.decision}, status=status.HTTP_201_CREATED)


class TherapyRecommendationAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/therapy-recommendation/
    POST /api/patients/<patient_id>/therapy-recommendation/
    """
    def get(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        latest = TherapyRecommendation.objects.filter(patient_id=patient_id).order_by('-created_at').first()
        if latest:
            return Response({
                "patient_id": patient_id,
                "therapy_type": latest.therapy_type,
                "flow_rate": latest.flow_rate,
                "device": latest.device,
                "duration": latest.duration,
                "precautions": latest.precautions,
                "recorded_at": latest.created_at,
            }, status=status.HTTP_200_OK)
        # Auto-compute from device selection and oxygen requirement
        device_sel = DeviceSelection.objects.filter(patient_id=patient_id).order_by('-created_at').first()
        o2_req = OxygenRequirement.objects.filter(patient_id=patient_id).order_by('-created_at').first()
        return Response({
            "patient_id": patient_id,
            "therapy_type": "Controlled Oxygen Therapy",
            "flow_rate": 2.0, # Defaulting since lpm_required is removed
            "device": device_sel.device if device_sel else "venturi",
            "duration": "Continuous",
            "precautions": "Maintain SpO2 88–92%. Avoid high-flow oxygen in COPD patients.",
        }, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        therapy_type = request.data.get('therapy_type', 'Controlled Oxygen Therapy')
        flow_rate = request.data.get('flow_rate', 2.0)
        device = request.data.get('device', 'venturi')
        record = TherapyRecommendation.objects.create(
            patient_id=patient_id,
            therapy_type=therapy_type,
            flow_rate=float(flow_rate),
            device=device,
            duration=request.data.get('duration', 'Continuous'),
            precautions=request.data.get('precautions', 'Maintain SpO2 88–92%.'),
        )
        return Response({"message": "Therapy recommendation saved.", "patient_id": patient_id, "therapy_type": record.therapy_type}, status=status.HTTP_201_CREATED)


class NIVRecommendationAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/niv-recommendation/
    POST /api/patients/<patient_id>/niv-recommendation/
    Body: { mode, ipap, epap, indication }
    """
    def get(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        latest = NIVRecommendation.objects.filter(patient_id=patient_id).order_by('-created_at').first()
        if latest:
            return Response({
                "patient_id": patient_id,
                "mode": latest.mode,
                "ipap": latest.ipap,
                "epap": latest.epap,
                "indication": latest.indication,
                "recorded_at": latest.created_at,
            }, status=status.HTTP_200_OK)
        # Default NIV protocol for COPD
        return Response({
            "patient_id": patient_id,
            "mode": "BiPAP",
            "ipap": 14.0,
            "epap": 4.0,
            "indication": "Acute hypercapnic respiratory failure with pH < 7.35 and PaCO2 > 45 mmHg.",
        }, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        mode = request.data.get('mode', 'BiPAP')
        ipap = request.data.get('ipap')
        epap = request.data.get('epap')
        if not ipap or not epap:
            return Response({"error": "ipap and epap are required."}, status=status.HTTP_400_BAD_REQUEST)
        record = NIVRecommendation.objects.create(
            patient_id=patient_id,
            mode=mode,
            ipap=float(ipap),
            epap=float(epap),
            indication=request.data.get('indication', ''),
        )
        return Response({"message": "NIV recommendation saved.", "patient_id": patient_id, "mode": record.mode}, status=status.HTTP_201_CREATED)


class EscalationCriteriaAPIView(APIView):
    """
    GET /api/patients/<patient_id>/escalation-criteria/
    Returns escalation assessment based on current clinical data.
    """
    def get(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        from patients.models import Vitals, ABGEntry
        latest_vitals = Vitals.objects.filter(patient_id=patient_id).order_by('-created_at').first()
        latest_abg = ABGEntry.objects.filter(patient_id=patient_id).order_by('-created_at').first()
        escalation_triggers = []
        criteria_met = False

        if latest_vitals:
            if latest_vitals.spo2 < 85:
                escalation_triggers.append("SpO2 < 85% — Critical hypoxaemia")
                criteria_met = True
            if latest_vitals.resp_rate > 35:
                escalation_triggers.append("Respiratory rate > 35 breaths/min")
                criteria_met = True

        if latest_abg:
            if latest_abg.ph < 7.25:
                escalation_triggers.append("pH < 7.25 — Severe respiratory acidosis")
                criteria_met = True
            if latest_abg.paco2 > 70:
                escalation_triggers.append("PaCO2 > 70 mmHg — Severe hypercapnia")
                criteria_met = True

        EscalationCriteria.objects.create(
            patient_id=patient_id, criteria_met=criteria_met, details=str(escalation_triggers)
        )

        return Response({
            "patient_id": patient_id,
            "criteria_met": criteria_met,
            "escalation_triggers": escalation_triggers,
            "recommendation": "Consider ICU escalation / NIV." if criteria_met else "Continue current management.",
        }, status=status.HTTP_200_OK)


class ScheduleReassessmentAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/schedule-reassessment/
    POST /api/patients/<patient_id>/schedule-reassessment/
    Body: { interval: "30m"|"1h"|"2h"|"4h" }
    """
    VALID_INTERVALS = ['30m', '1h', '2h', '4h']

    def get(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        records = ScheduleReassessment.objects.filter(patient_id=patient_id).order_by('-created_at').values()
        return Response({"patient_id": patient_id, "reassessments": list(records)}, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        interval = request.data.get('interval')
        if interval not in self.VALID_INTERVALS:
            return Response({"error": f"interval must be one of: {', '.join(self.VALID_INTERVALS)}"}, status=status.HTTP_400_BAD_REQUEST)
        interval_map = {'30m': 30, '1h': 60, '2h': 120, '4h': 240}
        from datetime import timedelta
        scheduled_at = timezone.now() + timedelta(minutes=interval_map[interval])
        record = ScheduleReassessment.objects.create(
            patient_id=patient_id, interval=interval, scheduled_at=scheduled_at
        )
        return Response({
            "message": f"Reassessment scheduled in {interval}.",
            "patient_id": patient_id,
            "interval": record.interval,
            "scheduled_at": record.scheduled_at,
        }, status=status.HTTP_201_CREATED)


class UrgentActionAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/urgent-action/
    POST /api/patients/<patient_id>/urgent-action/
    Body: { action_type, description }
    """
    def get(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        records = UrgentAction.objects.filter(patient_id=patient_id).order_by('-created_at').values()
        return Response({"patient_id": patient_id, "urgent_actions": list(records)}, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        patient, err = get_patient_or_404(patient_id)
        if err:
            return err
        action_type = request.data.get('action_type')
        if not action_type:
            return Response({"error": "action_type is required."}, status=status.HTTP_400_BAD_REQUEST)
        record = UrgentAction.objects.create(
            patient_id=patient_id,
            action_type=action_type,
            description=request.data.get('description', ''),
            status='pending',
        )
        return Response({
            "message": "Urgent action logged.",
            "patient_id": patient_id,
            "action_type": record.action_type,
            "status": record.status,
        }, status=status.HTTP_201_CREATED)
