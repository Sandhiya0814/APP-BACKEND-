from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Patient, BaselineDetails, GoldClassification, SpirometryData,
    GasExchangeHistory, CurrentSymptoms, Vitals, AbgEntry, ReassessmentChecklist
)
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
    Calculates patient risk based on vitals and ABG data.
    """
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

        latest_vitals = Vitals.objects.filter(patient_id=patient.id).order_by('-created_at').first()
        latest_abg = AbgEntry.objects.filter(patient_id=patient.id).order_by('-created_at').first()

        risk_level = "STABLE"
        confidence_score = 90
        key_factors = []

        spo2 = latest_vitals.spo2 if latest_vitals and latest_vitals.spo2 is not None else None
        rr = latest_vitals.respiratory_rate if latest_vitals and latest_vitals.respiratory_rate is not None else None
        ph = latest_abg.ph if latest_abg and latest_abg.ph is not None else None
        pco2 = latest_abg.paco2 if latest_abg and latest_abg.paco2 is not None else None

        # Check conditions
        is_critical = False
        is_warning = False

        if ph is not None and ph < 7.35:
            key_factors.append({"factor": "Acidosis (pH < 7.35)", "level": "Critical"})
            is_critical = True
        elif ph is not None and ph > 7.45:
            key_factors.append({"factor": "Alkalosis (pH > 7.45)", "level": "Warning"})
            is_warning = True

        if pco2 is not None and pco2 > 45:
            level = "Critical" if (ph is not None and ph < 7.35) else "Warning"
            key_factors.append({"factor": f"Hypercapnia (pCO2: {pco2})", "level": level})
            if pco2 > 50:
                is_critical = True
            else:
                is_warning = True

        if spo2 is not None:
            if spo2 < 88:
                key_factors.append({"factor": f"Hypoxemia (SpO2: {spo2}%)", "level": "Critical"})
                is_critical = True
            elif spo2 <= 92:
                key_factors.append({"factor": f"Low Oxygen (SpO2: {spo2}%)", "level": "Warning"})
                is_warning = True

        if rr is not None and rr > 24:
            key_factors.append({"factor": f"Tachypnea (RR: {rr})", "level": "Critical"})
            is_critical = True

        # Determine overall risk
        if is_critical:
            risk_level = "HIGH RISK"
            confidence_score = 92
        elif is_warning:
            risk_level = "WARNING"
            confidence_score = 85
        else:
            risk_level = "STABLE"
            confidence_score = 95
            key_factors.append({"factor": "All parameters within normal limits", "level": "Stable"})

        return Response({
            "risk_level": risk_level,
            "confidence_score": confidence_score,
            "key_factors": key_factors
        }, status=status.HTTP_200_OK)


class CustomTrendAnalysisAPIView(APIView):
    """
    GET /api/patient/trend-analysis/<patient_id>/
    Calculates patient trend (Improving/Stable/Worsening) based on latest two vitals/ABGs.
    """
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

        # Fetch latest two records
        vitals_list = list(Vitals.objects.filter(patient_id=patient.id).order_by('-created_at')[:2])
        abg_list = list(AbgEntry.objects.filter(patient_id=patient.id).order_by('-created_at')[:2])

        trend_indicators = []
        worsening_count = 0
        improving_count = 0

        # PaCO2 Retention Trend
        pco2_status = "Stable"
        if len(abg_list) == 2:
            current_pco2 = abg_list[0].paco2
            previous_pco2 = abg_list[1].paco2
            if current_pco2 is not None and previous_pco2 is not None:
                if current_pco2 > previous_pco2:
                    pco2_status = "Rising"
                    worsening_count += 1
                elif current_pco2 < previous_pco2:
                    improving_count += 1
        
        trend_indicators.append({
            "factor": "PaCO2 Retention",
            "description": "Carbon dioxide levels",
            "status": pco2_status
        })

        # pH Balance Trend
        ph_status = "Stable"
        if len(abg_list) == 2:
            current_ph = abg_list[0].ph
            previous_ph = abg_list[1].ph
            if current_ph is not None and previous_ph is not None:
                if current_ph < previous_ph:
                    ph_status = "Dropping"
                    worsening_count += 1
                elif current_ph > previous_ph:
                    improving_count += 1
        
        trend_indicators.append({
            "factor": "pH Balance",
            "description": "Acidity levels",
            "status": ph_status
        })

        # SpO2 Stability Trend
        spo2_status = "Stable"
        if len(vitals_list) == 2:
            current_spo2 = vitals_list[0].spo2
            previous_spo2 = vitals_list[1].spo2
            if current_spo2 is not None and previous_spo2 is not None:
                if current_spo2 < previous_spo2:
                    spo2_status = "Unstable"
                    worsening_count += 1
                elif current_spo2 > previous_spo2:
                    improving_count += 1
        
        trend_indicators.append({
            "factor": "SpO2 Stability",
            "description": "Oxygen saturation",
            "status": spo2_status
        })

        # Determine overall trend status
        if worsening_count >= 2:
            trend_status = "WORSENING"
        elif improving_count > 0 and worsening_count == 0:
            trend_status = "IMPROVING"
        else:
            trend_status = "STABLE"

        return Response({
            "trend_status": trend_status,
            "trend_indicators": trend_indicators
        }, status=status.HTTP_200_OK)


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
