"""Report router — POST /api/report/export → PDF bytes"""
import io
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.db_models import Gap, Topic, Paper

router = APIRouter(prefix="/api/report", tags=["report"])


@router.post("/export")
async def export_report(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    body: {
      "format": "pdf" | "json",
      "corpus_name": str,
      "gap_ids": [int, ...],
      "custom_questions": {gap_id: str}
    }
    """
    fmt = body.get("format", "pdf")
    gap_ids: list[int] = body.get("gap_ids", [])
    corpus_name = body.get("corpus_name", "ResearchLens Corpus")
    custom_questions: dict[str, str] = body.get("custom_questions", {})

    # Fetch selected gaps
    result = await db.execute(
        select(Gap, Topic)
        .join(Topic, Gap.topic_id == Topic.id)
        .where(Gap.id.in_(gap_ids) if gap_ids else True)
        .order_by(Gap.rank)
    )
    rows = result.fetchall()

    paper_count_res = await db.execute(select(Paper.id))
    paper_count = len(paper_count_res.fetchall())

    report_data = {
        "corpus_name": corpus_name,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "papers_analyzed": paper_count,
        "gaps": [],
    }

    for gap, topic in rows:
        cq = custom_questions.get(str(gap.id), gap.suggested_question)
        report_data["gaps"].append({
            "rank": gap.rank,
            "label": topic.label,
            "keywords": topic.keywords,
            "gap_score": round(topic.gap_score, 4),
            "struct_score": round(topic.struct_score, 4),
            "sem_score": round(topic.sem_score, 4),
            "temp_score": round(topic.temp_score, 4),
            "supporting_evidence": gap.supporting_evidence or [],
            "suggested_question": cq,
            "bordering_papers": gap.bordering_papers or [],
        })

    if fmt == "json":
        return JSONResponse(content=report_data)

    # PDF generation with ReportLab
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle,
        )

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=20,
                                     spaceAfter=6, textColor=colors.HexColor("#6C63FF"))
        h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13,
                                  textColor=colors.HexColor("#4A47A3"), spaceAfter=4)
        body_style = styles["BodyText"]
        body_style.leading = 14

        story = []
        story.append(Paragraph("ResearchLens — Research Gap Report", title_style))
        story.append(Paragraph(f"Corpus: {corpus_name}", body_style))
        story.append(Paragraph(
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | "
            f"Papers Analysed: {paper_count}", body_style))
        story.append(HRFlowable(width="100%", thickness=1,
                                color=colors.HexColor("#6C63FF"), spaceAfter=12))

        for g in report_data["gaps"]:
            story.append(Paragraph(
                f"#{g['rank']} — {g['label']}  (Score: {g['gap_score']:.3f})", h2_style
            ))
            kw_text = "  |  ".join(g["keywords"][:5])
            story.append(Paragraph(f"<b>Keywords:</b> {kw_text}", body_style))
            story.append(Paragraph(
                f"<b>Score Breakdown:</b> Structural {g['struct_score']:.3f} | "
                f"Semantic {g['sem_score']:.3f} | Temporal {g['temp_score']:.3f}",
                body_style,
            ))
            if g["suggested_question"]:
                story.append(Spacer(1, 6))
                story.append(Paragraph(
                    f"<b>Suggested Research Question:</b> {g['suggested_question']}", body_style
                ))
            if g["supporting_evidence"]:
                story.append(Spacer(1, 6))
                story.append(Paragraph("<b>Supporting Evidence:</b>", body_style))
                for ev in g["supporting_evidence"][:3]:
                    story.append(Paragraph(f'• "{ev}"', body_style))
            story.append(Spacer(1, 12))
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=colors.HexColor("#cccccc"), spaceAfter=8))

        doc.build(story)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=researchlens_report.pdf"},
        )
    except ImportError:
        return JSONResponse(
            content={"error": "reportlab not installed", "data": report_data},
            status_code=500,
        )
