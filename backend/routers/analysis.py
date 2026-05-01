"""
Analysis router — POST /api/analyze, GET /api/status/{job_id}
Runs the full NLP pipeline in a background thread.
"""
import uuid
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from database import get_db, AsyncSessionLocal
from models.db_models import Paper, Citation, Topic, PaperTopic, Gap
from config import get_settings

router = APIRouter(prefix="/api", tags=["analysis"])
logger = logging.getLogger(__name__)

# In-memory job store (use Redis/Celery for production at scale)
_jobs: dict[str, dict] = {}
_executor = ThreadPoolExecutor(max_workers=2)


def _update_job(job_id: str, stage: str, progress: int, message: str = "") -> None:
    if job_id in _jobs:
        _jobs[job_id].update({
            "stage": stage, "progress": progress,
            "message": message, "updated_at": datetime.utcnow().isoformat(),
        })


def _run_pipeline(job_id: str, paper_ids: list[int], settings_dict: dict) -> None:
    """Synchronous pipeline — runs in ThreadPoolExecutor."""
    import numpy as np
    from services.preprocessor import preprocess_paper
    from services.embedder import embed_batch, compute_corpus_centroid
    from services.citation_graph import (
        build_citation_graph, compute_graph_metrics, match_reference_to_corpus,
    )
    from services.topic_cluster import cluster_papers
    from services.gap_scorer import score_gaps

    import asyncio

    async def _run():
        async with AsyncSessionLocal() as db:
            try:
                _update_job(job_id, "extracting", 10, "Loading papers from database…")

                result = await db.execute(
                    select(Paper).where(Paper.id.in_(paper_ids))
                )
                papers = result.scalars().all()
                if not papers:
                    raise ValueError("No papers found for the given IDs")

                paper_dicts = [
                    {
                        "id": p.id, "title": p.title or "",
                        "abstract": p.abstract or "", "year": p.year,
                        "sections": p.sections or {},
                        "filename": p.filename,
                        "references": [],  # already parsed at upload
                    }
                    for p in papers
                ]

                _update_job(job_id, "extracting", 20, "Preprocessing text…")
                sections_map: dict[int, dict] = {}
                for pdict in paper_dicts:
                    processed = preprocess_paper(pdict["sections"])
                    sections_map[pdict["id"]] = processed

                _update_job(job_id, "embedding", 35, "Generating SPECTER2 embeddings…")
                embeddings_np = embed_batch(
                    paper_dicts,
                    model_name=settings_dict["EMBEDDING_MODEL"],
                    redis_url=settings_dict["REDIS_URL"],
                )
                corpus_centroid = compute_corpus_centroid(embeddings_np).tolist()
                embeddings_map: dict[int, np.ndarray] = {
                    p["id"]: embeddings_np[i] for i, p in enumerate(paper_dicts)
                }

                # Store embeddings on Paper rows
                for p in papers:
                    emb = embeddings_map.get(p.id)
                    if emb is not None:
                        p.embedding = emb.tolist()
                await db.flush()

                _update_job(job_id, "embedding", 50, "Building citation graph…")
                # Build citation edges from reference lists (fuzzy match to corpus)
                await db.execute(
                    delete(Citation).where(
                        Citation.citing_paper_id.in_(paper_ids)
                    )
                )
                citations_data: list[dict] = []
                for pdict in paper_dicts:
                    for ref_str in pdict.get("references", []):
                        matched_id = match_reference_to_corpus(ref_str, paper_dicts)
                        cit = Citation(
                            citing_paper_id=pdict["id"],
                            cited_paper_id=matched_id,
                            cited_title=ref_str[:300],
                        )
                        db.add(cit)
                        citations_data.append({
                            "citing_paper_id": pdict["id"],
                            "cited_paper_id": matched_id,
                        })
                await db.flush()

                G = build_citation_graph(paper_dicts, citations_data)
                graph_metrics = compute_graph_metrics(G)
                paper_years = {p.id: p.year for p in papers}

                _update_job(job_id, "clustering", 65, "Running BERTopic clustering…")
                docs = [f"{p['title']} {p['abstract']}" for p in paper_dicts]
                cluster_result = cluster_papers(
                    paper_ids=[p["id"] for p in paper_dicts],
                    docs=docs,
                    embeddings=embeddings_np,
                    min_cluster_size=settings_dict["MIN_CLUSTER_SIZE"],
                )

                # Store UMAP coordinates on Paper rows
                for p in papers:
                    coords = cluster_result["umap_coords"].get(p.id)
                    if coords:
                        p.umap_x = coords["x"]
                        p.umap_y = coords["y"]
                await db.flush()

                _update_job(job_id, "scoring", 80, "Scoring research gaps…")

                # Clear previous topics / gaps for these papers
                topic_ids_res = await db.execute(
                    select(PaperTopic.topic_id).where(
                        PaperTopic.paper_id.in_(paper_ids)
                    )
                )
                old_topic_ids = [r[0] for r in topic_ids_res.fetchall()]
                if old_topic_ids:
                    await db.execute(
                        delete(Gap).where(Gap.topic_id.in_(old_topic_ids))
                    )
                    await db.execute(
                        delete(PaperTopic).where(
                            PaperTopic.paper_id.in_(paper_ids)
                        )
                    )
                    await db.execute(
                        delete(Topic).where(Topic.id.in_(old_topic_ids))
                    )
                await db.flush()

                weights = (
                    settings_dict["WEIGHT_STRUCT"],
                    settings_dict["WEIGHT_SEM"],
                    settings_dict["WEIGHT_TEMP"],
                )
                gaps = score_gaps(
                    topics=cluster_result["topics"],
                    corpus_centroid=corpus_centroid,
                    graph_metrics=graph_metrics,
                    paper_years=paper_years,
                    paper_sections_map=sections_map,
                    embeddings_map=embeddings_map,
                    all_paper_ids=[p["id"] for p in paper_dicts],
                    weights=weights,
                )

                # Persist topics + gaps
                topic_assignment = cluster_result["topic_assignments"]
                for topic_data in cluster_result["topics"]:
                    if topic_data["topic_id"] == -1:
                        continue
                    db_topic = Topic(
                        label=topic_data["label"],
                        keywords=topic_data["keywords"],
                        centroid_embedding=topic_data.get("centroid_embedding"),
                    )
                    db.add(db_topic)
                    await db.flush()

                    for pid in topic_data["paper_ids"]:
                        db.add(PaperTopic(paper_id=pid, topic_id=db_topic.id))

                    # Find corresponding gap data
                    matched_gap = next(
                        (g for g in gaps if g["topic_id"] == topic_data["topic_id"]),
                        None,
                    )
                    if matched_gap:
                        db_topic.gap_score = matched_gap["gap_score"]
                        db_topic.struct_score = matched_gap["struct_score"]
                        db_topic.sem_score = matched_gap["sem_score"]
                        db_topic.temp_score = matched_gap["temp_score"]
                        db_topic.rank = matched_gap["rank"]

                        db_gap = Gap(
                            topic_id=db_topic.id,
                            rank=matched_gap["rank"],
                            supporting_evidence=matched_gap["supporting_evidence"],
                            suggested_question=matched_gap["suggested_question"],
                            bordering_papers=matched_gap["bordering_papers"],
                        )
                        db.add(db_gap)

                await db.commit()
                _update_job(job_id, "done", 100, "Analysis complete!")

            except Exception as exc:
                logger.exception("Pipeline failed for job %s", job_id)
                await db.rollback()
                _update_job(job_id, "failed", 0, str(exc))

    # On Windows, each ThreadPoolExecutor thread needs its own event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()


@router.post("/analyze")
async def start_analysis(
    body: dict = Body(default={}),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    result = await db.execute(select(Paper.id))
    paper_ids = [row[0] for row in result.fetchall()]
    if not paper_ids:
        raise HTTPException(status_code=400, detail="No papers uploaded yet")

    # Allow caller to override weights
    settings_dict = {
        "EMBEDDING_MODEL": settings.EMBEDDING_MODEL,
        "REDIS_URL": settings.REDIS_URL,
        "MIN_CLUSTER_SIZE": body.get("min_cluster_size", settings.MIN_CLUSTER_SIZE),
        "WEIGHT_STRUCT": body.get("weight_struct", settings.WEIGHT_STRUCT),
        "WEIGHT_SEM": body.get("weight_sem", settings.WEIGHT_SEM),
        "WEIGHT_TEMP": body.get("weight_temp", settings.WEIGHT_TEMP),
    }

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "job_id": job_id,
        "stage": "pending",
        "progress": 0,
        "message": "Queued…",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _run_pipeline, job_id, paper_ids, settings_dict)

    return {"job_id": job_id, "paper_count": len(paper_ids)}


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
