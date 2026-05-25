import { NavLink, Outlet } from 'react-router-dom'

const navLinks = [
  { to: '/', label: 'Home' },
  { to: '/extraction', label: 'Extraction Control' },
  { to: '/repositories', label: 'Repositories' },
  { to: '/health', label: 'System Health' },
]

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-14 gap-6">
            <span className="font-semibold text-gray-800 text-sm tracking-wide uppercase">
              AzDO Analyzer Admin
            </span>
            {navLinks.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `text-sm font-medium px-1 py-1 border-b-2 transition-colors ${
                    isActive
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  )
}
