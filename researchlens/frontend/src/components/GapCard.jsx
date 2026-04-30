import { useState } from 'react'
import { ChevronDown, ChevronUp, BookOpen, Tag, Sparkles, Plus } from 'lucide-react'

function ScoreBadge({ score }) {
  const pct = Math.round(score * 100)
  const cls = score >= 0.7 ? 'badge-high' : score >= 0.4 ? 'badge-medium' : 'badge-low'
  return <span className={cls}>{pct}%</span>
}

function ScoreBar({ label, value, color }) {
  const pct = Math.round(value * 100)
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-text-muted">
        <span>{label}</span>
        <span className="font-semibold" style={{ color }}>{pct}%</span>
      </div>
      <div className="h-1.5 bg-border rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}

export default function GapCard({ gap, onAddToReport, isInReport }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className={`card overflow-hidden transition-all duration-300 ${expanded ? 'border-accent/40 shadow-glow-sm' : 'hover:border-accent/20'}`}
    >
      {/* Header — always visible */}
      <div
        className="flex items-start gap-4 p-5 cursor-pointer"
        onClick={() => setExpanded(v => !v)}
      >
        {/* Rank */}
        <div className="w-10 h-10 rounded-xl bg-accent-glow border border-accent/30 flex items-center justify-center flex-shrink-0">
          <span className="text-sm font-bold text-accent">#{gap.rank}</span>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h3 className="text-sm font-semibold text-text-primary truncate">{gap.label}</h3>
            <ScoreBadge score={gap.gap_score} />
          </div>
          <div className="flex flex-wrap gap-1.5">
            {(gap.keywords || []).slice(0, 5).map(kw => (
              <span
                key={kw}
                className="inline-flex items-center gap-1 bg-bg border border-border text-text-muted text-xs px-2 py-0.5 rounded-lg"
              >
                <Tag size={10} />
                {kw}
              </span>
            ))}
          </div>
        </div>

        <div className="flex-shrink-0 text-text-muted">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-border px-5 pb-5 pt-4 space-y-5 animate-slide-up">
          {/* Score Breakdown */}
          <div className="space-y-2.5">
            <p className="section-label">Score Breakdown</p>
            <ScoreBar label="Citation Sparsity (Structural)" value={gap.struct_score} color="#6C63FF" />
            <ScoreBar label="Semantic Novelty" value={gap.sem_score} color="#10B981" />
            <ScoreBar label="Temporal Recency" value={gap.temp_score} color="#F59E0B" />
          </div>

          {/* Supporting Evidence */}
          {gap.supporting_evidence?.length > 0 && (
            <div className="space-y-2">
              <p className="section-label">Supporting Evidence</p>
              <div className="space-y-2">
                {gap.supporting_evidence.slice(0, 3).map((ev, i) => (
                  <blockquote
                    key={i}
                    className="text-xs text-text-secondary bg-bg border-l-2 border-accent/50 pl-3 py-2 pr-2 rounded-r-lg italic leading-relaxed"
                  >
                    {ev}
                  </blockquote>
                ))}
              </div>
            </div>
          )}

          {/* Suggested Research Question */}
          {gap.suggested_question && (
            <div className="space-y-2">
              <p className="section-label flex items-center gap-1.5">
                <Sparkles size={11} />Suggested Research Question
              </p>
              <p className="text-sm text-text-secondary bg-accent-glow border border-accent/20 rounded-xl px-4 py-3 leading-relaxed">
                {gap.suggested_question}
              </p>
            </div>
          )}

          {/* Bordering Papers */}
          {gap.bordering_papers?.length > 0 && (
            <div className="space-y-2">
              <p className="section-label flex items-center gap-1.5">
                <BookOpen size={11} />Bordering Papers
              </p>
              <div className="flex flex-wrap gap-1.5">
                {gap.bordering_papers.slice(0, 5).map((pid, i) => (
                  <span
                    key={pid}
                    className="text-xs bg-card-hover border border-border text-text-muted px-2.5 py-1 rounded-lg"
                  >
                    Paper #{pid}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Add to Report */}
          <button
            onClick={e => { e.stopPropagation(); onAddToReport?.(gap) }}
            disabled={isInReport}
            className={`flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-xl transition-all duration-200 ${
              isInReport
                ? 'bg-success-dim text-success border border-success/30 cursor-default'
                : 'btn-primary'
            }`}
          >
            <Plus size={14} />
            {isInReport ? 'Added to Report' : 'Add to Report'}
          </button>
        </div>
      )}
    </div>
  )
}
