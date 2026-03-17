from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Patient, BaselineDetails, GoldClassification, SpirometryData,
    GasExchangeHistory, CurrentSymptoms, Vitals, AbgEntry, ReassessmentChecklist
)
from therapy.models import TrendAnalysis
from .serializers import (
    PatientSerializer, AddPatientSerializer,
    BaselineDetailsInputSerializer, GoldClassificationInputSerializer,
    SpirometryDataInputSerializer, GasExchangeHistoryInputSerializer,
    CurrentSymptomsInputSerializer, VitalsInputSerializer,
    ABGEntryInputSerializer, ReassessmentChecklistInputSerializer
)


# ──────────────────────────────────────────────────────────────────────────────
# Patient CRUD
# ──────────────────────────────────────────────────────────────────────────────

class AddPatientAPIView(APIView):
    """
    POST /api/patients/add/
    Body: { full_name, dob, sex, ward, bed_number, assigned_doctor_id, created_by_staff_id }
    """
    def post(self, request):
        serializer = AddPatientSerializer(data=request.data)
        if serializer.is_valid():
            patient = Patient.objects.create(
                full_name=serializer.validated_data['full_name'],
                dob=serializer.validated_data['date_of_birth'],
                sex=serializer.validated_data['sex'],
                ward=serializer.validated_data['ward'],
                bed_number=serializer.validated_data['bed_number'],
                assigned_doctor_id=serializer.validated_data.get('assigned_doctor_id'),
                created_by_staff_id=serializer.validated_data.get('created_by_staff_id'),
                status='stable',
            )
            return Response({
                "message": "Patient added successfully.",
                "patient_id": patient.id,
                "full_name": patient.full_name,
                "ward": patient.ward,
                "bed_number": patient.bed_number,
                "status": patient.status,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PatientListAPIView(APIView):
    """
    GET /api/patients/?status=critical|warning|stable
    Returns all patients, optionally filtered by status.
    """
    def get(self, request):
        from datetime import date
        filter_status = request.query_params.get('status', None)
        patients = Patient.objects.all()
        
        data = []
        for p in patients:
            # Fetch the single latest vitals record
            latest_vital = Vitals.objects.filter(patient_id=p.id).order_by('-created_at').first()
            
            spo2_val = latest_vital.spo2 if latest_vital and latest_vital.spo2 is not None else None
            rr_val = latest_vital.respiratory_rate if latest_vital and latest_vital.respiratory_rate is not None else None
            
            # Dynamic status based on SpO2
            # CRITICAL: < 88, WARNING: 88-92, STABLE: > 92
            if spo2_val is not None:
                if spo2_val < 88:
                    display_status = 'CRITICAL'
                elif spo2_val <= 92:
                    display_status = 'WARNING'
                else:
                    display_status = 'STABLE'
            else:
                display_status = p.status.upper() if p.status else "STABLE"

            data.append({
                "id": p.id,
                "patient_id": p.id, # Keep for backward compatibility with existing models
                "name": p.full_name,
                "ward_no": p.ward,
                "room_no": p.bed_number,
                "spo2": spo2_val if spo2_val is not None else "--",
                "respiratory_rate": rr_val if rr_val is not None else "--",
                "status": display_status
            })

        # Sorting: Critical -> Warning -> Stable
        status_priority = {'CRITICAL': 0, 'WARNING': 1, 'STABLE': 2}
        data.sort(key=lambda x: status_priority.get(x['status'], 3))

        return Response(data, status=status.HTTP_200_OK)


class PatientDetailAPIView(APIView):
    """
    GET /api/patients/<patient_id>/
    Returns full patient details with the most recent vitals, ABG, and symptoms.
    """
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get latest records (Use Model.objects.filter instead of reverse relation if no FK)
        latest_vitals = Vitals.objects.filter(patient_id=patient.id).order_by('-created_at').first()
        latest_abg = AbgEntry.objects.filter(patient_id=patient.id).order_by('-created_at').first()
        latest_symptoms = CurrentSymptoms.objects.filter(patient_id=patient.id).order_by('-created_at').first()
        latest_gold = GoldClassification.objects.filter(patient_id=patient.id).order_by('-created_at').first()

        vitals_data = None
        if latest_vitals:
            vitals_data = {
                "spo2": latest_vitals.spo2,
                "respiratory_rate": latest_vitals.respiratory_rate,
                "heart_rate": latest_vitals.heart_rate,
                "temperature": latest_vitals.temperature,
                "blood_pressure": latest_vitals.blood_pressure,
                "recorded_at": latest_vitals.created_at,
            }

        abg_data = None
        if latest_abg:
            abg_data = {
                "ph": latest_abg.ph,
                "pao2": latest_abg.pao2,
                "paco2": latest_abg.paco2,
                "hco3": latest_abg.hco3,
                "fio2": latest_abg.fio2,
                "recorded_at": latest_abg.created_at,
            }

        symptoms_data = None
        if latest_symptoms:
            symptoms_data = {
                "mmrc_grade": latest_symptoms.mmrc_score,
                "cough": latest_symptoms.increased_cough,
                "sputum": latest_symptoms.increased_sputum,
                "wheezing": latest_symptoms.wheezing,
                "fever": latest_symptoms.fever,
                "chest_tightness": latest_symptoms.chest_tightness,
                "recorded_at": latest_symptoms.created_at,
            }

        return Response({
            "patient_id": patient.id,
            "full_name": patient.full_name,
            "dob": patient.dob,
            "sex": patient.sex,
            "ward": patient.ward,
            "bed_number": patient.bed_number,
            "status": patient.status,
            "gold_stage": latest_gold.gold_stage if latest_gold else None,
            "latest_vitals": vitals_data,
            "latest_abg": abg_data,
            "latest_symptoms": symptoms_data,
            "created_at": patient.created_at,
        }, status=status.HTTP_200_OK)


class PatientDetailsForDoctorAPIView(APIView):
    """
    GET /api/patient/details/<patient_id>/
    Returns patient details for Doctor view:
    name, ward_no, room_no, spo2, respiratory_rate, heart_rate,
    abg_values, device, flow, status
    """
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

        from datetime import date
        age = (date.today() - patient.dob).days // 365 if patient.dob else None

        # Get latest vitals
        latest_vitals = Vitals.objects.filter(patient_id=patient.id).order_by('-created_at').first()

        # Get latest ABG entry
        latest_abg = AbgEntry.objects.filter(patient_id=patient.id).order_by('-created_at').first()

        # Dynamic status based on SpO2
        spo2_val = latest_vitals.spo2 if latest_vitals and latest_vitals.spo2 is not None else None
        rr_val = latest_vitals.respiratory_rate if latest_vitals and latest_vitals.respiratory_rate is not None else None
        hr_val = latest_vitals.heart_rate if latest_vitals and latest_vitals.heart_rate is not None else None

        if spo2_val is not None:
            if spo2_val < 88:
                display_status = 'CRITICAL'
            elif spo2_val <= 92:
                display_status = 'WARNING'
            else:
                display_status = 'STABLE'
        else:
            display_status = patient.status.upper() if patient.status else "STABLE"

        # ABG values
        abg_values = None
        if latest_abg:
            abg_values = {
                "ph": latest_abg.ph,
                "pao2": latest_abg.pao2,
                "paco2": latest_abg.paco2,
                "hco3": latest_abg.hco3,
                "fio2": latest_abg.fio2,
            }

        # Device and flow — attempt to read from therapy recommendation if available
        device = None
        flow = None
        try:
            from therapy.models import TherapyRecommendation
            latest_therapy = TherapyRecommendation.objects.filter(patient_id=patient.id).order_by('-created_at').first()
            if latest_therapy:
                device = getattr(latest_therapy, 'device', None)
                flow = getattr(latest_therapy, 'flow_rate', None)
        except Exception:
            pass

        return Response({
            "patient_id": patient.id,
            "name": patient.full_name,
            "age": age,
            "gender": patient.sex,
            "ward_no": patient.ward,
            "room_no": patient.bed_number,
            "diagnosis": "COPD Exacerbation",
            "spo2": spo2_val if spo2_val is not None else "--",
            "target_spo2": "88-92",
            "respiratory_rate": rr_val if rr_val is not None else "--",
            "heart_rate": hr_val if hr_val is not None else "--",
            "abg_values": abg_values,
            "device": device if device else "--",
            "flow": flow if flow else "--",
            "status": display_status,
        }, status=status.HTTP_200_OK)


class AIRiskAPIView(APIView):
    """
    GET /api/patient/ai-risk/<patient_id>/
    1. Fetches latest vitals and ABG for the patient
    2. Calculates risk_level + confidence_score
    3. Stores result in ai_analysis table
    4. Calculates trend values and stores in trend_analysis table
    5. Returns the computed data
    """
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

        # ── 1. Fetch latest vitals ──
        latest_vitals = Vitals.objects.filter(patient_id=patient.id).order_by('-created_at').first()
        # ── 2. Fetch latest ABG ──
        latest_abg = AbgEntry.objects.filter(patient_id=patient.id).order_by('-created_at').first()

        if not latest_vitals and not latest_abg:
            return Response({
                "risk_level": "LOW",
                "confidence_score": 0,
                "acidosis": 0,
                "hypercapnia": 0,
                "key_factors": [],
                "message": "No analysis data available for this patient"
            }, status=status.HTTP_200_OK)

        # Extract values (use safe defaults if missing)
        spo2 = latest_vitals.spo2 if latest_vitals and latest_vitals.spo2 is not None else 98
        respiratory_rate = latest_vitals.respiratory_rate if latest_vitals and latest_vitals.respiratory_rate is not None else 16
        ph = latest_abg.ph if latest_abg and latest_abg.ph is not None else 7.40
        paco2 = latest_abg.paco2 if latest_abg and latest_abg.paco2 is not None else 40

        # ── 3. AI Risk Calculation ──
        if spo2 < 90 or ph < 7.35 or paco2 > 45:
            risk_level = "HIGH"
            confidence_score = 90
        elif 90 <= spo2 <= 94:
            risk_level = "MODERATE"
            confidence_score = 70
        else:
            risk_level = "LOW"
            confidence_score = 50

        # Determine acidosis and hypercapnia flags
        acidosis = 1 if ph < 7.35 else 0
        hypercapnia = 1 if paco2 > 45 else 0

        # ── 4. Store AI result in ai_analysis table ──
        from therapy.models import AIAnalysis
        AIAnalysis.objects.create(
            patient_id=patient.id,
            risk_level=risk_level,
            confidence_score=confidence_score,
            acidosis=acidosis,
            hypercapnia=hypercapnia
        )

        # ── 5. Trend Analysis Calculation ──
        paco2_status = "Rising" if paco2 > 45 else "Normal"
        ph_status = "Dropping" if ph < 7.35 else "Normal"
        spo2_status = "Unstable" if spo2 < 92 else "Stable"

        # Overall status: Worsening if any critical condition
        if paco2 > 45 or ph < 7.35 or spo2 < 92:
            overall_status = "Worsening"
        else:
            overall_status = "Stable"

        # ── 6. Store Trend result in trend_analysis table ──
        TrendAnalysis.objects.create(
            patient_id=patient.id,
            overall_status=overall_status,
            paco2_status=paco2_status,
            ph_status=ph_status,
            spo2_status=spo2_status
        )

        # Build key_factors dynamically
        key_factors = []
        if acidosis == 1:
            key_factors.append({"factor": "Acidosis (pH < 7.35)", "level": "Critical"})
        if hypercapnia == 1:
            key_factors.append({"factor": "Hypercapnia (High CO\u2082)", "level": "Warning"})

        return Response({
            "risk_level": risk_level,
            "confidence_score": confidence_score,
            "acidosis": acidosis,
            "hypercapnia": hypercapnia,
            "key_factors": key_factors
        }, status=status.HTTP_200_OK)


class CustomTrendAnalysisAPIView(APIView):
    """
    GET /api/patient/trend-analysis/<patient_id>/
    Fetches the latest trend analysis record for the patient from the database.
    """
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

        latest_trend = TrendAnalysis.objects.filter(patient_id=patient.id).order_by('-recorded_at').first()

        if not latest_trend:
            return Response({
                "overall_status": "Stable",
                "paco2_status": "Normal",
                "ph_status": "Normal",
                "spo2_status": "Stable"
            }, status=status.HTTP_200_OK)

        return Response({
            "overall_status": latest_trend.overall_status,
            "paco2_status": latest_trend.paco2_status,
            "ph_status": latest_trend.ph_status,
            "spo2_status": latest_trend.spo2_status
        }, status=status.HTTP_200_OK)


class DecisionSupportAPIView(APIView):
    """
    GET /api/patient/decision-support/<patient_id>/
    Fetches latest AI analysis + Trend analysis for the patient
    and returns combined decision support data.
    """
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

        from therapy.models import AIAnalysis

        latest_ai = AIAnalysis.objects.filter(patient_id=patient.id).order_by('-recorded_at').first()
        latest_trend = TrendAnalysis.objects.filter(patient_id=patient.id).order_by('-recorded_at').first()

        if not latest_ai and not latest_trend:
            return Response({
                "has_data": False,
                "message": "No analysis data available for this patient"
            }, status=status.HTTP_200_OK)

        # AI Analysis data
        risk_level = latest_ai.risk_level if latest_ai else "LOW"
        confidence_score = latest_ai.confidence_score if latest_ai else 0
        acidosis = latest_ai.acidosis if latest_ai else 0
        hypercapnia = latest_ai.hypercapnia if latest_ai else 0

        # Trend data
        overall_status = latest_trend.overall_status if latest_trend else "Stable"
        paco2_status = latest_trend.paco2_status if latest_trend else "Normal"
        ph_status = latest_trend.ph_status if latest_trend else "Normal"
        spo2_status = latest_trend.spo2_status if latest_trend else "Stable"

        # Decision based on risk_level
        if risk_level == "HIGH":
            recommendation = "Critical: Immediate intervention required. Consider escalating to ICU or initiating NIV therapy."
            action_level = "CRITICAL"
        elif risk_level == "MODERATE":
            recommendation = "Warning: Close monitoring required. Adjust oxygen therapy and reassess within 1 hour."
            action_level = "WARNING"
        else:
            recommendation = "Normal: Continue current monitoring protocol. Reassess at next scheduled interval."
            action_level = "NORMAL"

        return Response({
            "has_data": True,
            "risk_level": risk_level,
            "confidence_score": confidence_score,
            "acidosis": acidosis,
            "hypercapnia": hypercapnia,
            "overall_status": overall_status,
            "paco2_status": paco2_status,
            "ph_status": ph_status,
            "spo2_status": spo2_status,
            "recommendation": recommendation,
            "action_level": action_level
        }, status=status.HTTP_200_OK)

class ClinicalReviewAPIView(APIView):
    """
    GET  /api/patient/clinical-review/<patient_id>/
         Fetches latest vitals + ABG, computes recommended device.
    POST /api/patient/clinical-review/<patient_id>/
         Saves accept/override decision into review_recommendation table.
         Body: { device, fio2, flow_rate, decision: "accepted"|"override", override_reason }
    """
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

        latest_vitals = Vitals.objects.filter(patient_id=patient.id).order_by('-created_at').first()
        latest_abg = AbgEntry.objects.filter(patient_id=patient.id).order_by('-created_at').first()

        if not latest_vitals and not latest_abg:
            return Response({
                "has_data": False,
                "message": "No clinical data available"
            }, status=status.HTTP_200_OK)

        spo2 = latest_vitals.spo2 if latest_vitals and latest_vitals.spo2 is not None else 98

        if spo2 < 85:
            device = "Non-Rebreather Mask"
            fio2 = "60-90%"
            flow_rate = "10-15 L/min"
        elif spo2 <= 92:
            device = "Venturi Mask"
            fio2 = "28-35%"
            flow_rate = "4-8 L/min"
        else:
            device = "Nasal Cannula"
            fio2 = "24-28%"
            flow_rate = "1-4 L/min"

        return Response({
            "has_data": True,
            "recommended_device": device,
            "fio2": fio2,
            "flow_rate": flow_rate,
            "spo2": spo2
        }, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        device = data.get('device', '')
        fio2 = data.get('fio2', '')
        flow_rate = data.get('flow_rate', '')
        decision = data.get('decision', 'accepted')
        override_reason = data.get('override_reason', '')

        from therapy.models import ReviewRecommendation
        ReviewRecommendation.objects.create(
            patient_id=patient.id,
            device=device,
            fio2=fio2,
            flow_rate=flow_rate,
            decision=decision,
            override_reason=override_reason
        )

        return Response({"message": "Review recommendation saved successfully."}, status=status.HTTP_201_CREATED)


class ClinicalTherapyPlanAPIView(APIView):
    """
    GET /api/patient/clinical-therapy/<patient_id>/
    Fetches latest review_recommendation + AI analysis, computes therapy plan,
    stores in therapy_recommendation table, returns the plan.
    """
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

        from therapy.models import ReviewRecommendation as ReviewRec, AIAnalysis, TherapyRecommendation

        latest_rec = ReviewRec.objects.filter(patient_id=patient.id).order_by('-created_at').first()
        latest_ai = AIAnalysis.objects.filter(patient_id=patient.id).order_by('-recorded_at').first()

        if not latest_rec:
            return Response({
                "has_data": False,
                "message": "No recommendation data available"
            }, status=status.HTTP_200_OK)

        device = latest_rec.device
        fio2 = latest_rec.fio2
        flow_rate = latest_rec.flow_rate
        risk_level = latest_ai.risk_level if latest_ai else "LOW"

        # Target SpO2 logic
        if device == "Non-Rebreather Mask":
            target_spo2 = "92-96%"
        elif device == "Venturi Mask":
            target_spo2 = "88-92%"
        else:
            target_spo2 = "94-98%"

        # Next ABG logic
        if risk_level in ("HIGH", "MODERATE"):
            next_abg = "30 mins"
        else:
            next_abg = "1 hour"

        # Rationale
        rationale = "Patient shows " + risk_level + " risk. Maintain oxygen therapy via " + device + " and monitor closely."

        # Store therapy plan in therapy_recommendation table
        TherapyRecommendation.objects.create(
            patient_id=patient.id,
            device=device,
            fio2=fio2,
            flow_rate=flow_rate,
            target_spo2=target_spo2,
            next_abg=next_abg,
            rationale=rationale
        )

        return Response({
            "has_data": True,
            "device": device,
            "fio2": fio2,
            "flow_rate": flow_rate,
            "target_spo2": target_spo2,
            "next_abg_time": next_abg,
            "rationale": rationale,
            "risk_level": risk_level
        }, status=status.HTTP_200_OK)


class ClinicalReassessmentAPIView(APIView):
    """
    POST /api/patient/clinical-reassessment/<patient_id>/
    Body: { reassessment_time_minutes: 30|60|120|240 }
    Stores in schedule_reassessment table with due_time = NOW() + INTERVAL.
    """
    def post(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

        from therapy.models import ScheduleReassessment
        from django.utils import timezone
        import datetime

        minutes = request.data.get('reassessment_time_minutes', 60)
        try:
            minutes = int(minutes)
        except (ValueError, TypeError):
            minutes = 60

        due_time = timezone.now() + datetime.timedelta(minutes=minutes)

        ScheduleReassessment.objects.create(
            patient_id=patient.id,
            reassessment_minutes=minutes,
            due_time=due_time,
            status='pending'
        )

        return Response({
            "message": "Reassessment scheduled successfully.",
            "due_time": due_time.isoformat(),
            "reassessment_time_minutes": minutes
        }, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# Baseline Details
# ──────────────────────────────────────────────────────────────────────────────

class AddBaselineDetailsAPIView(APIView):
    """
    POST /api/baseline-details/add/
    Body: { patient_id, copd_history }
    """
    def post(self, request):
        patient_id = request.data.get("patient_id")
        copd_history = request.data.get("copd_history")

        # Validate required fields
        if not patient_id:
            return Response({"error": "patient_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not copd_history:
            return Response({"error": "copd_history is required."}, status=status.HTTP_400_BAD_REQUEST)

        BaselineDetails.objects.create(
            patient_id=patient_id,
            copd_history=copd_history
        )

        return Response({"message": "Baseline details saved successfully"}, status=status.HTTP_201_CREATED)



# ──────────────────────────────────────────────────────────────────────────────
# GOLD Classification
# ──────────────────────────────────────────────────────────────────────────────

class AddGoldClassificationAPIView(APIView):
    """
    POST /api/gold-classification/add/
    Body: { patient_id, gold_stage }
    """
    def post(self, request):
        patient_id = request.data.get("patient_id")
        gold_stage = request.data.get("gold_stage")

        if not patient_id:
            return Response({"error": "patient_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not gold_stage:
            return Response({"error": "gold_stage is required."}, status=status.HTTP_400_BAD_REQUEST)

        GoldClassification.objects.create(
            patient_id=patient_id,
            gold_stage=gold_stage
        )

        return Response({"message": "GOLD classification saved successfully"}, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# Spirometry Data
# ──────────────────────────────────────────────────────────────────────────────

class AddSpirometryAPIView(APIView):
    """
    POST /api/spirometry/add/
    Body: { patient_id, fev1_percent, fev1_fvc_ratio }
    """
    def post(self, request):
        patient_id = request.data.get("patient_id")
        fev1_percent = request.data.get("fev1_percent")
        fev1_fvc_ratio = request.data.get("fev1_fvc_ratio")

        if not patient_id:
            return Response({"error": "patient_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            fev1_percent = float(fev1_percent) if fev1_percent is not None else None
            fev1_fvc_ratio = float(fev1_fvc_ratio) if fev1_fvc_ratio is not None else None
        except ValueError:
            return Response({"error": "fev1_percent and fev1_fvc_ratio must be numbers."}, status=status.HTTP_400_BAD_REQUEST)

        if fev1_percent is None or fev1_fvc_ratio is None:
            return Response({"error": "fev1_percent and fev1_fvc_ratio are required."}, status=status.HTTP_400_BAD_REQUEST)

        SpirometryData.objects.create(
            patient_id=patient_id,
            fev1_percent=fev1_percent,
            fev1_fvc_ratio=fev1_fvc_ratio
        )

        return Response({"message": "Spirometry data saved successfully"}, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# Gas Exchange History
# ──────────────────────────────────────────────────────────────────────────────

class AddGasExchangeHistoryAPIView(APIView):
    """
    POST /api/gas-exchange-history/add/
    Body: { patient_id, chronic_hypoxemia, home_oxygen_use }
    """
    def post(self, request):
        patient_id = request.data.get("patient_id")
        chronic_hypoxemia = request.data.get("chronic_hypoxemia")
        home_oxygen_use = request.data.get("home_oxygen_use")

        if not patient_id:
            return Response({"error": "patient_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        GasExchangeHistory.objects.create(
            patient_id=patient_id,
            chronic_hypoxemia=chronic_hypoxemia,
            home_oxygen_use=home_oxygen_use
        )

        return Response({"message": "Gas exchange history saved successfully"}, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# Current Symptoms
# ──────────────────────────────────────────────────────────────────────────────

class AddCurrentSymptomsAPIView(APIView):
    """
    POST /api/current-symptoms/add/
    Body: { patient_id, mmrc_score, increased_cough, increased_sputum, wheezing, fever, chest_tightness }
    """
    def post(self, request):
        patient_id = request.data.get("patient_id")
        mmrc_score = request.data.get("mmrc_score")

        increased_cough = request.data.get("increased_cough", False)
        increased_sputum = request.data.get("increased_sputum", False)
        wheezing = request.data.get("wheezing", False)
        fever = request.data.get("fever", False)
        chest_tightness = request.data.get("chest_tightness", False)

        if not patient_id:
            return Response({"error": "patient_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        if mmrc_score is None:
            return Response({"error": "mmrc_score is required."}, status=status.HTTP_400_BAD_REQUEST)

        CurrentSymptoms.objects.create(
            patient_id=patient_id,
            mmrc_score=mmrc_score,
            increased_cough=increased_cough,
            increased_sputum=increased_sputum,
            wheezing=wheezing,
            fever=fever,
            chest_tightness=chest_tightness
        )

        return Response({"message": "Current symptoms saved successfully"}, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# Vitals
# ──────────────────────────────────────────────────────────────────────────────

class AddVitalsAPIView(APIView):
    """
    POST /api/vitals/add/
    Body: { patient_id, spo2, respiratory_rate, heart_rate, temperature, blood_pressure }
    """
    def post(self, request):
        patient_id = request.data.get("patient_id")
        spo2 = request.data.get("spo2")
        respiratory_rate = request.data.get("respiratory_rate")
        heart_rate = request.data.get("heart_rate")
        temperature = request.data.get("temperature")
        blood_pressure = request.data.get("blood_pressure")

        if not patient_id:
            return Response({"error": "patient_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        Vitals.objects.create(
            patient_id=patient_id,
            spo2=spo2,
            respiratory_rate=respiratory_rate,
            heart_rate=heart_rate,
            temperature=temperature,
            blood_pressure=blood_pressure
        )

        return Response({"message": "Vitals saved successfully"}, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# ABG Entry
# ──────────────────────────────────────────────────────────────────────────────

class AddAbgEntryAPIView(APIView):
    """
    POST /api/abg-entry/add/
    Body: { patient_id, ph, pao2, paco2, hco3, fio2 }
    """
    def post(self, request):
        patient_id = request.data.get("patient_id")
        ph = request.data.get("ph")
        pao2 = request.data.get("pao2")
        paco2 = request.data.get("paco2")
        hco3 = request.data.get("hco3")
        fio2 = request.data.get("fio2")

        if not patient_id:
            return Response({"error": "patient_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        AbgEntry.objects.create(
            patient_id=patient_id,
            ph=ph,
            pao2=pao2,
            paco2=paco2,
            hco3=hco3,
            fio2=fio2
        )

        return Response({"message": "ABG data saved successfully"}, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# Reassessment Checklist
# ──────────────────────────────────────────────────────────────────────────────

class ReassessmentChecklistAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/reassessment-checklist/
    POST /api/patients/<patient_id>/reassessment-checklist/
    Body: { spo2_checked, resp_rate_checked, consciousness_checked, device_fit_checked, abg_checked }
    """
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
        records = ReassessmentChecklist.objects.filter(patient=patient).order_by('-created_at').values()
        return Response({"patient_id": patient_id, "reassessments": list(records)}, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
        spo2 = request.data.get('spo2_checked', False)
        resp = request.data.get('resp_rate_checked', False)
        cons = request.data.get('consciousness_checked', False)
        dev = request.data.get('device_fit_checked', False)
        abg = request.data.get('abg_checked', False)
        all_clear = all([spo2, resp, cons, dev, abg])
        record = ReassessmentChecklist.objects.create(
            patient=patient,
            spo2_checked=spo2,
            resp_rate_checked=resp,
            consciousness_checked=cons,
            device_fit_checked=dev,
            abg_checked=abg,
            all_clear=all_clear,
        )
        return Response({
            "message": "Reassessment checklist completed." if all_clear else "Reassessment checklist saved (incomplete).",
            "patient_id": patient_id,
            "all_clear": record.all_clear,
            "recorded_at": record.created_at,
        }, status=status.HTTP_201_CREATED)
