import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  AlertTriangle, 
  TrendingUp, 
  MapPin, 
  Users, 
  Activity,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Bell,
  FileText,
  CheckCircle,
} from 'lucide-react'
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell,
  Legend,
  LineChart,
  Line,
} from 'recharts'
import { analyticsApi } from '../services/api'

const COLORS = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']
const AGE_COLORS = {
  '0-17': '#60a5fa',
  '18-29': '#34d399',
  '30-44': '#fbbf24',
  '45-59': '#f87171',
  '60+': '#a78bfa',
  'Unknown': '#9ca3af'
}

interface Alert {
  disease: string
  disease_id: string
  severity: 'critical' | 'warning'
  recent_cases: number
  baseline_avg: number
  increase_ratio: number | null
  message: string
}

interface GeographicCluster {
  type: string
  location?: string
  state?: string
  patient_count: number
  disease_count: number
  top_diseases: Array<{ name: string; count: number }>
}

interface AgeConcentration {
  disease: string
  dominant_age_group: string
  concentration: number
  patient_count: number
  total_patients: number
  description: string
}

// Alert Card Component
function AlertCard({ alert }: { alert: Alert }) {
  const isCritical = alert.severity === 'critical'
  
  return (
    <div className={`p-4 rounded-lg border-l-4 ${
      isCritical 
        ? 'bg-red-50 border-red-500' 
        : 'bg-amber-50 border-amber-500'
    }`}>
      <div className="flex items-start gap-3">
        <AlertTriangle className={`h-5 w-5 mt-0.5 ${
          isCritical ? 'text-red-500' : 'text-amber-500'
        }`} />
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <h4 className={`font-semibold ${
              isCritical ? 'text-red-700' : 'text-amber-700'
            }`}>
              {alert.disease}
            </h4>
            <span className={`text-xs px-2 py-1 rounded-full ${
              isCritical 
                ? 'bg-red-100 text-red-700' 
                : 'bg-amber-100 text-amber-700'
            }`}>
              {isCritical ? 'CRITICAL' : 'WARNING'}
            </span>
          </div>
          <p className="text-sm text-gray-600 mt-1">{alert.message}</p>
          <div className="flex gap-4 mt-2 text-xs text-gray-500">
            <span>Recent: <strong>{alert.recent_cases}</strong> cases</span>
            <span>Baseline: <strong>{alert.baseline_avg}</strong> avg</span>
            {alert.increase_ratio && (
              <span className={isCritical ? 'text-red-600' : 'text-amber-600'}>
                ↑ {Math.round((alert.increase_ratio - 1) * 100)}% increase
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// Geographic Cluster Card
function ClusterCard({ cluster }: { cluster: GeographicCluster }) {
  const [expanded, setExpanded] = useState(false)
  
  return (
    <div className="p-4 bg-white rounded-lg border hover:shadow-md transition-shadow">
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-50 rounded-lg">
            <MapPin className="h-5 w-5 text-blue-500" />
          </div>
          <div>
            <h4 className="font-medium">{cluster.location || cluster.state}</h4>
            <p className="text-sm text-gray-500">{cluster.type}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="font-semibold text-lg">{cluster.patient_count}</p>
            <p className="text-xs text-gray-500">patients</p>
          </div>
          {expanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
        </div>
      </div>
      
      {expanded && cluster.top_diseases.length > 0 && (
        <div className="mt-4 pt-4 border-t">
          <p className="text-sm font-medium mb-2">Top Diseases in this area:</p>
          <div className="flex flex-wrap gap-2">
            {cluster.top_diseases.map((d, idx) => (
              <span 
                key={idx}
                className="px-2 py-1 bg-gray-100 rounded-full text-xs"
              >
                {d.name} ({d.count})
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// Main Surveillance Dashboard
export default function SurveillanceDashboard() {
  const [selectedPeriod, setSelectedPeriod] = useState(30)
  
  // Fetch basic dashboard stats
  const { data: dashboardData } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => analyticsApi.dashboard().then(res => res.data),
  })
  
  // Fetch surveillance data
  const { data: surveillance, isLoading: loadingSurveillance, refetch } = useQuery({
    queryKey: ['surveillance', selectedPeriod],
    queryFn: () => analyticsApi.surveillance(selectedPeriod).then(res => res.data),
    refetchInterval: 60000, // Auto-refresh every minute
  })
  
  // Fetch disease trends
  const { data: trends } = useQuery({
    queryKey: ['trends', selectedPeriod],
    queryFn: () => analyticsApi.trends({ days: selectedPeriod }).then(res => res.data),
  })
  
  // Fetch comorbidity data
  const { data: comorbidity } = useQuery({
    queryKey: ['comorbidity'],
    queryFn: () => analyticsApi.comorbidity().then(res => res.data),
  })
  
  const alerts = surveillance?.alerts || []
  const clusters = surveillance?.geographic_clusters || []
  const ageConcentrations = surveillance?.age_concentrations || []
  const criticalAlerts = alerts.filter((a: Alert) => a.severity === 'critical')
  const warningAlerts = alerts.filter((a: Alert) => a.severity === 'warning')
  
  // Prepare trends data for chart
  const trendChartData = Object.entries(trends?.daily_trends || {}).slice(0, 5).map(([disease, data]) => ({
    disease,
    data: data as Array<{ date: string; count: number }>
  }))
  
  // Prepare comorbidity data for visualization
  const comorbidityData = (comorbidity?.comorbidities || []).slice(0, 10)

  if (loadingSurveillance) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Health Surveillance Dashboard</h1>
          <p className="text-gray-500">Real-time epidemic monitoring and health analytics</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(Number(e.target.value))}
            className="input w-40"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
            <option value={60}>Last 60 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <button
            onClick={() => refetch()}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Quick Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 rounded-lg">
              <FileText className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Documents</p>
              <p className="text-xl font-bold">{dashboardData?.documents?.total || 0}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-50 rounded-lg">
              <Users className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Patients</p>
              <p className="text-xl font-bold">{dashboardData?.patients?.total || 0}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-50 rounded-lg">
              <Activity className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Diseases</p>
              <p className="text-xl font-bold">{dashboardData?.diseases?.unique_diseases || 0}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-50 rounded-lg">
              <CheckCircle className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Processed</p>
              <p className="text-xl font-bold">{dashboardData?.documents?.processed || 0}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Alert Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card bg-gradient-to-br from-red-500 to-red-600 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-red-100 text-sm">Critical Alerts</p>
              <p className="text-3xl font-bold">{criticalAlerts.length}</p>
            </div>
            <Bell className="h-10 w-10 text-red-200" />
          </div>
        </div>
        
        <div className="card bg-gradient-to-br from-amber-500 to-amber-600 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-amber-100 text-sm">Warning Alerts</p>
              <p className="text-3xl font-bold">{warningAlerts.length}</p>
            </div>
            <AlertTriangle className="h-10 w-10 text-amber-200" />
          </div>
        </div>
        
        <div className="card bg-gradient-to-br from-blue-500 to-blue-600 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-100 text-sm">Disease Hotspots</p>
              <p className="text-3xl font-bold">{clusters.length}</p>
            </div>
            <MapPin className="h-10 w-10 text-blue-200" />
          </div>
        </div>
        
        <div className="card bg-gradient-to-br from-purple-500 to-purple-600 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-100 text-sm">Age-Specific Patterns</p>
              <p className="text-3xl font-bold">{ageConcentrations.length}</p>
            </div>
            <Users className="h-10 w-10 text-purple-200" />
          </div>
        </div>
      </div>

      {/* Alerts Section */}
      {alerts.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Bell className="h-5 w-5 text-red-500" />
            <h2 className="text-lg font-semibold">Active Alerts</h2>
            <span className="text-sm text-gray-500">
              ({criticalAlerts.length} critical, {warningAlerts.length} warnings)
            </span>
          </div>
          <div className="space-y-3">
            {alerts.slice(0, 5).map((alert: Alert, idx: number) => (
              <AlertCard key={idx} alert={alert} />
            ))}
          </div>
        </div>
      )}

      {/* Main Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Disease Trends */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="h-5 w-5 text-primary-500" />
            <h2 className="text-lg font-semibold">Disease Trends</h2>
          </div>
          {trendChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tick={{ fontSize: 10 }}
                  tickFormatter={(val) => val ? new Date(val).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : ''}
                />
                <YAxis />
                <Tooltip 
                  labelFormatter={(val) => val ? new Date(val).toLocaleDateString() : ''}
                />
                <Legend />
                {trendChartData.map((trend, idx) => (
                  <Line
                    key={trend.disease}
                    data={trend.data}
                    type="monotone"
                    dataKey="count"
                    name={trend.disease}
                    stroke={COLORS[idx % COLORS.length]}
                    strokeWidth={2}
                    dot={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-400">
              No trend data available
            </div>
          )}
        </div>

        {/* Age Group Distribution */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Users className="h-5 w-5 text-blue-500" />
            <h2 className="text-lg font-semibold">Age-Specific Disease Patterns</h2>
          </div>
          {ageConcentrations.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={ageConcentrations.slice(0, 8)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 100]} tickFormatter={(val) => `${val}%`} />
                <YAxis dataKey="disease" type="category" width={120} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(val: number) => `${val}%`} />
                <Bar dataKey="concentration" name="Concentration">
                  {ageConcentrations.slice(0, 8).map((entry: AgeConcentration, idx: number) => (
                    <Cell 
                      key={idx} 
                      fill={AGE_COLORS[entry.dominant_age_group as keyof typeof AGE_COLORS] || '#9ca3af'} 
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-400">
              No age concentration data available
            </div>
          )}
          
          {/* Age Group Legend */}
          <div className="flex flex-wrap gap-2 mt-4 justify-center">
            {Object.entries(AGE_COLORS).map(([group, color]) => (
              <div key={group} className="flex items-center gap-1 text-xs">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: color }}></div>
                <span>{group}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Geographic Clusters & Comorbidity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Geographic Hotspots */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <MapPin className="h-5 w-5 text-blue-500" />
            <h2 className="text-lg font-semibold">Geographic Hotspots</h2>
          </div>
          {clusters.length > 0 ? (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {clusters.slice(0, 10).map((cluster: GeographicCluster, idx: number) => (
                <ClusterCard key={idx} cluster={cluster} />
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-400">
              No geographic clusters detected
            </div>
          )}
        </div>

        {/* Comorbidity Analysis */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="h-5 w-5 text-purple-500" />
            <h2 className="text-lg font-semibold">Common Comorbidities</h2>
          </div>
          {comorbidityData.length > 0 ? (
            <div className="space-y-2">
              {comorbidityData.map((item: { disease_1: string; disease_2: string; co_occurrence_count: number }, idx: number) => (
                <div 
                  key={idx}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center gap-2 flex-1">
                    <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-sm">
                      {item.disease_1}
                    </span>
                    <span className="text-gray-400">+</span>
                    <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-sm">
                      {item.disease_2}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="font-semibold">{item.co_occurrence_count}</span>
                    <span className="text-xs text-gray-500 ml-1">patients</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-400">
              No comorbidity data available
            </div>
          )}
        </div>
      </div>

      {/* Insights Summary */}
      <div className="card bg-gradient-to-r from-gray-50 to-gray-100">
        <h2 className="text-lg font-semibold mb-4">📊 Key Insights</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {criticalAlerts.length > 0 && (
            <div className="p-4 bg-white rounded-lg">
              <h3 className="font-medium text-red-600 mb-2">🚨 Immediate Attention</h3>
              <p className="text-sm text-gray-600">
                {criticalAlerts.length} disease(s) showing unusual spike: {' '}
                <strong>{criticalAlerts.map((a: Alert) => a.disease).join(', ')}</strong>
              </p>
            </div>
          )}
          
          {ageConcentrations.length > 0 && (
            <div className="p-4 bg-white rounded-lg">
              <h3 className="font-medium text-blue-600 mb-2">👥 Age-Specific Patterns</h3>
              <p className="text-sm text-gray-600">
                {ageConcentrations[0]?.description || 'Analyzing patterns...'}
              </p>
            </div>
          )}
          
          {clusters.length > 0 && (
            <div className="p-4 bg-white rounded-lg">
              <h3 className="font-medium text-purple-600 mb-2">📍 Top Hotspot</h3>
              <p className="text-sm text-gray-600">
                <strong>{clusters[0]?.location || clusters[0]?.state}</strong> has{' '}
                {clusters[0]?.patient_count} patients with{' '}
                {clusters[0]?.disease_count} different diseases
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
