from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    title = Column(Text, nullable=True)
    authors = Column(JSON, default=list)        # ["Author One", "Author Two"]
    year = Column(Integer, nullable=True)
    abstract = Column(Text, nullable=True)
    full_text = Column(Text, nullable=True)
    sections = Column(JSON, default=dict)       # {"introduction": "...", ...}
    upload_time = Column(DateTime, default=datetime.utcnow)
    umap_x = Column(Float, nullable=True)
    umap_y = Column(Float, nullable=True)
    embedding = Column(JSON, nullable=True)     # [float, ...] 768-dim

    citations_made = relationship(
        "Citation",
        foreign_keys="Citation.citing_paper_id",
        back_populates="citing_paper",
    )
    citations_received = relationship(
        "Citation",
        foreign_keys="Citation.cited_paper_id",
        back_populates="cited_paper",
    )
    paper_topics = relationship("PaperTopic", back_populates="paper")


class Citation(Base):
    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, index=True)
    citing_paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    cited_paper_id = Column(Integer, ForeignKey("papers.id"), nullable=True)  # null = external
    cited_title = Column(Text, nullable=True)
    context_sentence = Column(Text, nullable=True)
    section = Column(String(100), nullable=True)

    citing_paper = relationship(
        "Paper", foreign_keys=[citing_paper_id], back_populates="citations_made"
    )
    cited_paper = relationship(
        "Paper", foreign_keys=[cited_paper_id], back_populates="citations_received"
    )


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(255), nullable=False)
    keywords = Column(JSON, default=list)           # ["keyword1", ...]
    centroid_embedding = Column(JSON, nullable=True)
    gap_score = Column(Float, default=0.0)
    struct_score = Column(Float, default=0.0)
    sem_score = Column(Float, default=0.0)
    temp_score = Column(Float, default=0.0)
    rank = Column(Integer, nullable=True)

    paper_topics = relationship("PaperTopic", back_populates="topic")
    gaps = relationship("Gap", back_populates="topic")


class PaperTopic(Base):
    __tablename__ = "paper_topics"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)

    paper = relationship("Paper", back_populates="paper_topics")
    topic = relationship("Topic", back_populates="paper_topics")


class Gap(Base):
    __tablename__ = "gaps"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    rank = Column(Integer, nullable=False)
    supporting_evidence = Column(JSON, default=list)   # ["quote1", ...]
    suggested_question = Column(Text, nullable=True)
    bordering_papers = Column(JSON, default=list)      # [paper_id, ...]

    topic = relationship("Topic", back_populates="gaps")
