"""Visualisations router — UMAP coordinates and citation graph JSON."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.db_models import Paper, PaperTopic, Topic, Citation

router = APIRouter(prefix="/api/visualizations", tags=["visualizations"])


@router.get("/umap")
async def get_umap(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Paper, PaperTopic, Topic)
        .outerjoin(PaperTopic, Paper.id == PaperTopic.paper_id)
        .outerjoin(Topic, PaperTopic.topic_id == Topic.id)
    )
    rows = result.fetchall()

    points = []
    seen = set()
    for paper, pt, topic in rows:
        if paper.id in seen:
            continue
        seen.add(paper.id)
        points.append({
            "paper_id": paper.id,
            "title": paper.title,
            "year": paper.year,
            "x": paper.umap_x,
            "y": paper.umap_y,
            "topic_id": topic.id if topic else None,
            "topic_label": topic.label if topic else "Unclustered",
            "gap_score": round(topic.gap_score, 4) if topic else None,
        })

    return {"points": points, "total": len(points)}


@router.get("/graph")
async def get_citation_graph(db: AsyncSession = Depends(get_db)):
    paper_result = await db.execute(select(Paper))
    papers = paper_result.scalars().all()

    # Get topic assignment per paper
    pt_result = await db.execute(select(PaperTopic, Topic).join(Topic))
    topic_map: dict[int, dict] = {}
    for pt, topic in pt_result.fetchall():
        topic_map[pt.paper_id] = {
            "topic_id": topic.id,
            "topic_label": topic.label,
            "gap_score": topic.gap_score,
        }

    cit_result = await db.execute(
        select(Citation).where(Citation.cited_paper_id.isnot(None))
    )
    citations = cit_result.scalars().all()

    nodes = []
    for p in papers:
        in_deg = sum(1 for c in citations if c.cited_paper_id == p.id)
        tm = topic_map.get(p.id, {})
        nodes.append({
            "id": p.id,
            "title": p.title or f"Paper {p.id}",
            "year": p.year,
            "in_degree": in_deg,
            "topic_id": tm.get("topic_id"),
            "topic_label": tm.get("topic_label", "Unclustered"),
            "gap_score": tm.get("gap_score"),
        })

    links = [
        {"source": c.citing_paper_id, "target": c.cited_paper_id}
        for c in citations
    ]

    # Citation density per topic
    from sqlalchemy import func
    topic_result = await db.execute(select(Topic).order_by(Topic.rank))
    topics = topic_result.scalars().all()
    density_data = [
        {
            "topic_id": t.id,
            "label": t.label,
            "struct_score": round(t.struct_score, 4),
            "gap_score": round(t.gap_score, 4),
            "paper_count": sum(1 for pt_pid, tm_data in topic_map.items() if tm_data.get("topic_id") == t.id),
        }
        for t in topics
    ]

    return {
        "nodes": nodes,
        "links": links,
        "density": density_data,
    }
