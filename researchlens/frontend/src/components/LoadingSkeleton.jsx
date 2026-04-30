export function SkeletonLine({ className = '' }) {
  return (
    <div className={`bg-border rounded animate-pulse ${className}`} />
  )
}

export function SkeletonCard({ lines = 3 }) {
  return (
    <div className="card p-5 space-y-3 animate-fade-in">
      <SkeletonLine className="h-4 w-3/4" />
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonLine key={i} className={`h-3 ${i === lines - 1 ? 'w-1/2' : 'w-full'}`} />
      ))}
    </div>
  )
}

export function SkeletonList({ count = 4 }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} lines={2} />
      ))}
    </div>
  )
}

export function SkeletonChart() {
  return (
    <div className="card p-6 animate-pulse">
      <SkeletonLine className="h-5 w-40 mb-6" />
      <div className="flex items-end gap-3 h-40">
        {[70, 45, 90, 60, 80, 35, 55].map((h, i) => (
          <div
            key={i}
            className="flex-1 bg-border rounded-t"
            style={{ height: `${h}%` }}
          />
        ))}
      </div>
    </div>
  )
}
