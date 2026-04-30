import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { uploadPapers } from '../api/client'

export default function Uploader({ onUploaded }) {
  const [files, setFiles] = useState([])       // {file, status, progress, result}
  const [uploading, setUploading] = useState(false)

  const onDrop = useCallback((accepted, rejected) => {
    rejected.forEach(r => {
      const err = r.errors[0]
      toast.error(`${r.file.name}: ${err?.message || 'Invalid file'}`)
    })
    const newFiles = accepted.map(f => ({
      id: Math.random().toString(36).slice(2),
      file: f,
      status: 'pending',
      progress: 0,
      result: null,
    }))
    setFiles(prev => [...prev, ...newFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxSize: 20 * 1024 * 1024,
    maxFiles: 50,
  })

  const removeFile = id => setFiles(prev => prev.filter(f => f.id !== id))

  const upload = async () => {
    const pending = files.filter(f => f.status === 'pending')
    if (!pending.length) return

    setUploading(true)
    const formData = new FormData()
    pending.forEach(({ file }) => formData.append('files', file))

    setFiles(prev =>
      prev.map(f => f.status === 'pending' ? { ...f, status: 'uploading' } : f)
    )

    try {
      const { data } = await uploadPapers(formData, evt => {
        const pct = Math.round((evt.loaded / evt.total) * 100)
        setFiles(prev =>
          prev.map(f => f.status === 'uploading' ? { ...f, progress: pct } : f)
        )
      })

      const uploaded = data.uploaded || []
      setFiles(prev =>
        prev.map(f => {
          const match = uploaded.find(u => u.filename === f.file.name || u.error)
          if (!match) return f
          return {
            ...f,
            status: match.error ? 'error' : 'done',
            progress: 100,
            result: match,
          }
        })
      )

      const success = uploaded.filter(u => !u.error)
      if (success.length) {
        toast.success(`${success.length} paper${success.length > 1 ? 's' : ''} uploaded!`)
        onUploaded?.(success)
      }
      const errors = uploaded.filter(u => u.error)
      errors.forEach(e => toast.error(`${e.filename}: ${e.error}`))
    } catch (err) {
      toast.error('Upload failed: ' + (err.response?.data?.detail || err.message))
      setFiles(prev => prev.map(f => f.status === 'uploading' ? { ...f, status: 'error' } : f))
    } finally {
      setUploading(false)
    }
  }

  const statusIcon = status => {
    if (status === 'done') return <CheckCircle size={15} className="text-success" />
    if (status === 'error') return <AlertCircle size={15} className="text-danger" />
    if (status === 'uploading') return <Loader2 size={15} className="text-accent animate-spin" />
    return <FileText size={15} className="text-text-muted" />
  }

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer
          transition-all duration-300 group
          ${isDragActive
            ? 'border-accent bg-accent-glow scale-[1.01]'
            : 'border-border hover:border-accent/50 hover:bg-white/[0.02]'
          }
        `}
      >
        <input {...getInputProps()} />
        <div className={`w-14 h-14 mx-auto mb-4 rounded-2xl flex items-center justify-center transition-colors ${
          isDragActive ? 'bg-accent text-white' : 'bg-card-hover text-text-muted group-hover:text-accent'
        }`}>
          <Upload size={26} />
        </div>
        <p className="text-base font-semibold text-text-primary mb-1">
          {isDragActive ? 'Drop your PDFs here' : 'Drag & drop research papers'}
        </p>
        <p className="text-sm text-text-muted">
          PDF only · up to 50 files · max 20 MB each
        </p>
        <button
          type="button"
          className="mt-4 btn-secondary text-sm"
          onClick={e => e.stopPropagation()}
        >
          Browse files
        </button>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="section-label">{files.length} file{files.length > 1 ? 's' : ''} selected</p>
            {files.some(f => f.status !== 'done') && (
              <button
                onClick={() => setFiles([])}
                className="text-xs text-text-muted hover:text-danger transition-colors"
              >
                Clear all
              </button>
            )}
          </div>
          <div className="space-y-1.5 max-h-72 overflow-y-auto pr-1">
            {files.map(({ id, file, status, progress, result }) => (
              <div
                key={id}
                className="flex items-center gap-3 bg-card border border-border rounded-xl px-4 py-2.5 animate-fade-in"
              >
                {statusIcon(status)}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary truncate font-medium">
                    {result?.title || file.name}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <p className="text-xs text-text-muted">
                      {(file.size / 1024 / 1024).toFixed(1)} MB
                      {result?.year ? ` · ${result.year}` : ''}
                      {result?.authors?.[0] ? ` · ${result.authors[0]}` : ''}
                    </p>
                    {status === 'uploading' && (
                      <div className="flex-1 h-1 bg-border rounded-full overflow-hidden">
                        <div
                          className="h-full bg-accent rounded-full transition-all"
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                    )}
                  </div>
                </div>
                {status !== 'uploading' && (
                  <button
                    onClick={() => removeFile(id)}
                    className="text-text-muted hover:text-danger transition-colors flex-shrink-0"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload button */}
      {files.some(f => f.status === 'pending') && (
        <button
          onClick={upload}
          disabled={uploading}
          className="btn-primary w-full flex items-center justify-center gap-2"
        >
          {uploading
            ? <><Loader2 size={16} className="animate-spin" />Uploading…</>
            : <><Upload size={16} />Upload {files.filter(f => f.status === 'pending').length} Paper{files.filter(f => f.status === 'pending').length > 1 ? 's' : ''}</>
          }
        </button>
      )}
    </div>
  )
}
