import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts'
import { Activity, Users } from 'lucide-react'
import { analyticsApi } from '../services/api'
import type { DiseaseAnalytics, Disease } from '@/types'

const COLORS = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']

export default function Diseases() {
  const [selectedDisease, setSelectedDisease] = useState<number | null>(null)

  const { data: diseaseData, isLoading } = useQuery({
    queryKey: ['disease-analytics', selectedDisease],
    queryFn: () => analyticsApi.diseases({ 
      disease_id: selectedDisease || undefined
    }).then(res => res.data),
  })

  const { data: ageData } = useQuery({
    queryKey: ['age-analytics'],
    queryFn: () => analyticsApi.age().then(res => res.data),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  // If viewing all diseases
  if (!selectedDisease) {
    const diseases = (diseaseData as Disease[]) || []
    
    return (
      <div>
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Disease Analytics</h1>
          <p className="text-gray-500">View patient distribution by disease</p>
        </div>

        {/* Disease Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {diseases.map((disease: Disease & { age_groups?: Array<{ age_group: string; count: number }>; category?: string }) => (
            <div 
              key={disease.id}
              onClick={() => setSelectedDisease(disease.id)}
              className="card cursor-pointer hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="p-2 bg-primary-50 rounded-lg">
                  <Activity className="h-6 w-6 text-primary-600" />
                </div>
                <span className="flex items-center gap-1 text-sm text-gray-500">
                  <Users className="h-4 w-4" />
                  {disease.patient_count}
                </span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-1">{disease.name}</h3>
              {disease.category && (
                <span className="text-xs text-gray-500">{disease.category}</span>
              )}
              
              {/* Mini age distribution */}
              {disease.age_groups && disease.age_groups.length > 0 && (
                <div className="mt-4 flex gap-1">
                  {disease.age_groups.map((ag, idx) => (
                    <div 
                      key={ag.age_group}
                      className="flex-1 h-2 rounded-full"
                      style={{ 
                        backgroundColor: COLORS[idx % COLORS.length],
                        opacity: 0.3 + (ag.count / disease.patient_count) * 0.7
                      }}
                      title={`${ag.age_group}: ${ag.count}`}
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        {diseases.length === 0 && (
          <div className="card text-center py-12 text-gray-500">
            No disease data available. Process documents to extract patient diagnoses.
          </div>
        )}

        {/* Age Distribution by Disease Chart */}
        {ageData?.by_disease && ageData.by_disease.length > 0 && (
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Age Distribution by Disease</h2>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={ageData.by_disease}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="disease" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="age_groups.0-17" name="0-17" fill={COLORS[0]} />
                <Bar dataKey="age_groups.18-29" name="18-29" fill={COLORS[1]} />
                <Bar dataKey="age_groups.30-44" name="30-44" fill={COLORS[2]} />
                <Bar dataKey="age_groups.45-59" name="45-59" fill={COLORS[3]} />
                <Bar dataKey="age_groups.60+" name="60+" fill={COLORS[4]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    )
  }

  // Viewing specific disease
  const disease = diseaseData as DiseaseAnalytics
  
  return (
    <div>
      <div className="mb-8">
        <button 
          onClick={() => setSelectedDisease(null)}
          className="text-primary-600 hover:text-primary-700 mb-2"
        >
          ← Back to all diseases
        </button>
        <h1 className="text-2xl font-bold text-gray-900">{disease?.disease || 'Unknown Disease'}</h1>
        <p className="text-gray-500">
          {disease?.patient_count || 0} patients diagnosed
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Age Distribution */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Age Distribution</h2>
          {disease?.age_distribution && disease.age_distribution.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={disease.age_distribution}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="age_group" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#22c55e" name="Patients" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-400">
              No age data available
            </div>
          )}
        </div>

        {/* Gender Distribution */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Gender Distribution</h2>
          {disease?.gender_distribution && disease.gender_distribution.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={disease.gender_distribution}
                  dataKey="count"
                  nameKey="gender"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ gender, count }: { gender: string; count: number }) => `${gender}: ${count}`}
                >
                  {disease.gender_distribution.map((_entry: { gender: string; count: number }, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-400">
              No gender data available
            </div>
          )}
        </div>

        {/* Location Distribution */}
        <div className="card lg:col-span-2">
          <h2 className="text-lg font-semibold mb-4">Location Distribution</h2>
          {disease?.location_distribution && disease.location_distribution.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={disease.location_distribution} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="location" type="category" width={150} />
                <Tooltip />
                <Bar dataKey="count" fill="#3b82f6" name="Patients" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-400">
              No location data available
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

