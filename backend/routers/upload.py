"""Upload router — POST /api/upload, GET /api/papers, DELETE /api/papers/{id}"""
import os
import shutil
import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.db_models import Paper
from services.pdf_parser import parse_pdf
from config import get_settings

router = APIRouter(prefix="/api", tags=["papers"])
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_papers(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    results = []

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            results.append({"filename": file.filename, "error": "Not a PDF file"})
            continue

        data = await file.read()
        if len(data) > max_bytes:
            results.append({
                "filename": file.filename,
                "error": f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit",
            })
            continue

        save_path = upload_dir / file.filename
        counter = 1
        while save_path.exists():
            stem = Path(file.filename).stem
            suffix = Path(file.filename).suffix
            save_path = upload_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        with open(save_path, "wb") as f:
            f.write(data)

        try:
            parsed = parse_pdf(str(save_path))
        except Exception as e:
            logger.error("PDF parse error for %s: %s", file.filename, e)
            parsed = {
                "title": Path(file.filename).stem,
                "abstract": "", "authors": [], "year": None,
                "sections": {}, "references": [], "full_text": "",
            }

        paper = Paper(
            filename=save_path.name,
            title=parsed["title"],
            authors=parsed["authors"],
            year=parsed["year"],
            abstract=parsed["abstract"],
            full_text=parsed["full_text"],
            sections=parsed["sections"],
        )
        db.add(paper)
        await db.flush()

        results.append({
            "paper_id": paper.id,
            "filename": paper.filename,
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "abstract": (paper.abstract or "")[:300],
        })

    await db.commit()
    return {"uploaded": results}


@router.get("/papers")
async def list_papers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Paper).order_by(Paper.upload_time.desc()))
    papers = result.scalars().all()
    return [
        {
            "id": p.id,
            "filename": p.filename,
            "title": p.title,
            "authors": p.authors,
            "year": p.year,
            "abstract": (p.abstract or "")[:300],
            "upload_time": p.upload_time.isoformat() if p.upload_time else None,
        }
        for p in papers
    ]


@router.delete("/papers/{paper_id}")
async def delete_paper(paper_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    settings = get_settings()
    file_path = Path(settings.UPLOAD_DIR) / paper.filename
    if file_path.exists():
        file_path.unlink()

    await db.delete(paper)
    await db.commit()
    return {"deleted": paper_id}
