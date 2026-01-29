import axios, { AxiosInstance, AxiosProgressEvent } from 'axios'
import type {
  Document,
  DocumentListParams,
  Patient,
  PatientListParams,
  Disease,
  DashboardData,
  DiseaseAnalytics,
  LocationAnalytics,
  ProcessDocumentResponse,
  ProcessTextResponse,
  ProcessBatchResponse,
  ProcessingStatus,
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Documents API
export const documentsApi = {
  list: (params?: DocumentListParams) => 
    api.get<{ results: Document[]; count: number }>('/documents/', { params }),
  get: (id: number) => 
    api.get<Document>(`/documents/${id}/`),
  upload: (formData: FormData, onProgress?: (progress: number) => void) => 
    api.post<Document>('/documents/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percent)
        }
      },
    }),
  bulkUpload: (formData: FormData) => 
    api.post('/documents/bulk_upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  process: (id: number) => 
    api.post(`/documents/${id}/process/`),
  processAllPending: () => 
    api.post<{ processed: number }>('/documents/process_all_pending/'),
  delete: (id: number) => 
    api.delete(`/documents/${id}/`),
}

// Patients API
export const patientsApi = {
  list: (params?: PatientListParams) => 
    api.get<{ results: Patient[]; count: number }>('/patients/', { params }),
  get: (id: number) => 
    api.get<Patient>(`/patients/${id}/`),
  export: (params?: PatientListParams, format: 'csv' | 'excel' = 'csv') => 
    api.get('/patients/export/', { 
      params: { ...params, format },
      responseType: 'blob',
    }),
  byDisease: () => 
    api.get('/patients/by_disease/'),
}

// Diseases API
export const diseasesApi = {
  list: (params?: { page?: number; page_size?: number }) => 
    api.get<{ results: Disease[]; count: number }>('/patients/diseases/', { params }),
  get: (id: number) => 
    api.get<Disease>(`/patients/diseases/${id}/`),
}

// Analytics API
export const analyticsApi = {
  dashboard: () => 
    api.get<DashboardData>('/analytics/dashboard/'),
  diseases: (params?: { disease_id?: number }) => 
    api.get<DiseaseAnalytics | Disease[]>('/analytics/diseases/', { params }),
  locations: () => 
    api.get<LocationAnalytics[]>('/analytics/locations/'),
  age: () => 
    api.get<{ by_disease: Array<{ disease: string; age_groups: Record<string, number> }> }>('/analytics/age/'),
}

// Processing API - New unified processing pipeline
export const processingApi = {
  // Process a single document (file or text)
  processDocument: (formData: FormData, onProgress?: (progress: number) => void) =>
    api.post<ProcessDocumentResponse>('/process/document/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent: AxiosProgressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percent)
        }
      },
    }),
  
  // Process clinical text directly
  processText: (text: string, hospitalName = '', location = '') =>
    api.post<ProcessTextResponse>('/process/text/', { 
      text, 
      hospital_name: hospitalName, 
      location 
    }),
  
  // Process batch file (CSV/JSON)
  processBatch: (formData: FormData, onProgress?: (progress: number) => void) =>
    api.post<ProcessBatchResponse>('/process/batch/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent: AxiosProgressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percent)
        }
      },
    }),
  
  // Check processing service status
  status: () => 
    api.get<ProcessingStatus>('/process/status/'),
}

export default api
