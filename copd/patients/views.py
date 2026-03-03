from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Patient, BaselineDetails, GoldClassification, SpirometryData,
    GasExchangeHistory, CurrentSymptoms, Vitals, ABGEntry, ReassessmentChecklist
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
                dob=serializer.validated_data['dob'],
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
        filter_status = request.query_params.get('status', None)
        if filter_status and filter_status in ['critical', 'warning', 'stable']:
            patients = Patient.objects.filter(status=filter_status)
        else:
            patients = Patient.objects.all()
        data = patients.values('id', 'full_name', 'dob', 'sex', 'ward', 'bed_number', 'status', 'created_at')
        total = Patient.objects.count()
        critical = Patient.objects.filter(status='critical').count()
        warning = Patient.objects.filter(status='warning').count()
        stable = Patient.objects.filter(status='stable').count()
        return Response({
            "total_patients": total,
            "critical_count": critical,
            "warning_count": warning,
            "stable_count": stable,
            "patients": list(data),
        }, status=status.HTTP_200_OK)


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

        # Get latest records
        latest_vitals = patient.vitals.order_by('-created_at').first()
        latest_abg = patient.abg_entries.order_by('-created_at').first()
        latest_symptoms = patient.symptoms.order_by('-created_at').first()
        latest_gold = patient.gold_classifications.order_by('-created_at').first()

        vitals_data = None
        if latest_vitals:
            vitals_data = {
                "spo2": latest_vitals.spo2,
                "resp_rate": latest_vitals.resp_rate,
                "heart_rate": latest_vitals.heart_rate,
                "temperature": latest_vitals.temperature,
                "bp": latest_vitals.bp,
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
                "mmrc_grade": latest_symptoms.mmrc_grade,
                "cough": latest_symptoms.cough,
                "sputum": latest_symptoms.sputum,
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


# ──────────────────────────────────────────────────────────────────────────────
# Baseline Details
# ──────────────────────────────────────────────────────────────────────────────

class BaselineDetailsAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/baseline/
    POST /api/patients/<patient_id>/baseline/
    Body: { has_previous_diagnosis }
    """
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
            baseline = BaselineDetails.objects.get(patient=patient)
            return Response({
                "patient_id": patient_id,
                "has_previous_diagnosis": baseline.has_previous_diagnosis,
                "created_at": baseline.created_at,
            }, status=status.HTTP_200_OK)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
        except BaselineDetails.DoesNotExist:
            return Response({"error": "Baseline details not recorded yet."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
        has_prev = request.data.get('has_previous_diagnosis', None)
        if has_prev is None:
            return Response({"error": "has_previous_diagnosis is required."}, status=status.HTTP_400_BAD_REQUEST)
        baseline, created = BaselineDetails.objects.get_or_create(patient=patient)
        baseline.has_previous_diagnosis = has_prev
        baseline.save()
        return Response({
            "message": "Baseline details saved.",
            "patient_id": patient_id,
            "has_previous_diagnosis": baseline.has_previous_diagnosis,
        }, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# GOLD Classification
# ──────────────────────────────────────────────────────────────────────────────

class GoldClassificationAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/gold-classification/
    POST /api/patients/<patient_id>/gold-classification/
    Body: { gold_stage: 1|2|3|4 }
    """
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
        records = GoldClassification.objects.filter(patient=patient).order_by('-created_at').values()
        return Response({"patient_id": patient_id, "gold_classifications": list(records)}, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
        gold_stage = request.data.get('gold_stage')
        if gold_stage not in [1, 2, 3, 4]:
            return Response({"error": "gold_stage must be 1, 2, 3, or 4."}, status=status.HTTP_400_BAD_REQUEST)
        record = GoldClassification.objects.create(patient=patient, gold_stage=gold_stage)
        return Response({
            "message": "GOLD classification saved.",
            "patient_id": patient_id,
            "gold_stage": record.gold_stage,
            "recorded_at": record.created_at,
        }, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# Spirometry Data
# ──────────────────────────────────────────────────────────────────────────────

class SpirometryDataAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/spirometry/
    POST /api/patients/<patient_id>/spirometry/
    Body: { fev1, fev1_fvc }
    """
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
        records = SpirometryData.objects.filter(patient=patient).order_by('-created_at').values()
        return Response({"patient_id": patient_id, "spirometry_data": list(records)}, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        serializer = SpirometryDataInputSerializer(data={**request.data, 'patient_id': patient_id})
        if serializer.is_valid():
            try:
                patient = Patient.objects.get(id=patient_id)
            except Patient.DoesNotExist:
                return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
            record = SpirometryData.objects.create(
                patient=patient,
                fev1=serializer.validated_data['fev1'],
                fev1_fvc=serializer.validated_data['fev1_fvc'],
            )
            return Response({
                "message": "Spirometry data saved.",
                "patient_id": patient_id,
                "fev1": record.fev1,
                "fev1_fvc": record.fev1_fvc,
                "recorded_at": record.created_at,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────────────────────────────────────
# Gas Exchange History
# ──────────────────────────────────────────────────────────────────────────────

class GasExchangeHistoryAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/gas-exchange/
    POST /api/patients/<patient_id>/gas-exchange/
    Body: { has_hypoxemia: "yes"|"no"|"unknown", on_oxygen_therapy: true|false }
    """
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
        records = GasExchangeHistory.objects.filter(patient=patient).order_by('-created_at').values()
        return Response({"patient_id": patient_id, "gas_exchange_history": list(records)}, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
        has_hypoxemia = request.data.get('has_hypoxemia', 'unknown')
        on_oxygen_therapy = request.data.get('on_oxygen_therapy', False)
        if has_hypoxemia not in ['yes', 'no', 'unknown']:
            return Response({"error": "has_hypoxemia must be 'yes', 'no', or 'unknown'."}, status=status.HTTP_400_BAD_REQUEST)
        record = GasExchangeHistory.objects.create(
            patient=patient,
            has_hypoxemia=has_hypoxemia,
            on_oxygen_therapy=on_oxygen_therapy,
        )
        return Response({
            "message": "Gas exchange history saved.",
            "patient_id": patient_id,
            "has_hypoxemia": record.has_hypoxemia,
            "on_oxygen_therapy": record.on_oxygen_therapy,
            "recorded_at": record.created_at,
        }, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# Current Symptoms
# ──────────────────────────────────────────────────────────────────────────────

class CurrentSymptomsAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/symptoms/
    POST /api/patients/<patient_id>/symptoms/
    Body: { mmrc_grade, cough, sputum, wheezing, fever, chest_tightness }
    """
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
        records = CurrentSymptoms.objects.filter(patient=patient).order_by('-created_at').values()
        return Response({"patient_id": patient_id, "symptoms": list(records)}, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
        data = {**request.data, 'patient_id': patient_id}
        serializer = CurrentSymptomsInputSerializer(data=data)
        if serializer.is_valid():
            record = CurrentSymptoms.objects.create(
                patient=patient,
                mmrc_grade=serializer.validated_data['mmrc_grade'],
                cough=serializer.validated_data.get('cough', False),
                sputum=serializer.validated_data.get('sputum', False),
                wheezing=serializer.validated_data.get('wheezing', False),
                fever=serializer.validated_data.get('fever', False),
                chest_tightness=serializer.validated_data.get('chest_tightness', False),
            )
            return Response({
                "message": "Symptoms recorded successfully.",
                "patient_id": patient_id,
                "mmrc_grade": record.mmrc_grade,
                "symptoms": {
                    "cough": record.cough,
                    "sputum": record.sputum,
                    "wheezing": record.wheezing,
                    "fever": record.fever,
                    "chest_tightness": record.chest_tightness,
                },
                "recorded_at": record.created_at,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────────────────────────────────────
# Vitals
# ──────────────────────────────────────────────────────────────────────────────

class VitalsAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/vitals/
    POST /api/patients/<patient_id>/vitals/
    Body: { spo2, resp_rate, heart_rate, temperature, bp }
    Also auto-updates patient status based on SpO2 value.
    """
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
        records = Vitals.objects.filter(patient=patient).order_by('-created_at').values()
        return Response({"patient_id": patient_id, "vitals": list(records)}, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
        data = {**request.data, 'patient_id': patient_id}
        serializer = VitalsInputSerializer(data=data)
        if serializer.is_valid():
            spo2 = serializer.validated_data['spo2']
            record = Vitals.objects.create(
                patient=patient,
                spo2=spo2,
                resp_rate=serializer.validated_data['resp_rate'],
                heart_rate=serializer.validated_data['heart_rate'],
                temperature=serializer.validated_data['temperature'],
                bp=serializer.validated_data['bp'],
            )
            # Auto-update patient status based on SpO2
            if spo2 < 88:
                patient.status = 'critical'
            elif spo2 < 92:
                patient.status = 'warning'
            else:
                patient.status = 'stable'
            patient.save()

            return Response({
                "message": "Vitals recorded successfully.",
                "patient_id": patient_id,
                "spo2": record.spo2,
                "resp_rate": record.resp_rate,
                "heart_rate": record.heart_rate,
                "temperature": record.temperature,
                "bp": record.bp,
                "patient_status_updated_to": patient.status,
                "recorded_at": record.created_at,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────────────────────────────────────
# ABG Entry
# ──────────────────────────────────────────────────────────────────────────────

class ABGEntryAPIView(APIView):
    """
    GET  /api/patients/<patient_id>/abg-entry/
    POST /api/patients/<patient_id>/abg-entry/
    Body: { ph, pao2, paco2, hco3, fio2 }
    """
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
        records = ABGEntry.objects.filter(patient=patient).order_by('-created_at').values()
        return Response({"patient_id": patient_id, "abg_entries": list(records)}, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
        data = {**request.data, 'patient_id': patient_id}
        serializer = ABGEntryInputSerializer(data=data)
        if serializer.is_valid():
            record = ABGEntry.objects.create(
                patient=patient,
                ph=serializer.validated_data['ph'],
                pao2=serializer.validated_data['pao2'],
                paco2=serializer.validated_data['paco2'],
                hco3=serializer.validated_data['hco3'],
                fio2=serializer.validated_data['fio2'],
            )
            return Response({
                "message": "ABG data recorded successfully.",
                "patient_id": patient_id,
                "ph": record.ph,
                "pao2": record.pao2,
                "paco2": record.paco2,
                "hco3": record.hco3,
                "fio2": record.fio2,
                "recorded_at": record.created_at,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
