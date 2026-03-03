from rest_framework import serializers
from .models import (
    Patient, BaselineDetails, GoldClassification, SpirometryData,
    GasExchangeHistory, CurrentSymptoms, Vitals, ABGEntry, ReassessmentChecklist
)


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = '__all__'


class AddPatientSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255, error_messages={"required": "Full name is required."})
    dob = serializers.DateField(error_messages={"required": "Date of birth is required."})
    sex = serializers.ChoiceField(choices=['Male', 'Female', 'Other'], error_messages={"required": "Sex is required."})
    ward = serializers.CharField(max_length=100, error_messages={"required": "Ward is required."})
    bed_number = serializers.CharField(max_length=50, error_messages={"required": "Bed number is required."})
    assigned_doctor_id = serializers.IntegerField(required=False, allow_null=True)
    created_by_staff_id = serializers.IntegerField(required=False, allow_null=True)


class BaselineDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineDetails
        fields = '__all__'


class BaselineDetailsInputSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(error_messages={"required": "patient_id is required."})
    has_previous_diagnosis = serializers.BooleanField(error_messages={"required": "has_previous_diagnosis is required."})


class GoldClassificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoldClassification
        fields = '__all__'


class GoldClassificationInputSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(error_messages={"required": "patient_id is required."})
    gold_stage = serializers.ChoiceField(choices=[1, 2, 3, 4], error_messages={"required": "gold_stage is required."})


class SpirometryDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpirometryData
        fields = '__all__'


class SpirometryDataInputSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(error_messages={"required": "patient_id is required."})
    fev1 = serializers.FloatField(error_messages={"required": "FEV1 is required."})
    fev1_fvc = serializers.FloatField(error_messages={"required": "FEV1/FVC ratio is required."})


class GasExchangeHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GasExchangeHistory
        fields = '__all__'


class GasExchangeHistoryInputSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(error_messages={"required": "patient_id is required."})
    has_hypoxemia = serializers.ChoiceField(choices=['yes', 'no', 'unknown'], error_messages={"required": "has_hypoxemia is required."})
    on_oxygen_therapy = serializers.BooleanField(error_messages={"required": "on_oxygen_therapy is required."})


class CurrentSymptomsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrentSymptoms
        fields = '__all__'


class CurrentSymptomsInputSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(error_messages={"required": "patient_id is required."})
    mmrc_grade = serializers.ChoiceField(choices=[0, 1, 2, 3, 4], error_messages={"required": "mmrc_grade is required."})
    cough = serializers.BooleanField(default=False)
    sputum = serializers.BooleanField(default=False)
    wheezing = serializers.BooleanField(default=False)
    fever = serializers.BooleanField(default=False)
    chest_tightness = serializers.BooleanField(default=False)


class VitalsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vitals
        fields = '__all__'


class VitalsInputSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(error_messages={"required": "patient_id is required."})
    spo2 = serializers.FloatField(error_messages={"required": "SpO2 is required."})
    resp_rate = serializers.IntegerField(error_messages={"required": "Respiratory rate is required."})
    heart_rate = serializers.IntegerField(error_messages={"required": "Heart rate is required."})
    temperature = serializers.FloatField(error_messages={"required": "Temperature is required."})
    bp = serializers.CharField(max_length=20, error_messages={"required": "Blood pressure is required."})


class ABGEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ABGEntry
        fields = '__all__'


class ABGEntryInputSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(error_messages={"required": "patient_id is required."})
    ph = serializers.FloatField(error_messages={"required": "pH is required."})
    pao2 = serializers.FloatField(error_messages={"required": "PaO2 is required."})
    paco2 = serializers.FloatField(error_messages={"required": "PaCO2 is required."})
    hco3 = serializers.FloatField(error_messages={"required": "HCO3 is required."})
    fio2 = serializers.FloatField(error_messages={"required": "FiO2 is required."})


class ReassessmentChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReassessmentChecklist
        fields = '__all__'


class ReassessmentChecklistInputSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(error_messages={"required": "patient_id is required."})
    spo2_checked = serializers.BooleanField(default=False)
    resp_rate_checked = serializers.BooleanField(default=False)
    consciousness_checked = serializers.BooleanField(default=False)
    device_fit_checked = serializers.BooleanField(default=False)
    abg_checked = serializers.BooleanField(default=False)
