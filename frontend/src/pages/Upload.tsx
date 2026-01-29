import { useState, useCallback } from 'react'
import { useDropzone, } from 'react-dropzone'
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
import { Upload as UploadIcon, File, X, CheckCircle, Loader2, FileText, AlertCircle, Database } from 'lucide-react'
import toast from 'react-hot-toast'
import { processingApi } from '../services/api'
import type { ProcessDocumentResponse, ProcessTextResponse, ProcessBatchResponse } from '@/types'

const DOCUMENT_TYPES = [
  { value: 'auto', label: 'Auto-detect' },
  { value: 'prescription', label: 'Prescription (Handwritten/Printed)' },
  { value: 'lab_report', label: 'Lab Report' },
  { value: 'clinical_text', label: 'Clinical Notes' },
  { value: 'structured_data', label: 'Database Export (CSV/JSON)' },
] as const

type DocumentType = typeof DOCUMENT_TYPES[number]['value']
type TabType = 'file' | 'text' | 'batch'
type FileStatus = 'pending' | 'processing' | 'success' | 'error'

interface FileItem {
  file: File
  id: string
  status: FileStatus
  result: ProcessDocumentResponse | ProcessBatchResponse | null
}

export default function Upload() {
  const [files, setFiles] = useState<FileItem[]>([])
  const [documentType, setDocumentType] = useState<DocumentType>('auto')
  const [hospitalName, setHospitalName] = useState('')
  const [location, setLocation] = useState('')
  const [clinicalText, setClinicalText] = useState('')
  const [activeTab, setActiveTab] = useState<TabType>('file')
  const [processingResults, setProcessingResults] = useState<(ProcessDocumentResponse | ProcessTextResponse | ProcessBatchResponse)[]>([])
  
  const queryClient = useQueryClient()

  // Check processing service status
  const { data: statusData } = useQuery({
    queryKey: ['processingStatus'],
    queryFn: () => processingApi.status().then(res => res.data),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Process document mutation
  const processDocumentMutation = useMutation({
    mutationFn: async ({ file }: { file: File }) => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('document_type', documentType)
      formData.append('hospital_name', hospitalName)
      formData.append('location', location)
      
      const response = await processingApi.processDocument(formData)
      return response.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['patients'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setProcessingResults(prev => [...prev, data])
    },
  })

  // Process text mutation
  const processTextMutation = useMutation({
    mutationFn: async () => {
      const response = await processingApi.processText(clinicalText, hospitalName, location)
      return response.data
    },
    onSuccess: (data: ProcessTextResponse) => {
      queryClient.invalidateQueries({ queryKey: ['patients'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setProcessingResults(prev => [...prev, data])
      setClinicalText('')
      const patientsCount = data.patients_created || 0
      const diseasesCount = data.diseases_found?.length || 0
      toast.success(`Processed: ${patientsCount} patients, ${diseasesCount} diseases found`)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to process text')
    }
  })

  // Process batch mutation
  const processBatchMutation = useMutation({
    mutationFn: async ({ file }: { file: File }) => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('hospital_name', hospitalName)
      formData.append('location', location)
      
      const response = await processingApi.processBatch(formData)
      return response.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['patients'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setProcessingResults(prev => [...prev, data])
      toast.success(`Batch processed: ${data.processed_count}/${data.processed_count + data.failed_count} records`)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to process batch')
    }
  })

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: FileItem[] = acceptedFiles.map(file => ({
      file,
      id: Math.random().toString(36).substring(2, 9),
      status: 'pending' as FileStatus,
      result: null,
    }))
    setFiles(prev => [...prev, ...newFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: activeTab === 'batch' 
      ? { 'text/csv': ['.csv'], 'application/json': ['.json'] }
      : {
          'application/pdf': ['.pdf'],
          'image/*': ['.png', '.jpg', '.jpeg', '.webp'],
          'text/csv': ['.csv'],
          'application/json': ['.json'],
        },
    maxSize: 10 * 1024 * 1024,
  })

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id))
  }

  const processFiles = async () => {
    for (const fileItem of files) {
      if (fileItem.status === 'success') continue
      
      setFiles(prev => 
        prev.map(f => f.id === fileItem.id ? { ...f, status: 'processing' as FileStatus } : f)
      )
      
      try {
        let result: ProcessDocumentResponse | ProcessBatchResponse
        
        // Check if it's a batch file
        const isBatchFile = fileItem.file.name.endsWith('.csv') || fileItem.file.name.endsWith('.json')
        
        if (isBatchFile || activeTab === 'batch') {
          result = await processBatchMutation.mutateAsync({ file: fileItem.file })
        } else {
          result = await processDocumentMutation.mutateAsync({ file: fileItem.file })
        }
        
        setFiles(prev => 
          prev.map(f => f.id === fileItem.id ? { ...f, status: 'success' as FileStatus, result } : f)
        )
        
        const diseasesCount = (result as ProcessDocumentResponse).diseases_found?.length || 0
        const patientsCount = (result as ProcessDocumentResponse).patients_created || (result as ProcessBatchResponse).processed_count || 0
        toast.success(`Processed ${fileItem.file.name}: ${patientsCount} patients, ${diseasesCount} diseases`)
      } catch (error) {
        setFiles(prev => 
          prev.map(f => f.id === fileItem.id ? { ...f, status: 'error' as FileStatus, result: null } : f)
        )
        toast.error(`Failed to process ${fileItem.file.name}`)
      }
    }
  }

  const clearCompleted = () => {
    setFiles(prev => prev.filter(f => f.status !== 'success'))
  }

  const getFileIcon = (fileName: string) => {
    if (fileName.endsWith('.csv') || fileName.endsWith('.json')) {
      return <Database className="h-5 w-5 text-green-500" />
    }
    return <File className="h-5 w-5 text-gray-400" />
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Process Medical Documents</h1>
        <p className="text-gray-500">Extract patient data and diseases from medical records</p>
      </div>

      {/* Service Status Banner */}
      {statusData && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Processing Services</h3>
          <div className="flex flex-wrap gap-4">
            {Object.entries(statusData.services || {}).map(([name, status]) => (
              <div key={name} className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${status ? 'bg-green-500' : 'bg-yellow-500'}`} />
                <span className="text-sm text-gray-600 capitalize">{name.replace(/_/g, ' ')}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab('file')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'file' 
              ? 'bg-primary-600 text-white' 
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <UploadIcon className="h-4 w-4 inline mr-2" />
          Upload Files
        </button>
        <button
          onClick={() => setActiveTab('text')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'text' 
              ? 'bg-primary-600 text-white' 
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <FileText className="h-4 w-4 inline mr-2" />
          Clinical Text
        </button>
        <button
          onClick={() => setActiveTab('batch')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'batch' 
              ? 'bg-primary-600 text-white' 
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <Database className="h-4 w-4 inline mr-2" />
          Batch Import
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content Area */}
        <div className="lg:col-span-2">
          <div className="card">
            {/* File Upload Tab */}
            {(activeTab === 'file' || activeTab === 'batch') && (
              <>
                <div
                  {...getRootProps()}
                  className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                    isDragActive 
                      ? 'border-primary-500 bg-primary-50' 
                      : 'border-gray-300 hover:border-primary-400'
                  }`}
                >
                  <input {...getInputProps()} />
                  <UploadIcon className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                  {isDragActive ? (
                    <p className="text-primary-600">Drop the files here...</p>
                  ) : (
                    <>
                      <p className="text-gray-600 mb-2">
                        Drag & drop files here, or click to select
                      </p>
                      <p className="text-sm text-gray-400">
                        {activeTab === 'batch' 
                          ? 'Supports CSV, JSON (max 10MB)'
                          : 'Supports PDF, PNG, JPG, CSV, JSON (max 10MB)'
                        }
                      </p>
                    </>
                  )}
                </div>

                {/* File List */}
                {files.length > 0 && (
                  <div className="mt-6">
                    <div className="flex justify-between items-center mb-3">
                      <h3 className="font-medium">Files to process</h3>
                      <button 
                        onClick={clearCompleted}
                        className="text-sm text-gray-500 hover:text-gray-700"
                      >
                        Clear completed
                      </button>
                    </div>
                    <div className="space-y-2">
                      {files.map((fileItem) => (
                        <div 
                          key={fileItem.id}
                          className={`flex items-center gap-3 p-3 rounded-lg ${
                            fileItem.status === 'success' ? 'bg-green-50' :
                            fileItem.status === 'error' ? 'bg-red-50' : 'bg-gray-50'
                          }`}
                        >
                          {getFileIcon(fileItem.file.name)}
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">
                              {fileItem.file.name}
                            </p>
                            <p className="text-xs text-gray-400">
                              {(fileItem.file.size / 1024).toFixed(1)} KB
                              {(fileItem.result as ProcessDocumentResponse)?.processing_method && (
                                <span className="ml-2 text-primary-600">
                                  via {(fileItem.result as ProcessDocumentResponse).processing_method}
                                </span>
                              )}
                            </p>
                            {(fileItem.result as ProcessDocumentResponse)?.diseases_found && (fileItem.result as ProcessDocumentResponse).diseases_found!.length > 0 && (
                              <p className="text-xs text-green-600 mt-1">
                                Found: {(fileItem.result as ProcessDocumentResponse).diseases_found!.slice(0, 3).join(', ')}
                                {(fileItem.result as ProcessDocumentResponse).diseases_found!.length > 3 && '...'}
                              </p>
                            )}
                          </div>
                          {fileItem.status === 'processing' && (
                            <Loader2 className="h-5 w-5 text-primary-600 animate-spin" />
                          )}
                          {fileItem.status === 'success' && (
                            <CheckCircle className="h-5 w-5 text-green-600" />
                          )}
                          {fileItem.status === 'error' && (
                            <AlertCircle className="h-5 w-5 text-red-600" />
                          )}
                          {fileItem.status === 'pending' && (
                            <button 
                              onClick={() => removeFile(fileItem.id)}
                              className="p-1 hover:bg-gray-200 rounded"
                            >
                              <X className="h-4 w-4 text-gray-400" />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>

                    <button
                      onClick={processFiles}
                      disabled={
                        processDocumentMutation.isPending || 
                        processBatchMutation.isPending ||
                        files.every(f => f.status === 'success')
                      }
                      className="btn-primary w-full mt-4 disabled:opacity-50"
                    >
                      {(processDocumentMutation.isPending || processBatchMutation.isPending) 
                        ? 'Processing...' 
                        : 'Process All Files'
                      }
                    </button>
                  </div>
                )}
              </>
            )}

            {/* Clinical Text Tab */}
            {activeTab === 'text' && (
              <div>
                <label className="label">Enter Clinical Notes / Prescription Text</label>
                <textarea
                  value={clinicalText}
                  onChange={(e) => setClinicalText(e.target.value)}
                  rows={10}
                  className="input font-mono text-sm"
                  placeholder="Paste clinical notes, prescription details, or medical history here...

Example:
Patient: Ramesh Kumar, 45/M
Chief Complaint: Chest pain, breathlessness for 2 days
History: Known case of DM, HTN for 5 years
Diagnosis: Acute Coronary Syndrome
Treatment: Started on Aspirin, Clopidogrel, Atorvastatin"
                />
                <button
                  onClick={() => processTextMutation.mutate()}
                  disabled={processTextMutation.isPending || !clinicalText.trim()}
                  className="btn-primary w-full mt-4 disabled:opacity-50"
                >
                  {processTextMutation.isPending ? 'Processing...' : 'Process Clinical Text'}
                </button>
              </div>
            )}
          </div>

          {/* Results Summary */}
          {processingResults.length > 0 && (
            <div className="card mt-6">
              <h3 className="font-medium mb-4">Recent Processing Results</h3>
              <div className="space-y-3">
                {processingResults.slice(-5).reverse().map((result, idx) => (
                  <div key={idx} className="p-3 bg-gray-50 rounded-lg">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {(result as ProcessDocumentResponse | ProcessTextResponse).patients_created || (result as ProcessBatchResponse).processed_count || 0} patient(s) processed
                        </p>
                        <p className="text-xs text-gray-500">
                          Method: {(result as ProcessDocumentResponse).processing_method || 'N/A'}
                        </p>
                      </div>
                      <span className={`px-2 py-1 text-xs rounded ${
                        result.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {result.success ? 'Success' : 'Failed'}
                      </span>
                    </div>
                    {(result as ProcessDocumentResponse | ProcessTextResponse).diseases_found && (result as ProcessDocumentResponse | ProcessTextResponse).diseases_found!.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {(result as ProcessDocumentResponse | ProcessTextResponse).diseases_found!.map((disease, dIdx) => (
                          <span 
                            key={dIdx}
                            className="px-2 py-0.5 bg-primary-100 text-primary-700 text-xs rounded"
                          >
                            {disease}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Settings Sidebar */}
        <div className="card h-fit">
          <h3 className="font-medium mb-4">Processing Settings</h3>
          
          <div className="space-y-4">
            {activeTab === 'file' && (
              <div>
                <label className="label">Document Type</label>
                <select 
                  value={documentType}
                  onChange={(e) => setDocumentType(e.target.value as DocumentType)}
                  className="input"
                >
                  {DOCUMENT_TYPES.map(type => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div>
              <label className="label">Hospital/Clinic Name</label>
              <input
                type="text"
                value={hospitalName}
                onChange={(e) => setHospitalName(e.target.value)}
                className="input"
                placeholder="e.g., City Hospital"
              />
            </div>

            <div>
              <label className="label">Location</label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="input"
                placeholder="e.g., Mumbai, Maharashtra"
              />
            </div>
          </div>

          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-800 mb-2">
              {activeTab === 'file' && 'Supported Files'}
              {activeTab === 'text' && 'Clinical Text Tips'}
              {activeTab === 'batch' && 'Batch Format'}
            </h4>
            <ul className="text-sm text-blue-700 space-y-1">
              {activeTab === 'file' && (
                <>
                  <li>• Handwritten/printed prescriptions</li>
                  <li>• Lab reports (PDF/Image)</li>
                  <li>• Scanned medical documents</li>
                </>
              )}
              {activeTab === 'text' && (
                <>
                  <li>• Include patient name & demographics</li>
                  <li>• Mention diagnoses clearly</li>
                  <li>• Use standard abbreviations (DM, HTN)</li>
                </>
              )}
              {activeTab === 'batch' && (
                <>
                  <li>• CSV with headers: name, age, gender, diseases</li>
                  <li>• JSON array of patient objects</li>
                  <li>• Separate diseases with commas</li>
                </>
              )}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

