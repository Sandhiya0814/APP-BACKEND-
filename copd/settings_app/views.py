from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class SettingsAPIView(APIView):
    """
    GET /api/settings/
    Returns app configuration metadata.
    """
    def get(self, request):
        return Response({
            "app_name": "CDSS COPD",
            "version": "1.0.0",
            "description": "Clinical Decision Support System for Oxygen Therapy in COPD Patients",
            "settings": {
                "spo2_target_min": 88,
                "spo2_target_max": 92,
                "critical_spo2_threshold": 88,
                "warning_spo2_threshold": 92,
                "reassessment_intervals": ["30m", "1h", "2h", "4h"],
                "supported_devices": ["Venturi Mask", "Nasal Cannula", "High-Flow Nasal Cannula", "Non-Rebreather Mask"],
            }
        }, status=status.HTTP_200_OK)


class ClinicalGuidelinesAPIView(APIView):
    """
    GET /api/clinical-guidelines/
    Returns COPD clinical guidelines for reference in the app.
    """
    def get(self, request):
        return Response({
            "guidelines": {
                "oxygen_therapy": {
                    "title": "COPD Oxygen Therapy Guidelines",
                    "target_spo2": "88–92%",
                    "rationale": "Controlled oxygen therapy targets 88–92% SpO2 to avoid hypercapnia and oxygen toxicity in COPD patients (GOLD Guidelines).",
                    "gold_classification": {
                        "GOLD1": "FEV1 ≥ 80% predicted — Mild",
                        "GOLD2": "50% ≤ FEV1 < 80% predicted — Moderate",
                        "GOLD3": "30% ≤ FEV1 < 50% predicted — Severe",
                        "GOLD4": "FEV1 < 30% predicted — Very Severe"
                    },
                    "escalation_criteria": [
                        "SpO2 < 85% despite optimal oxygen therapy",
                        "RR > 35 breaths/min",
                        "pH < 7.25 with PaCO2 > 60 mmHg",
                        "Decreased level of consciousness",
                        "Haemodynamic instability"
                    ],
                    "niv_indications": [
                        "pH < 7.35 with PaCO2 > 45 mmHg",
                        "Moderate-to-severe dyspnoea with RR > 25 breaths/min",
                        "Failed optimal oxygen therapy"
                    ]
                },
                "abg_normal_values": {
                    "ph": "7.35–7.45",
                    "pao2": "75–100 mmHg",
                    "paco2": "35–45 mmHg",
                    "hco3": "22–26 mEq/L",
                    "fio2_room_air": "0.21"
                }
            }
        }, status=status.HTTP_200_OK)


class HelpSupportAPIView(APIView):
    """
    GET  /api/help-support/
    POST /api/help-support/ — submit a support request
    """
    def get(self, request):
        return Response({
            "contact": {
                "email": "support@cdss.com",
                "phone": "+91-XXXXXXXXXX",
                "hours": "Monday–Friday, 9 AM – 6 PM IST"
            },
            "faq": [
                {"question": "How is patient status determined?", "answer": "Patient status (critical/warning/stable) is auto-updated based on SpO2 when vitals are recorded."},
                {"question": "What is the SpO2 target for COPD?", "answer": "Target SpO2 is 88–92% for COPD patients to avoid hypercapnia."},
                {"question": "When should NIV be considered?", "answer": "NIV should be considered when pH < 7.35 and PaCO2 > 45 mmHg."},
            ]
        }, status=status.HTTP_200_OK)

    def post(self, request):
        name = request.data.get('name')
        email = request.data.get('email')
        issue = request.data.get('issue')
        if not (name and email and issue):
            return Response({"error": "name, email, and issue are required."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "message": "Support request received. We will contact you within 24 hours.",
            "ticket_id": f"CDSS-{name[:3].upper()}-001",
        }, status=status.HTTP_200_OK)
