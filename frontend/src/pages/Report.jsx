import { useState } from 'react'
import { FileText } from 'lucide-react'
import ReportBuilder from '../components/ReportBuilder'

const getGaps = () => {
  try { return JSON.parse(sessionStorage.getItem('reportGaps') || '[]') } catch { return [] }
}
const saveGaps = gaps => sessionStorage.setItem('reportGaps', JSON.stringify(gaps))

export default function Report() {
  const [gaps, setGaps] = useState(getGaps)

  const handleRemove = id => {
    const next = gaps.filter(g => g.id !== id)
    setGaps(next)
    saveGaps(next)
  }

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <div className="mb-6 animate-fade-in">
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3 mb-1">
          <FileText size={22} className="text-accent" />
          Research Gap Report
        </h1>
        <p className="text-sm text-text-muted">
          Review and export your selected research gaps with custom research questions.
        </p>
      </div>
      <ReportBuilder gaps={gaps} onRemove={handleRemove} />
    </div>
  )
}
