import { useState } from 'react'
import { FileText, Download, Trash2, Edit3 } from 'lucide-react'
import toast from 'react-hot-toast'
import { exportReport } from '../api/client'

export default function ReportBuilder({ gaps, onRemove }) {
  const [questions, setQuestions] = useState({})  // {gap_id: string}
  const [corpusName, setCorpusName] = useState('My Research Corpus')
  const [exporting, setExporting] = useState(false)

  const handleQuestion = (id, val) =>
    setQuestions(prev => ({ ...prev, [id]: val }))

  const doExport = async (fmt) => {
    if (!gaps.length) { toast.error('No gaps selected for report.'); return }
    setExporting(true)
    try {
      const body = {
        format: fmt,
        corpus_name: corpusName,
        gap_ids: gaps.map(g => g.id),
        custom_questions: questions,
      }
      const res = await exportReport(body)

      if (fmt === 'json') {
        const text = await res.data.text()
        const blob = new Blob([text], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a'); a.href = url; a.download = 'researchlens_report.json'; a.click()
        URL.revokeObjectURL(url)
        toast.success('JSON report downloaded!')
      } else {
        const url = URL.createObjectURL(res.data)
        const a = document.createElement('a'); a.href = url; a.download = 'researchlens_report.pdf'; a.click()
        URL.revokeObjectURL(url)
        toast.success('PDF report downloaded!')
      }
    } catch (err) {
      toast.error('Export failed: ' + err.message)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="space-y-5">
      {/* Report header */}
      <div className="card p-5 space-y-4">
        <h2 className="text-base font-semibold text-text-primary flex items-center gap-2">
          <FileText size={16} className="text-accent" />
          Report Configuration
        </h2>
        <div>
          <label className="section-label block mb-1.5">Corpus Name</label>
          <input
            className="input w-full"
            value={corpusName}
            onChange={e => setCorpusName(e.target.value)}
            placeholder="My Research Corpus"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-bg border border-border rounded-xl p-3 text-center">
            <p className="text-2xl font-bold gradient-text">{gaps.length}</p>
            <p className="text-xs text-text-muted mt-0.5">Gaps Selected</p>
          </div>
          <div className="bg-bg border border-border rounded-xl p-3 text-center">
            <p className="text-2xl font-bold gradient-text">
              {gaps.length ? (gaps.reduce((a, g) => a + g.gap_score, 0) / gaps.length * 100).toFixed(0) : 0}%
            </p>
            <p className="text-xs text-text-muted mt-0.5">Avg Gap Score</p>
          </div>
        </div>
      </div>

      {/* Gap list */}
      {gaps.length === 0 ? (
        <div className="card p-10 text-center text-text-muted">
          <FileText size={36} className="mx-auto mb-3 opacity-30" />
          <p className="font-medium">No gaps added yet</p>
          <p className="text-sm mt-1">Go to Results and click "Add to Report" on a gap.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {gaps.map(gap => (
            <div key={gap.id} className="card p-5 space-y-3 animate-slide-up">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-accent">#{gap.rank}</span>
                    <h3 className="text-sm font-semibold text-text-primary">{gap.label}</h3>
                  </div>
                  <p className="text-xs text-text-muted mt-0.5">
                    Gap Score: {(gap.gap_score * 100).toFixed(0)}%
                  </p>
                </div>
                <button
                  onClick={() => onRemove(gap.id)}
                  className="text-text-muted hover:text-danger transition-colors flex-shrink-0"
                >
                  <Trash2 size={14} />
                </button>
              </div>

              <div>
                <label className="section-label flex items-center gap-1.5 mb-1.5">
                  <Edit3 size={10} />Research Question
                </label>
                <textarea
                  className="input w-full resize-none text-sm leading-relaxed"
                  rows={2}
                  value={questions[gap.id] ?? (gap.suggested_question || '')}
                  onChange={e => handleQuestion(gap.id, e.target.value)}
                  placeholder="Edit the suggested research question…"
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Export buttons */}
      <div className="flex gap-3">
        <button
          onClick={() => doExport('pdf')}
          disabled={exporting || !gaps.length}
          className="btn-primary flex-1 flex items-center justify-center gap-2"
        >
          <Download size={15} />
          {exporting ? 'Exporting…' : 'Export PDF'}
        </button>
        <button
          onClick={() => doExport('json')}
          disabled={exporting || !gaps.length}
          className="btn-secondary flex-1 flex items-center justify-center gap-2"
        >
          <Download size={15} />
          Export JSON
        </button>
      </div>
    </div>
  )
}
