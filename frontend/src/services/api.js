import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Documents API
export const documentsApi = {
  list: (params) => api.get('/documents/', { params }),
  get: (id) => api.get(`/documents/${id}/`),
  upload: (formData, onProgress) => 
    api.post('/documents/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percent)
        }
      },
    }),
  bulkUpload: (formData) => 
    api.post('/documents/bulk_upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  process: (id) => api.post(`/documents/${id}/process/`),
  processAllPending: () => api.post('/documents/process_all_pending/'),
  delete: (id) => api.delete(`/documents/${id}/`),
}

// Patients API
export const patientsApi = {
  list: (params) => api.get('/patients/', { params }),
  get: (id) => api.get(`/patients/${id}/`),
  export: (params, format = 'csv') => 
    api.get('/patients/export/', { 
      params: { ...params, format },
      responseType: 'blob',
    }),
  byDisease: () => api.get('/patients/by_disease/'),
}

// Diseases API
export const diseasesApi = {
  list: (params) => api.get('/patients/diseases/', { params }),
  get: (id) => api.get(`/patients/diseases/${id}/`),
}

// Analytics API
export const analyticsApi = {
  dashboard: () => api.get('/analytics/dashboard/'),
  diseases: (params) => api.get('/analytics/diseases/', { params }),
  locations: () => api.get('/analytics/locations/'),
  age: () => api.get('/analytics/age/'),
}

export default api
