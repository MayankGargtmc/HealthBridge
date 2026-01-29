// API Response Types
export interface ApiResponse<T> {
  data: T
  status: number
  statusText: string
}

// Document Types
export interface Document {
  id: number
  file_name: string
  file_type: string
  file_size: number
  upload_date: string
  status: 'pending' | 'processing' | 'processed' | 'failed'
  processed_at?: string
  error_message?: string
  patient_count?: number
}

export interface DocumentListParams {
  page?: number
  page_size?: number
  status?: string
  search?: string
}

// Patient Types
export interface Patient {
  id: number | string
  name: string
  phone?: string
  phone_number?: string
  age?: number
  gender?: 'male' | 'female' | 'other' | 'unknown'
  diseases?: string[]
  disease_list?: string[]
  hospital?: string
  hospital_clinic?: string
  clinic?: string
  address?: string
  location?: PatientLocation | string
  city?: string
  state?: string
  district?: string
  pincode?: string
  email?: string
  doctor_name?: string
  created_at: string
  updated_at?: string
}

export interface PatientLocation {
  address?: string
  city: string
  state: string
  pincode?: string
  coordinates?: {
    lat: number
    lng: number
  }
}

export interface PatientListParams {
  page?: number
  page_size?: number
  disease?: string
  location?: string
  search?: string
}

// Disease Types
export interface Disease {
  id: number
  name: string
  patient_count: number
  normalized_name: string
}

// Dashboard Types
export interface DashboardData {
  documents: {
    total: number
    processed: number
    pending: number
    failed: number
  }
  patients: {
    total: number
    with_contact: number
  }
  diseases: {
    unique_diseases: number
    total_diagnoses: number
  }
  gender_distribution: Array<{
    gender: string
    count: number
  }>
  top_diseases: Array<{
    name: string
    patient_count: number
  }>
}

export interface DiseaseAnalytics {
  disease: string
  patient_count?: number
  total_patients?: number
  age_distribution?: Array<{
    age_group: string
    count: number
  }>
  age_groups?: Array<{
    age_group: string
    count: number
  }>
  gender_distribution?: Array<{
    gender: string
    count: number
  }>
  location_distribution?: Array<{
    location: string
    count: number
  }>
}

export interface LocationAnalytics {
  location: string
  patient_count: number
  diseases: string[]
}

export interface AgeAnalytics {
  age_group: string
  count: number
  percentage: number
}

// Processing Types
export interface ProcessDocumentResponse {
  success: boolean
  document_id?: number
  patients?: Patient[]
  patients_created?: number
  diseases_found?: string[]
  processing_method?: string
  error?: string
}

export interface ProcessTextResponse {
  success: boolean
  patients?: Patient[]
  patients_created?: number
  diseases_found?: string[]
  error?: string
}

export interface ProcessBatchResponse {
  success: boolean
  processed_count: number
  failed_count: number
  errors?: string[]
}

export interface ProcessingStatus {
  status: 'healthy' | 'degraded' | 'down'
  services: {
    ocr?: boolean
    classifier?: boolean
    normalizer?: boolean
  }
}
