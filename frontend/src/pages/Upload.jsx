import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload as UploadIcon, File, X, CheckCircle, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { documentsApi } from '../services/api'

const DOCUMENT_TYPES = [
  { value: 'handwritten', label: 'Handwritten Prescription' },
  { value: 'printed_lab', label: 'Printed Lab Report' },
  { value: 'clinical_db', label: 'Clinical Database Export' },
  { value: 'other', label: 'Other' },
]

export default function Upload() {
  const [files, setFiles] = useState([])
  const [documentType, setDocumentType] = useState('printed_lab')
  const [hospitalName, setHospitalName] = useState('')
  const [location, setLocation] = useState('')
  const [processAfterUpload, setProcessAfterUpload] = useState(true)
  
  const queryClient = useQueryClient()

  const uploadMutation = useMutation({
    mutationFn: async ({ file, process }) => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('document_type', documentType)
      formData.append('hospital_clinic_name', hospitalName)
      formData.append('source_location', location)
      
      const url = process ? '?process=true' : ''
      const response = await documentsApi.upload(formData)
      
      // If process flag is set, trigger processing
      if (process && response.data?.id) {
        await documentsApi.process(response.data.id)
      }
      
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const onDrop = useCallback((acceptedFiles) => {
    const newFiles = acceptedFiles.map(file => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      status: 'pending', // pending, uploading, success, error
      progress: 0,
    }))
    setFiles(prev => [...prev, ...newFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg'],
    },
    maxSize: 10 * 1024 * 1024, // 10MB
  })

  const removeFile = (id) => {
    setFiles(prev => prev.filter(f => f.id !== id))
  }

  const uploadFiles = async () => {
    for (const fileItem of files) {
      if (fileItem.status === 'success') continue
      
      setFiles(prev => 
        prev.map(f => f.id === fileItem.id ? { ...f, status: 'uploading' } : f)
      )
      
      try {
        await uploadMutation.mutateAsync({ 
          file: fileItem.file, 
          process: processAfterUpload 
        })
        
        setFiles(prev => 
          prev.map(f => f.id === fileItem.id ? { ...f, status: 'success' } : f)
        )
        toast.success(`Uploaded ${fileItem.file.name}`)
      } catch (error) {
        setFiles(prev => 
          prev.map(f => f.id === fileItem.id ? { ...f, status: 'error' } : f)
        )
        toast.error(`Failed to upload ${fileItem.file.name}`)
      }
    }
  }

  const clearCompleted = () => {
    setFiles(prev => prev.filter(f => f.status !== 'success'))
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Upload Documents</h1>
        <p className="text-gray-500">Upload medical documents for processing</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Area */}
        <div className="lg:col-span-2">
          <div className="card">
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
                    Supports PDF, PNG, JPG (max 10MB each)
                  </p>
                </>
              )}
            </div>

            {/* File List */}
            {files.length > 0 && (
              <div className="mt-6">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="font-medium">Files to upload</h3>
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
                      className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
                    >
                      <File className="h-5 w-5 text-gray-400" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {fileItem.file.name}
                        </p>
                        <p className="text-xs text-gray-400">
                          {(fileItem.file.size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                      {fileItem.status === 'uploading' && (
                        <Loader2 className="h-5 w-5 text-primary-600 animate-spin" />
                      )}
                      {fileItem.status === 'success' && (
                        <CheckCircle className="h-5 w-5 text-green-600" />
                      )}
                      {fileItem.status === 'error' && (
                        <span className="text-xs text-red-600">Failed</span>
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
                  onClick={uploadFiles}
                  disabled={uploadMutation.isPending || files.every(f => f.status === 'success')}
                  className="btn-primary w-full mt-4 disabled:opacity-50"
                >
                  {uploadMutation.isPending ? 'Uploading...' : 'Upload All Files'}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Settings */}
        <div className="card h-fit">
          <h3 className="font-medium mb-4">Upload Settings</h3>
          
          <div className="space-y-4">
            <div>
              <label className="label">Document Type</label>
              <select 
                value={documentType}
                onChange={(e) => setDocumentType(e.target.value)}
                className="input"
              >
                {DOCUMENT_TYPES.map(type => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

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
              <label className="label">Source Location</label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="input"
                placeholder="e.g., Mumbai, Maharashtra"
              />
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="processAfterUpload"
                checked={processAfterUpload}
                onChange={(e) => setProcessAfterUpload(e.target.checked)}
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <label htmlFor="processAfterUpload" className="text-sm text-gray-700">
                Process immediately after upload
              </label>
            </div>
          </div>

          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-800 mb-2">Supported Inputs</h4>
            <ul className="text-sm text-blue-700 space-y-1">
              <li>• Handwritten prescriptions (PDF/Image)</li>
              <li>• Printed lab reports</li>
              <li>• Clinical database exports</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
