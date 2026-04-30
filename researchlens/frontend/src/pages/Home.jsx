import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  FlaskConical, PlayCircle, CheckCircle2, Loader2,
  FileText, Trash2, AlertCircle, ChevronRight,
} from 'lucide-react'
import toast from 'react-hot-toast'
import Uploader from '../components/Uploader'
import { fetchPapers, deletePaper, startAnalysis, fetchStatus } from '../api/client'

const STAGES = [
  { key: 'extracting', label: 'Extracting Text' },
  { key: 'embedding',  label: 'Generating Embeddings' },
  { key: 'clustering', label: 'Clustering Topics' },
  { key: 'scoring',    label: 'Scoring Gaps' },
  { key: 'done',       label: 'Complete' },
]

function StageTracker({ stage, progress, message }) {
  const stageIdx = STAGES.findIndex(s => s.key === stage)
  return (
    <div className="card p-5 space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-text-primary">Analysis Pipeline</p>
        <span className="text-xs text-accent font-semibold">{progress}%</span>
      </div>
      {/* Overall bar */}
      <div className="h-2 bg-border rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-accent rounded-full transition-all duration-700"
          style={{ width: `${progress}%` }}
        />
      </div>
      {/* Stages */}
      <div className="space-y-2">
        {STAGES.map((s, i) => {
          const done = i < stageIdx || stage === 'done'
          const active = s.key === stage && stage !== 'done'
          return (
            <div key={s.key} className={`flex items-center gap-3 text-xs transition-opacity ${i > stageIdx && stage !== 'done' ? 'opacity-30' : ''}`}>
              {done
                ? <CheckCircle2 size={14} className="text-success flex-shrink-0" />
                : active
                  ? <Loader2 size={14} className="text-accent animate-spin flex-shrink-0" />
                  : <div className="w-3.5 h-3.5 rounded-full border border-border flex-shrink-0" />
              }
              <span className={done ? 'text-success' : active ? 'text-accent' : 'text-text-muted'}>
                {s.label}
              </span>
            </div>
          )
        })}
      </div>
      {message && (
        <p className="text-xs text-text-muted italic border-t border-border pt-3">{message}</p>
      )}
    </div>
  )
}

export default function Home() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [jobId, setJobId] = useState(null)
  const [jobData, setJobData] = useState(null)
  const pollRef = useRef(null)

  const { data: papersData, refetch: refetchPapers } = useQuery({
    queryKey: ['papers'],
    queryFn: fetchPapers,
    refetchInterval: false,
  })
  const papers = papersData || []

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  const startPolling = (id) => {
    stopPolling()
    pollRef.current = setInterval(async () => {
      try {
        const status = await fetchStatus(id)
        setJobData(status)
        if (status.stage === 'done') {
          stopPolling()
          toast.success('Analysis complete! View your results.')
          qc.invalidateQueries(['gaps'])
          qc.invalidateQueries(['umap'])
          qc.invalidateQueries(['graph'])
        } else if (status.stage === 'failed') {
          stopPolling()
          toast.error('Analysis failed: ' + status.message)
        }
      } catch { stopPolling() }
    }, 2000)
  }

  useEffect(() => () => stopPolling(), [])

  const handleAnalyze = async () => {
    if (!papers.length) { toast.error('Upload at least one paper first.'); return }
    try {
      const { job_id } = await startAnalysis()
      setJobId(job_id)
      setJobData({ stage: 'pending', progress: 0, message: 'Starting…' })
      startPolling(job_id)
      toast.success('Analysis started!')
    } catch (err) {
      toast.error('Failed to start: ' + (err.response?.data?.detail || err.message))
    }
  }

  const handleDelete = async (id) => {
    try {
      await deletePaper(id)
      refetchPapers()
      toast.success('Paper removed.')
    } catch { toast.error('Failed to remove.') }
  }

  const analyzing = jobData && !['done', 'failed', null].includes(jobData?.stage)
  const done = jobData?.stage === 'done'

  return (
    <div className="p-8 max-w-3xl mx-auto">
      {/* Hero */}
      <div className="mb-10 animate-fade-in">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-accent flex items-center justify-center shadow-glow">
            <FlaskConical size={22} className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-text-primary">ResearchLens</h1>
            <p className="text-sm text-text-muted">Discover what hasn't been researched yet</p>
          </div>
        </div>
        <p className="text-sm text-text-secondary leading-relaxed">
          Upload research papers and let ResearchLens identify unexplored research gaps using
          semantic embeddings, citation analysis, and topic modelling.
        </p>
      </div>

      {/* Uploader */}
      <div className="card p-6 mb-6">
        <h2 className="text-sm font-semibold text-text-primary mb-4">Upload Papers</h2>
        <Uploader onUploaded={() => refetchPapers()} />
      </div>

      {/* Paper list */}
      {papers.length > 0 && (
        <div className="card p-6 mb-6 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text-primary">
              Corpus <span className="text-accent">({papers.length})</span>
            </h2>
          </div>
          <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
            {papers.map(p => (
              <div
                key={p.id}
                className="flex items-center gap-3 bg-bg border border-border rounded-xl px-4 py-2.5 group"
              >
                <FileText size={15} className="text-text-muted flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary truncate font-medium">
                    {p.title || p.filename}
                  </p>
                  <p className="text-xs text-text-muted">
                    {p.authors?.[0] || 'Unknown author'}
                    {p.year ? ` · ${p.year}` : ''}
                  </p>
                </div>
                <button
                  onClick={() => handleDelete(p.id)}
                  className="text-text-muted hover:text-danger opacity-0 group-hover:opacity-100 transition-all flex-shrink-0"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Analysis pipeline status */}
      {jobData && (
        <div className="mb-6">
          <StageTracker
            stage={jobData.stage}
            progress={jobData.progress}
            message={jobData.message}
          />
        </div>
      )}

      {/* CTA */}
      <div className="flex gap-3">
        <button
          onClick={handleAnalyze}
          disabled={analyzing || !papers.length}
          className="btn-primary flex-1 flex items-center justify-center gap-2 py-3"
          id="analyze-btn"
        >
          {analyzing
            ? <><Loader2 size={16} className="animate-spin" />Analyzing…</>
            : <><PlayCircle size={16} />Analyze Papers</>
          }
        </button>
        {done && (
          <button
            onClick={() => navigate('/results')}
            className="btn-secondary flex items-center gap-2 px-5"
          >
            View Results <ChevronRight size={15} />
          </button>
        )}
      </div>
    </div>
  )
}
