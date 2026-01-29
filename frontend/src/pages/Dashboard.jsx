import { useQuery } from '@tanstack/react-query'
import { 
  FileText, 
  Users, 
  Activity, 
  CheckCircle,
  Clock,
  XCircle 
} from 'lucide-react'
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
import { analyticsApi } from '../services/api'

const COLORS = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

function StatCard({ title, value, icon: Icon, color = 'primary' }) {
  const colorClasses = {
    primary: 'bg-primary-50 text-primary-600',
    blue: 'bg-blue-50 text-blue-600',
    amber: 'bg-amber-50 text-amber-600',
    red: 'bg-red-50 text-red-600',
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { data: dashboardData, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => analyticsApi.dashboard().then(res => res.data),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  const data = dashboardData || {
    documents: { total: 0, processed: 0, pending: 0, failed: 0 },
    patients: { total: 0, with_contact: 0 },
    diseases: { unique_diseases: 0, total_diagnoses: 0 },
    gender_distribution: [],
    top_diseases: [],
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">Overview of patient data and document processing</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard 
          title="Total Documents" 
          value={data.documents.total} 
          icon={FileText}
          color="primary"
        />
        <StatCard 
          title="Total Patients" 
          value={data.patients.total} 
          icon={Users}
          color="blue"
        />
        <StatCard 
          title="Unique Diseases" 
          value={data.diseases.unique_diseases} 
          icon={Activity}
          color="amber"
        />
        <StatCard 
          title="Processed" 
          value={data.documents.processed} 
          icon={CheckCircle}
          color="primary"
        />
      </div>

      {/* Document Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="card flex items-center gap-4">
          <div className="p-2 rounded-lg bg-green-50">
            <CheckCircle className="h-5 w-5 text-green-600" />
          </div>
          <div>
            <p className="text-sm text-gray-500">Processed</p>
            <p className="text-xl font-semibold">{data.documents.processed}</p>
          </div>
        </div>
        <div className="card flex items-center gap-4">
          <div className="p-2 rounded-lg bg-amber-50">
            <Clock className="h-5 w-5 text-amber-600" />
          </div>
          <div>
            <p className="text-sm text-gray-500">Pending</p>
            <p className="text-xl font-semibold">{data.documents.pending}</p>
          </div>
        </div>
        <div className="card flex items-center gap-4">
          <div className="p-2 rounded-lg bg-red-50">
            <XCircle className="h-5 w-5 text-red-600" />
          </div>
          <div>
            <p className="text-sm text-gray-500">Failed</p>
            <p className="text-xl font-semibold">{data.documents.failed}</p>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Diseases Chart */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Top Diseases</h2>
          {data.top_diseases?.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data.top_diseases} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={120} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="patient_count" fill="#22c55e" name="Patients" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-400">
              No disease data available
            </div>
          )}
        </div>

        {/* Gender Distribution */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Gender Distribution</h2>
          {data.gender_distribution?.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={data.gender_distribution}
                  dataKey="count"
                  nameKey="gender"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ gender, count }) => `${gender}: ${count}`}
                >
                  {data.gender_distribution.map((entry, index) => (
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
      </div>
    </div>
  )
}
