import { useQuery } from '@tanstack/react-query'
import { fetchUmap } from '../api/client'
import {
  ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, Legend,
} from 'recharts'
import { SkeletonChart } from './LoadingSkeleton'

const COLORS = [
  '#6C63FF', '#10B981', '#F59E0B', '#EF4444', '#3B82F6',
  '#EC4899', '#8B5CF6', '#14B8A6', '#F97316', '#06B6D4',
]

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-card border border-border rounded-xl px-4 py-3 shadow-card text-xs max-w-[220px]">
      <p className="font-semibold text-text-primary mb-1 leading-snug">{d.title || `Paper ${d.paper_id}`}</p>
      <p className="text-text-muted">{d.topic_label || 'Unclustered'}</p>
      {d.year && <p className="text-text-muted">Year: {d.year}</p>}
      {d.gap_score != null && (
        <p className="mt-1 font-medium text-accent">Gap Score: {(d.gap_score * 100).toFixed(0)}%</p>
      )}
    </div>
  )
}

export default function TopicMap() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['umap'],
    queryFn: fetchUmap,
  })

  if (isLoading) return <SkeletonChart />
  if (error) return (
    <div className="card p-8 text-center text-text-muted">
      <p>Run analysis to generate the topic map.</p>
    </div>
  )

  const points = data?.points || []
  if (!points.length) return (
    <div className="card p-8 text-center text-text-muted">
      <p>No UMAP data yet. Upload papers and run <strong className="text-text-primary">Analyze</strong>.</p>
    </div>
  )

  // Group by topic for coloring
  const topicIds = [...new Set(points.map(p => p.topic_id))]
  const colorMap = {}
  topicIds.forEach((tid, i) => {
    colorMap[tid] = tid == null ? '#4A5568' : COLORS[i % COLORS.length]
  })

  return (
    <div className="card p-6">
      <h2 className="text-base font-semibold text-text-primary mb-1">Topic Map</h2>
      <p className="text-xs text-text-muted mb-5">2D UMAP projection of paper embeddings. Clusters = topics, gray = unclustered.</p>
      <ResponsiveContainer width="100%" height={420}>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
          <XAxis dataKey="x" type="number" domain={['auto', 'auto']} hide />
          <YAxis dataKey="y" type="number" domain={['auto', 'auto']} hide />
          <Tooltip content={<CustomTooltip />} />
          {topicIds.map(tid => (
            <Scatter
              key={String(tid)}
              name={points.find(p => p.topic_id === tid)?.topic_label || 'Unclustered'}
              data={points.filter(p => p.topic_id === tid)}
              fill={colorMap[tid]}
            >
              {points.filter(p => p.topic_id === tid).map((_, i) => (
                <Cell key={i} fill={colorMap[tid]} fillOpacity={0.85} />
              ))}
            </Scatter>
          ))}
          <Legend
            formatter={(value) => (
              <span className="text-xs text-text-secondary">{value}</span>
            )}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
