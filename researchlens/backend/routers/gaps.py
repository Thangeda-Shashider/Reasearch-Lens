"""Gaps router — GET /api/gaps, GET /api/gaps/{gap_id}"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from database import get_db
from models.db_models import Gap, Topic, PaperTopic, Paper

router = APIRouter(prefix="/api", tags=["gaps"])


@router.get("/gaps")
async def list_gaps(
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    max_score: float = Query(1.0, ge=0.0, le=1.0),
    year_start: Optional[int] = Query(None),
    year_end: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Gap, Topic)
        .join(Topic, Gap.topic_id == Topic.id)
        .where(Topic.gap_score >= min_score, Topic.gap_score <= max_score)
        .order_by(Gap.rank)
    )
    rows = result.fetchall()

    gaps = []
    for gap, topic in rows:
        # Year filter: get papers for this topic
        if year_start or year_end:
            pt_result = await db.execute(
                select(Paper.year)
                .join(PaperTopic, Paper.id == PaperTopic.paper_id)
                .where(PaperTopic.topic_id == topic.id)
            )
            years = [r[0] for r in pt_result.fetchall() if r[0]]
            if years:
                mean_year = sum(years) / len(years)
                if year_start and mean_year < year_start:
                    continue
                if year_end and mean_year > year_end:
                    continue

        gaps.append({
            "id": gap.id,
            "topic_id": gap.topic_id,
            "rank": gap.rank,
            "label": topic.label,
            "keywords": topic.keywords,
            "gap_score": round(topic.gap_score, 4),
            "struct_score": round(topic.struct_score, 4),
            "sem_score": round(topic.sem_score, 4),
            "temp_score": round(topic.temp_score, 4),
            "supporting_evidence": gap.supporting_evidence or [],
            "suggested_question": gap.suggested_question,
            "bordering_papers": gap.bordering_papers or [],
        })

    return {"gaps": gaps, "total": len(gaps)}


@router.get("/gaps/{gap_id}")
async def get_gap(gap_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Gap, Topic)
        .join(Topic, Gap.topic_id == Topic.id)
        .where(Gap.id == gap_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Gap not found")

    gap, topic = row

    # Fetch papers in this topic
    pt_result = await db.execute(
        select(Paper)
        .join(PaperTopic, Paper.id == PaperTopic.paper_id)
        .where(PaperTopic.topic_id == topic.id)
    )
    papers = pt_result.scalars().all()

    # Fetch bordering paper details
    bordering_ids = gap.bordering_papers or []
    bordering_papers = []
    if bordering_ids:
        b_result = await db.execute(
            select(Paper).where(Paper.id.in_(bordering_ids))
        )
        bordering_papers = [
            {"id": p.id, "title": p.title, "year": p.year, "authors": p.authors}
            for p in b_result.scalars().all()
        ]

    return {
        "id": gap.id,
        "topic_id": gap.topic_id,
        "rank": gap.rank,
        "label": topic.label,
        "keywords": topic.keywords,
        "gap_score": round(topic.gap_score, 4),
        "struct_score": round(topic.struct_score, 4),
        "sem_score": round(topic.sem_score, 4),
        "temp_score": round(topic.temp_score, 4),
        "supporting_evidence": gap.supporting_evidence or [],
        "suggested_question": gap.suggested_question,
        "papers": [
            {"id": p.id, "title": p.title, "year": p.year, "authors": p.authors}
            for p in papers
        ],
        "bordering_papers": bordering_papers,
    }
