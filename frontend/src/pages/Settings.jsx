import { useState } from 'react'
import { Settings as SettingsIcon, Save, RotateCcw } from 'lucide-react'
import toast from 'react-hot-toast'

const DEFAULTS = {
  weightStruct: 0.40,
  weightSem: 0.35,
  weightTemp: 0.25,
  minClusterSize: 3,
  yearStart: 2000,
  yearEnd: 2024,
  embeddingModel: 'allenai/specter2',
}

const MODELS = [
  { value: 'allenai/specter2', label: 'SPECTER2 (Recommended)' },
  { value: 'allenai/scibert_scivocab_uncased', label: 'SciBERT' },
  { value: 'bert-base-uncased', label: 'BERT-base' },
]

function Slider({ label, value, onChange, min = 0, max = 1, step = 0.01, display }) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <label className="text-sm text-text-secondary">{label}</label>
        <span className="text-sm font-semibold text-accent">
          {display ? display(value) : value}
        </span>
      </div>
      <input
        type="range" min={min} max={max} step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full accent-[#6C63FF]"
      />
    </div>
  )
}

export default function Settings() {
  const [cfg, setCfg] = useState(() => {
    try { return { ...DEFAULTS, ...JSON.parse(localStorage.getItem('rl_settings') || '{}') } }
    catch { return DEFAULTS }
  })

  const set = key => val => setCfg(prev => ({ ...prev, [key]: val }))

  const weightSum = (cfg.weightStruct + cfg.weightSem + cfg.weightTemp).toFixed(2)
  const weightOk = Math.abs(Number(weightSum) - 1.0) < 0.001

  const handleSave = () => {
    if (!weightOk) {
      toast.error(`Weights must sum to 1.0 (currently ${weightSum})`)
      return
    }
    localStorage.setItem('rl_settings', JSON.stringify(cfg))
    toast.success('Settings saved! They will apply on the next analysis run.')
  }

  const handleReset = () => {
    setCfg(DEFAULTS)
    localStorage.removeItem('rl_settings')
    toast.success('Settings reset to defaults.')
  }

  return (
    <div className="p-8 max-w-xl mx-auto">
      <div className="mb-8 animate-fade-in">
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3 mb-1">
          <SettingsIcon size={22} className="text-accent" />
          Analysis Settings
        </h1>
        <p className="text-sm text-text-muted">
          Adjust NLP pipeline parameters. Changes apply on the next analysis run.
        </p>
      </div>

      <div className="space-y-6 animate-fade-in">
        {/* Gap Score Weights */}
        <div className="card p-6 space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-text-primary">Gap Score Weights</h2>
            <span className={`text-xs font-semibold px-2.5 py-1 rounded-lg ${weightOk
                ? 'bg-success-dim text-success border border-success/30'
                : 'bg-danger-dim text-danger border border-danger/30'
              }`}>
              Sum: {weightSum}
            </span>
          </div>
          <Slider
            label="Structural (Citation Sparsity)"
            value={cfg.weightStruct}
            onChange={set('weightStruct')}
            display={v => `${(v * 100).toFixed(0)}%`}
          />
          <Slider
            label="Semantic (Embedding Novelty)"
            value={cfg.weightSem}
            onChange={set('weightSem')}
            display={v => `${(v * 100).toFixed(0)}%`}
          />
          <Slider
            label="Temporal (Recency)"
            value={cfg.weightTemp}
            onChange={set('weightTemp')}
            display={v => `${(v * 100).toFixed(0)}%`}
          />
          {!weightOk && (
            <p className="text-xs text-danger">
              ⚠ Weights must sum to 1.00. Current sum: {weightSum}
            </p>
          )}
        </div>

        {/* Clustering */}
        <div className="card p-6 space-y-5">
          <h2 className="text-sm font-semibold text-text-primary">Topic Clustering</h2>
          <Slider
            label="Minimum Cluster Size"
            value={cfg.minClusterSize}
            onChange={set('minClusterSize')}
            min={2} max={20} step={1}
            display={v => v}
          />
        </div>

        {/* Temporal */}
        <div className="card p-6 space-y-5">
          <h2 className="text-sm font-semibold text-text-primary">Temporal Filter</h2>
          <Slider
            label="Year Range Start"
            value={cfg.yearStart}
            onChange={set('yearStart')}
            min={1990} max={2024} step={1}
            display={v => v}
          />
          <Slider
            label="Year Range End"
            value={cfg.yearEnd}
            onChange={set('yearEnd')}
            min={1990} max={2025} step={1}
            display={v => v}
          />
        </div>

        {/* Embedding Model */}
        <div className="card p-6 space-y-3">
          <h2 className="text-sm font-semibold text-text-primary">Embedding Model</h2>
          <p className="text-xs text-text-muted">
            SPECTER2 is optimised for scientific papers and recommended. Changing model
            invalidates the embedding cache.
          </p>
          <div className="space-y-2">
            {MODELS.map(m => (
              <label
                key={m.value}
                className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all ${cfg.embeddingModel === m.value
                    ? 'border-accent/50 bg-accent-glow'
                    : 'border-border hover:border-accent/30'
                  }`}
              >
                <input
                  type="radio"
                  name="model"
                  value={m.value}
                  checked={cfg.embeddingModel === m.value}
                  onChange={() => set('embeddingModel')(m.value)}
                  className="accent-[#6C63FF]"
                />
                <div>
                  <p className="text-sm font-medium text-text-primary">{m.label}</p>
                  <p className="text-xs text-text-muted">{m.value}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button onClick={handleSave} className="btn-primary flex-1 flex items-center justify-center gap-2">
            <Save size={15} />Save Settings
          </button>
          <button onClick={handleReset} className="btn-secondary flex items-center gap-2 px-5">
            <RotateCcw size={14} />Reset
          </button>
        </div>
      </div>
    </div>
  )
}
