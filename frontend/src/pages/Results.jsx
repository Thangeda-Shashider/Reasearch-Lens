import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { SlidersHorizontal, Search, TrendingUp } from 'lucide-react'
import GapCard from '../components/GapCard'
import { SkeletonList } from '../components/LoadingSkeleton'
import { fetchGaps } from '../api/client'

// Store report gaps in sessionStorage so Report page can read them
const getReportGaps = () => {
  try { return JSON.parse(sessionStorage.getItem('reportGaps') || '[]') } catch { return [] }
}
const saveReportGaps = (gaps) => sessionStorage.setItem('reportGaps', JSON.stringify(gaps))

export default function Results() {
  const [minScore, setMinScore] = useState(0)
  const [maxScore, setMaxScore] = useState(1)
  const [searchTerm, setSearchTerm] = useState('')
  const [reportGaps, setReportGaps] = useState(getReportGaps)

  const { data, isLoading } = useQuery({
    queryKey: ['gaps', minScore, maxScore],
    queryFn: () => fetchGaps({ min_score: minScore, max_score: maxScore }),
    refetchOnWindowFocus: false,
  })

  const gaps = (data?.gaps || []).filter(g =>
    !searchTerm || g.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
    g.keywords?.some(k => k.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  const isInReport = id => reportGaps.some(g => g.id === id)

  const handleAddToReport = gap => {
    if (isInReport(gap.id)) return
    const next = [...reportGaps, gap]
    setReportGaps(next)
    saveReportGaps(next)
  }

  return (
    <div className="p-8">
      <div className="mb-6 animate-fade-in">
        <h1 className="text-2xl font-bold text-text-primary mb-1">Research Gaps</h1>
        <p className="text-sm text-text-muted">
          {data?.total ?? 0} gaps identified · ranked by composite score
        </p>
      </div>

      {/* Filter bar */}
      <div className="card p-4 mb-6 flex flex-wrap items-center gap-4 animate-fade-in">
        <SlidersHorizontal size={15} className="text-accent flex-shrink-0" />

        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted">Min score</span>
          <input
            type="range" min={0} max={1} step={0.05}
            value={minScore}
            onChange={e => setMinScore(Number(e.target.value))}
            className="w-24 accent-[#6C63FF]"
          />
          <span className="text-xs text-accent font-semibold w-8">{Math.round(minScore * 100)}%</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted">Max score</span>
          <input
            type="range" min={0} max={1} step={0.05}
            value={maxScore}
            onChange={e => setMaxScore(Number(e.target.value))}
            className="w-24 accent-[#6C63FF]"
          />
          <span className="text-xs text-accent font-semibold w-8">{Math.round(maxScore * 100)}%</span>
        </div>

        <div className="flex-1 min-w-48 relative">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            className="input w-full pl-8 text-xs py-2"
            placeholder="Search by keyword…"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
          />
        </div>

        <span className="text-xs text-text-muted ml-auto">
          {gaps.length} shown · <span className="text-success">{reportGaps.length}</span> in report
        </span>
      </div>

      {/* Gaps */}
      {isLoading ? (
        <SkeletonList count={5} />
      ) : gaps.length === 0 ? (
        <div className="card p-12 text-center">
          <TrendingUp size={40} className="mx-auto mb-4 text-text-muted opacity-30" />
          <p className="font-semibold text-text-secondary">No gaps found</p>
          <p className="text-sm text-text-muted mt-1">
            Upload papers and click <strong className="text-text-primary">Analyze Papers</strong> first.
          </p>
        </div>
      ) : (
        <div className="space-y-3 animate-fade-in">
          {gaps.map(gap => (
            <GapCard
              key={gap.id}
              gap={gap}
              onAddToReport={handleAddToReport}
              isInReport={isInReport(gap.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
