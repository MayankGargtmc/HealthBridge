from rest_framework import serializers
from .models import Patient, Disease, PatientDisease


class DiseaseSerializer(serializers.ModelSerializer):
    patient_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Disease
        fields = ['id', 'name', 'category', 'icd_code', 'description', 'patient_count']
    
    def get_patient_count(self, obj):
        return obj.patients.count()


class PatientDiseaseSerializer(serializers.ModelSerializer):
    disease_name = serializers.CharField(source='disease.name', read_only=True)
    
    class Meta:
        model = PatientDisease
        fields = ['id', 'disease', 'disease_name', 'diagnosis_date', 'severity', 'status']


class PatientSerializer(serializers.ModelSerializer):
    diseases = DiseaseSerializer(many=True, read_only=True)
    disease_list = serializers.ListField(read_only=True)
    age_group = serializers.CharField(read_only=True)
    patient_diseases = PatientDiseaseSerializer(
        source='patientdisease_set', 
        many=True, 
        read_only=True
    )
    
    class Meta:
        model = Patient
        fields = [
            'id', 'name', 'age', 'age_group', 'gender', 'phone_number', 'email',
            'address', 'city', 'district', 'state', 'pincode', 'location',
            'hospital_clinic', 'doctor_name', 'diseases', 'disease_list',
            'patient_diseases', 'notes', 'economic_status',
            'created_at', 'updated_at'
        ]


class PatientListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views."""
    disease_list = serializers.ListField(read_only=True)
    age_group = serializers.CharField(read_only=True)
    
    class Meta:
        model = Patient
        fields = [
            'id', 'name', 'age', 'age_group', 'gender', 'phone_number',
            'location', 'hospital_clinic', 'disease_list', 'created_at'
        ]


class PatientExportSerializer(serializers.ModelSerializer):
    """Serializer for CSV/Excel export."""
    diseases = serializers.SerializerMethodField()
    age_group = serializers.CharField(read_only=True)
    
    class Meta:
        model = Patient
        fields = [
            'name', 'age', 'age_group', 'gender', 'phone_number', 'email',
            'address', 'city', 'district', 'state', 'pincode', 'location',
            'hospital_clinic', 'doctor_name', 'diseases', 'economic_status',
            'created_at'
        ]
    
    def get_diseases(self, obj):
        return ', '.join(obj.disease_list)
