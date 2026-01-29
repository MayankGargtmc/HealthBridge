import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  FileText, 
  Clock, 
  CheckCircle, 
  XCircle, 
  RefreshCw,
  Trash2,
  Eye
} from 'lucide-react'
import toast from 'react-hot-toast'
import { documentsApi } from '../services/api'

const STATUS_CONFIG = {
  pending: { icon: Clock, color: 'text-amber-600', bg: 'bg-amber-50', label: 'Pending' },
  processing: { icon: RefreshCw, color: 'text-blue-600', bg: 'bg-blue-50', label: 'Processing' },
  completed: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50', label: 'Completed' },
  failed: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-50', label: 'Failed' },
}

const DOCUMENT_TYPE_LABELS = {
  handwritten: 'Handwritten',
  printed_lab: 'Lab Report',
  clinical_db: 'Clinical DB',
  other: 'Other',
}

export default function Documents() {
  const [selectedDoc, setSelectedDoc] = useState(null)
  const queryClient = useQueryClient()

  const { data: documentsData, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentsApi.list().then(res => res.data),
  })

  const processMutation = useMutation({
    mutationFn: (id) => documentsApi.process(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.success('Document processing started')
    },
    onError: () => {
      toast.error('Failed to process document')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => documentsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      toast.success('Document deleted')
    },
    onError: () => {
      toast.error('Failed to delete document')
    },
  })

  const processAllMutation = useMutation({
    mutationFn: () => documentsApi.processAllPending(),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.success(`Processed ${response.data.processed} documents`)
    },
    onError: () => {
      toast.error('Failed to process documents')
    },
  })

  const documents = documentsData?.results || []
  const pendingCount = documents.filter(d => d.processing_status === 'pending').length

  return (
    <div>
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
          <p className="text-gray-500">
            {documentsData?.count || 0} documents uploaded
          </p>
        </div>
        {pendingCount > 0 && (
          <button
            onClick={() => processAllMutation.mutate()}
            disabled={processAllMutation.isPending}
            className="btn-primary flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${processAllMutation.isPending ? 'animate-spin' : ''}`} />
            Process All Pending ({pendingCount})
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Documents List */}
        <div className="lg:col-span-2">
          <div className="card">
            {isLoading ? (
              <div className="flex justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
              </div>
            ) : documents.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                No documents uploaded yet. Go to Upload page to add documents.
              </div>
            ) : (
              <div className="divide-y">
                {documents.map((doc) => {
                  const statusConfig = STATUS_CONFIG[doc.processing_status]
                  const StatusIcon = statusConfig.icon
                  
                  return (
                    <div 
                      key={doc.id}
                      className={`p-4 hover:bg-gray-50 cursor-pointer ${
                        selectedDoc?.id === doc.id ? 'bg-primary-50' : ''
                      }`}
                      onClick={() => setSelectedDoc(doc)}
                    >
                      <div className="flex items-start gap-4">
                        <div className="p-2 bg-gray-100 rounded-lg">
                          <FileText className="h-6 w-6 text-gray-600" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">{doc.original_filename}</p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-gray-500">
                              {DOCUMENT_TYPE_LABELS[doc.document_type]}
                            </span>
                            <span className="text-xs text-gray-400">•</span>
                            <span className="text-xs text-gray-500">
                              {new Date(doc.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${statusConfig.bg} ${statusConfig.color}`}>
                            <StatusIcon className="h-3 w-3" />
                            {statusConfig.label}
                          </span>
                          {doc.processing_status === 'pending' && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                processMutation.mutate(doc.id)
                              }}
                              disabled={processMutation.isPending}
                              className="p-1 hover:bg-gray-200 rounded"
                              title="Process"
                            >
                              <RefreshCw className="h-4 w-4 text-gray-500" />
                            </button>
                          )}
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              if (confirm('Delete this document?')) {
                                deleteMutation.mutate(doc.id)
                              }
                            }}
                            className="p-1 hover:bg-red-100 rounded"
                            title="Delete"
                          >
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Document Details */}
        <div className="card h-fit">
          {selectedDoc ? (
            <>
              <h3 className="font-semibold mb-4">Document Details</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-gray-500">Filename</label>
                  <p className="text-sm font-medium">{selectedDoc.original_filename}</p>
                </div>
                
                <div>
                  <label className="text-xs text-gray-500">Type</label>
                  <p className="text-sm">{DOCUMENT_TYPE_LABELS[selectedDoc.document_type]}</p>
                </div>
                
                <div>
                  <label className="text-xs text-gray-500">Status</label>
                  <p className="text-sm">{STATUS_CONFIG[selectedDoc.processing_status].label}</p>
                </div>
                
                {selectedDoc.hospital_clinic_name && (
                  <div>
                    <label className="text-xs text-gray-500">Hospital/Clinic</label>
                    <p className="text-sm">{selectedDoc.hospital_clinic_name}</p>
                  </div>
                )}
                
                {selectedDoc.source_location && (
                  <div>
                    <label className="text-xs text-gray-500">Location</label>
                    <p className="text-sm">{selectedDoc.source_location}</p>
                  </div>
                )}
                
                {selectedDoc.processing_error && (
                  <div>
                    <label className="text-xs text-red-500">Error</label>
                    <p className="text-sm text-red-600">{selectedDoc.processing_error}</p>
                  </div>
                )}
                
                {selectedDoc.structured_data && Object.keys(selectedDoc.structured_data).length > 0 && (
                  <div>
                    <label className="text-xs text-gray-500">Extracted Data</label>
                    <pre className="text-xs bg-gray-50 p-3 rounded-lg overflow-auto max-h-64 mt-1">
                      {JSON.stringify(selectedDoc.structured_data, null, 2)}
                    </pre>
                  </div>
                )}

                {selectedDoc.file_url && (
                  <a
                    href={selectedDoc.file_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-secondary w-full flex items-center justify-center gap-2"
                  >
                    <Eye className="h-4 w-4" />
                    View Original
                  </a>
                )}
              </div>
            </>
          ) : (
            <div className="text-center py-8 text-gray-400">
              Select a document to view details
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
