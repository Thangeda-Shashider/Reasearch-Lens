import { useQuery } from '@tanstack/react-query'
import { fetchGraph } from '../api/client'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { SkeletonChart } from './LoadingSkeleton'

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-card border border-border rounded-xl px-4 py-3 shadow-card text-xs">
      <p className="font-semibold text-text-primary mb-1 truncate max-w-[200px]">{d.label}</p>
      <p className="text-text-muted">Papers: {d.paper_count}</p>
      <p className="text-text-muted">Struct Score: {(d.struct_score * 100).toFixed(0)}%</p>
      <p className="font-semibold text-accent mt-1">Gap Score: {(d.gap_score * 100).toFixed(0)}%</p>
    </div>
  )
}

export default function DensityChart() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['graph'],
    queryFn: fetchGraph,
  })

  if (isLoading) return <SkeletonChart />
  if (error || !data?.density?.length) return (
    <div className="card p-8 text-center text-text-muted">
      <p>Run analysis to view citation density.</p>
    </div>
  )

  const density = [...(data.density || [])]
    .sort((a, b) => a.struct_score - b.struct_score)  // Ascending: sparser = higher gap potential

  const getColor = (score) => {
    if (score >= 0.7) return '#10B981'   // high sparsity = big gap → green
    if (score >= 0.4) return '#F59E0B'   // medium
    return '#EF4444'                      // low sparsity = well-cited → red
  }

  const truncate = (str, n) => str?.length > n ? str.slice(0, n) + '…' : str

  return (
    <div className="card p-6">
      <h2 className="text-base font-semibold text-text-primary mb-1">Citation Density by Topic</h2>
      <p className="text-xs text-text-muted mb-5">
        <span className="text-danger font-medium">Red</span> = well-cited (low gap). &nbsp;
        <span className="text-success font-medium">Green</span> = sparse citations (high gap potential).
      </p>
      <ResponsiveContainer width="100%" height={Math.max(300, density.length * 52)}>
        <BarChart
          data={density}
          layout="vertical"
          margin={{ top: 0, right: 30, bottom: 0, left: 120 }}
        >
          <XAxis
            type="number"
            domain={[0, 1]}
            tickFormatter={v => `${Math.round(v * 100)}%`}
            tick={{ fill: '#64748B', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={115}
            tick={{ fill: '#94A3B8', fontSize: 11 }}
            tickFormatter={v => truncate(v, 20)}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(108,99,255,0.06)' }} />
          <Bar dataKey="struct_score" radius={[0, 6, 6, 0]} maxBarSize={28}>
            {density.map((entry, i) => (
              <Cell key={i} fill={getColor(entry.struct_score)} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
