import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, Search, Filter, ChevronLeft, ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { patientsApi, diseasesApi } from '../services/api'
import type { Disease } from '@/types'

interface Filters {
  disease_name: string
  gender: string
  age_group: string
  location: string
}

export default function Patients() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState<Filters>({
    disease_name: '',
    gender: '',
    age_group: '',
    location: '',
  })
  const [showFilters, setShowFilters] = useState(false)

  const { data: patientsData, isLoading } = useQuery({
    queryKey: ['patients', page, search, filters],
    queryFn: () => patientsApi.list({ 
      page, 
      search,
      ...Object.fromEntries(
        Object.entries(filters).filter(([_, v]) => v !== '')
      ) as Partial<Filters>
    }).then(res => res.data),
  })

  const { data: diseases } = useQuery({
    queryKey: ['diseases'],
    queryFn: () => diseasesApi.list().then(res => res.data),
  })

  const handleExport = async (format: 'csv' | 'excel') => {
    try {
      const response = await patientsApi.export(filters, format)
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `patients_export.${format === 'excel' ? 'xlsx' : 'csv'}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      
      toast.success(`Exported as ${format.toUpperCase()}`)
    } catch (error) {
      toast.error('Failed to export data')
    }
  }

  const patients = patientsData?.results || []
  const totalPages = Math.ceil((patientsData?.count || 0) / 20)

  return (
    <div>
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Patients</h1>
          <p className="text-gray-500">
            {patientsData?.count || 0} patients extracted from documents
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleExport('csv')}
            className="btn-secondary flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </button>
          <button
            onClick={() => handleExport('excel')}
            className="btn-primary flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            Export Excel
          </button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="card mb-6">
        <div className="flex gap-4 mb-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by name or phone..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`btn-secondary flex items-center gap-2 ${showFilters ? 'bg-gray-200' : ''}`}
          >
            <Filter className="h-4 w-4" />
            Filters
          </button>
        </div>

        {showFilters && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-4 border-t">
            <div>
              <label className="label">Disease</label>
              <select
                value={filters.disease_name}
                onChange={(e) => setFilters(prev => ({ ...prev, disease_name: e.target.value }))}
                className="input"
              >
                <option value="">All Diseases</option>
                {diseases?.results?.map((disease: Disease) => (
                  <option key={disease.id} value={disease.name}>
                    {disease.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Gender</label>
              <select
                value={filters.gender}
                onChange={(e) => setFilters(prev => ({ ...prev, gender: e.target.value }))}
                className="input"
              >
                <option value="">All</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="label">Age Group</label>
              <select
                value={filters.age_group}
                onChange={(e) => setFilters(prev => ({ ...prev, age_group: e.target.value }))}
                className="input"
              >
                <option value="">All Ages</option>
                <option value="0-17">0-17</option>
                <option value="18-29">18-29</option>
                <option value="30-44">30-44</option>
                <option value="45-59">45-59</option>
                <option value="60+">60+</option>
              </select>
            </div>
            <div>
              <label className="label">Location</label>
              <input
                type="text"
                value={filters.location}
                onChange={(e) => setFilters(prev => ({ ...prev, location: e.target.value }))}
                placeholder="Filter by location"
                className="input"
              />
            </div>
          </div>
        )}
      </div>

      {/* Patients Table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : patients.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No patients found. Upload and process documents to extract patient data.
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Name</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Age</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Gender</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Phone</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Location</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Hospital</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Diseases</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {patients.map((patient) => {
                    const phone = patient.phone || patient.phone_number || '-'
                    // Handle location - could be string or PatientLocation object
                    const location = typeof patient.location === 'string' 
                      ? patient.location
                      : patient.location?.city && patient.location?.state
                        ? `${patient.location.city}, ${patient.location.state}`
                        : patient.address
                          || (patient.city && patient.state ? `${patient.city}, ${patient.state}` : null)
                          || '-'
                    const hospital = patient.hospital || patient.hospital_clinic || '-'
                    const diseases = patient.diseases || patient.disease_list || []
                    
                    return (
                      <tr key={patient.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium">{patient.name}</td>
                        <td className="px-4 py-3 text-gray-600">{patient.age || '-'}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded-full text-xs ${
                            patient.gender === 'male' ? 'bg-blue-100 text-blue-700' :
                            patient.gender === 'female' ? 'bg-pink-100 text-pink-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {patient.gender === 'unknown' ? 'Unknown' : patient.gender || 'Unknown'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-600">{phone}</td>
                        <td className="px-4 py-3 text-gray-600">{location}</td>
                        <td className="px-4 py-3 text-gray-600">{hospital}</td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {diseases.slice(0, 2).map((disease, idx) => (
                              <span 
                                key={idx}
                                className="px-2 py-0.5 bg-primary-50 text-primary-700 rounded-full text-xs"
                              >
                                {disease}
                              </span>
                            ))}
                            {diseases.length > 2 && (
                              <span className="text-xs text-gray-500">
                                +{diseases.length - 2} more
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t">
                <p className="text-sm text-gray-500">
                  Showing page {page} of {totalPages}
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="p-2 rounded hover:bg-gray-100 disabled:opacity-50"
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="p-2 rounded hover:bg-gray-100 disabled:opacity-50"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

