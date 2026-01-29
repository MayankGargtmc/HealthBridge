import { Link, Outlet, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, 
  Upload, 
  Users, 
  FileText, 
  Activity,
  Heart
} from 'lucide-react'
import { clsx } from 'clsx'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Upload Documents', href: '/upload', icon: Upload },
  { name: 'Patients', href: '/patients', icon: Users },
  { name: 'Diseases', href: '/diseases', icon: Activity },
  { name: 'Documents', href: '/documents', icon: FileText },
]

export default function Layout() {
  const location = useLocation()

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 fixed h-full">
        <div className="p-6">
          <Link to="/" className="flex items-center gap-2">
            <Heart className="h-8 w-8 text-primary-600" />
            <span className="text-xl font-bold text-gray-900">HealthBridge</span>
          </Link>
          <p className="text-xs text-gray-500 mt-1">Bridge the Gap</p>
        </div>
        
        <nav className="mt-6 px-3">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.name}
                to={item.href}
                className={clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 transition-colors',
                  isActive 
                    ? 'bg-primary-50 text-primary-700 font-medium' 
                    : 'text-gray-600 hover:bg-gray-50'
                )}
              >
                <item.icon className="h-5 w-5" />
                {item.name}
              </Link>
            )
          })}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 ml-64">
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
