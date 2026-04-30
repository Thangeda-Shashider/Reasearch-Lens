# ResearchLens 🔬

> **Citation-Aware Research Gap Identification System**  
> Upload academic PDFs → NLP pipeline → Ranked research gaps + visualizations + exportable report

---

## Quick Start

### 1. Backend (Python 3.10+)

```bash
cd researchlens/backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Copy env template
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux

uvicorn main:app --reload
```

Backend runs at **http://localhost:8000**  
API docs at **http://localhost:8000/docs**

---

### 2. Frontend (Node 18+)

```bash
cd researchlens/frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**

---

## Environment Variables (backend/.env)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./researchlens.db` | Use PostgreSQL URL for cloud |
| `REDIS_URL` | *(empty)* | Optional — in-memory cache fallback |
| `EMBEDDING_MODEL` | `allenai/specter2` | HuggingFace model name |
| `UPLOAD_DIR` | `./uploads` | PDF storage directory |
| `MIN_CLUSTER_SIZE` | `3` | BERTopic HDBSCAN minimum cluster size |
| `WEIGHT_STRUCT` | `0.40` | Citation sparsity weight |
| `WEIGHT_SEM` | `0.35` | Semantic novelty weight |
| `WEIGHT_TEMP` | `0.25` | Temporal recency weight |

### Cloud / PostgreSQL

```
DATABASE_URL=postgresql://user:password@host:5432/researchlens
```

---

## How It Works

```
PDF Upload → Text Extraction (PDFMiner/PyMuPDF)
          → Preprocessing (spaCy, NLTK)
          → SPECTER2 Embeddings (sentence-transformers)
          → Citation Graph (NetworkX)
          → BERTopic Clustering (HDBSCAN + UMAP)
          → Gap Scoring  GapScore = 0.40·S_struct + 0.35·S_sem + 0.25·S_temp
          → Ranked Research Gaps + Evidence + Visualizations
```

---

## Notes

- **First run**: SPECTER2 (~800MB) is downloaded from HuggingFace automatically
- **Minimum papers for BERTopic**: 6 (falls back to K-Means for smaller corpora)
- **RAM**: 8GB+ recommended for large corpora (50 papers)
- **Redis**: Optional — leave `REDIS_URL` empty to use in-memory embedding cache

---

## Project Structure

```
researchlens/
├── backend/
│   ├── main.py              FastAPI entry point
│   ├── config.py            Settings (pydantic-settings)
│   ├── database.py          SQLAlchemy async engine
│   ├── models/db_models.py  ORM models
│   ├── routers/             API route handlers
│   ├── services/            NLP pipeline services
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── pages/           Home, Results, Visualizations, Report, Settings
    │   ├── components/      Uploader, GapCard, TopicMap, CitationGraph, etc.
    │   └── api/client.js    Axios API wrapper
    └── package.json
```
