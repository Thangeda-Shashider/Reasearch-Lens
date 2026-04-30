import { useState } from 'react'
import { Map, Network, BarChart3 } from 'lucide-react'
import TopicMap from '../components/TopicMap'
import CitationGraph from '../components/CitationGraph'
import DensityChart from '../components/DensityChart'

const TABS = [
  { key: 'topic', label: 'Topic Map', icon: Map },
  { key: 'citation', label: 'Citation Network', icon: Network },
  { key: 'density', label: 'Citation Density', icon: BarChart3 },
]

export default function Visualizations() {
  const [tab, setTab] = useState('topic')

  return (
    <div className="p-8">
      <div className="mb-6 animate-fade-in">
        <h1 className="text-2xl font-bold text-text-primary mb-1">Visualizations</h1>
        <p className="text-sm text-text-muted">
          Explore your corpus visually — topic clusters, citation structure, and density.
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-2 mb-6 p-1 bg-card border border-border rounded-2xl w-fit">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${tab === key
              ? 'bg-gradient-accent text-white shadow-glow-sm'
              : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
              }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Panels */}
      <div className="animate-fade-in">
        {tab === 'topic' && <TopicMap />}
        {tab === 'citation' && <CitationGraph />}
        {tab === 'density' && <DensityChart />}
      </div>
    </div>
  )
}
