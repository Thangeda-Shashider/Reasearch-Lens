import { NavLink } from 'react-router-dom'
import {
  Search, Home, BarChart3, Network, FileText, Settings, FlaskConical,
} from 'lucide-react'

const NAV = [
  { to: '/', icon: Home, label: 'Upload' },
  { to: '/results', icon: Search, label: 'Results' },
  { to: '/visualizations', icon: Network, label: 'Visualize' },
  { to: '/report', icon: FileText, label: 'Report' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  return (
    <aside className="fixed top-0 left-0 h-screen w-60 bg-card border-r border-border flex flex-col z-30">
      {/* Logo */}
      <div className="px-5 py-6 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-accent flex items-center justify-center shadow-glow-sm">
            <FlaskConical size={18} className="text-white" />
          </div>
          <div>
            <div className="text-sm font-bold text-text-primary leading-tight">ResearchLens</div>
            <div className="text-[10px] text-text-muted leading-tight">Gap Identification</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        <p className="section-label px-2 mb-3">Navigation</p>
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group
              ${isActive
                ? 'bg-accent-glow text-accent border border-accent/25 shadow-glow-sm'
                : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon
                  size={17}
                  className={`flex-shrink-0 transition-colors ${isActive ? 'text-accent' : 'text-text-muted group-hover:text-text-secondary'}`}
                />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-border">
        <div className="text-xs text-text-muted">
          <span className="gradient-text font-semibold">ResearchLens</span> v1.0
          <br />
          <span className="opacity-60">AI-powered gap analysis</span>
        </div>
      </div>
    </aside>
  )
}
