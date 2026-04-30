"""
Gap scoring engine.

GapScore(Tk) = 0.40 * S_struct + 0.35 * S_sem + 0.25 * S_temp

S_struct = citation sparsity  (from citation_graph.compute_struct_score)
S_sem    = 1 - cosine_similarity(cluster_centroid, corpus_centroid)
S_temp   = 1 / (1 + mean_publication_age_in_years)
"""
import logging
import random
from datetime import datetime
from typing import Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

CURRENT_YEAR = datetime.utcnow().year

# --------------------------------------------------------------------------
# Categorised question templates — chosen based on the dominant gap signal.
# {primary} = most important keyword phrase
# {secondary} = supporting keyword phrase  
# {domain} = human-readable topic label
# --------------------------------------------------------------------------

# Used when citation sparsity (struct score) is the dominant gap signal
_STRUCT_TEMPLATES = [
    "How can {primary} be studied more systematically to address the lack of peer validation and citation support in {domain}?",
    "What experimental frameworks would enable the research community to build a stronger empirical foundation for {primary} within {domain}?",
    "Why does {primary} remain sparsely cited in {domain}, and what collaborative research directions could bridge this gap?",
    "How can future studies connect {primary} with well-established approaches in {domain} to increase its academic impact?",
]

# Used when semantic novelty (sem score) is the dominant gap signal
_SEM_TEMPLATES = [
    "What novel approaches to {primary} could open entirely new research directions that current literature in {domain} has not yet explored?",
    "How might combining {primary} with {secondary} produce breakthrough insights that existing work in {domain} has overlooked?",
    "In what ways does {primary} represent an under-explored frontier that could substantially redefine our understanding of {domain}?",
    "What interdisciplinary perspectives could shed new light on {primary} and accelerate progress in {domain}?",
]

# Used when temporal recency (temp score) is the dominant gap signal
_TEMP_TEMPLATES = [
    "How have recent advances in {primary} changed the research landscape of {domain}, and what questions remain unanswered?",
    "What emerging challenges in {primary} require urgent investigation to keep pace with rapid developments in {domain}?",
    "How can early findings on {primary} be scaled or validated to solidify their role in the evolving field of {domain}?",
    "What longitudinal studies are needed to track the impact of {primary} on {domain} as the field continues to mature?",
]

# Generic fallback templates
_GENERIC_TEMPLATES = [
    "What are the most critical unresolved challenges surrounding {primary} in the context of {domain}?",
    "How can researchers design studies that more rigorously assess the role of {primary} within {domain}?",
    "What conditions or factors moderate the relationship between {primary} and outcomes studied in {domain}?",
    "How does {primary} interact with {secondary} to shape the key open problems in {domain}?",
]


def _cosine_sim(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    va = np.array(a, dtype=np.float32).reshape(1, -1)
    vb = np.array(b, dtype=np.float32).reshape(1, -1)
    return float(cosine_similarity(va, vb)[0][0])


def compute_s_sem(cluster_centroid: list[float], corpus_centroid: list[float]) -> float:
    """Semantic novelty: how far is this cluster from the overall corpus centre."""
    return max(0.0, min(1.0, 1.0 - _cosine_sim(cluster_centroid, corpus_centroid)))


def compute_s_temp(
    cluster_paper_years: list[Optional[int]],
    current_year: int = CURRENT_YEAR,
) -> float:
    """
    Temporal recency score.
    Recent clusters (newer papers) get a higher score because older topics are
    more likely to be already well-covered. But very under-explored recent
    areas are strong gap candidates.
    Score = 1 / (1 + mean_age). Ranges (0, 1].
    """
    valid = [y for y in cluster_paper_years if y and 1900 < y <= current_year]
    if not valid:
        return 0.5
    mean_age = current_year - (sum(valid) / len(valid))
    return float(1.0 / (1.0 + max(0.0, mean_age)))


def compute_gap_score(
    s_struct: float,
    s_sem: float,
    s_temp: float,
    w_struct: float = 0.40,
    w_sem: float = 0.35,
    w_temp: float = 0.25,
) -> float:
    return round(w_struct * s_struct + w_sem * s_sem + w_temp * s_temp, 6)


def _clean_keyword(kw: str) -> str:
    """Capitalise and strip underscores/hyphens for natural reading."""
    return kw.replace("_", " ").replace("-", " ").strip().capitalize()


def _generate_question(
    keywords: list[str],
    domain: str,
    s_struct: float = 0.0,
    s_sem: float = 0.0,
    s_temp: float = 0.0,
) -> str:
    """
    Generate a clear, natural-language research question tailored to the
    dominant gap signal (structural sparsity, semantic novelty, or temporal recency).
    """
    # Clean keywords into readable phrases
    clean_kws = [_clean_keyword(k) for k in keywords if k.strip()]

    # Build primary and secondary keyword phrases
    if len(clean_kws) >= 2:
        primary = " and ".join(clean_kws[:2])
        secondary = clean_kws[2] if len(clean_kws) > 2 else clean_kws[0]
    elif len(clean_kws) == 1:
        primary = clean_kws[0]
        secondary = "related methodologies"
    else:
        primary = "this research area"
        secondary = "established approaches"

    # Clean domain label
    domain_label = (
        domain.replace("_", " ").strip().capitalize()
        if domain
        else "the research domain"
    )

    # Choose template bank based on the dominant gap dimension
    scores = {"struct": s_struct, "sem": s_sem, "temp": s_temp}
    dominant = max(scores, key=scores.get)  # type: ignore[arg-type]

    if dominant == "struct" and s_struct > 0.1:
        templates = _STRUCT_TEMPLATES
    elif dominant == "sem" and s_sem > 0.1:
        templates = _SEM_TEMPLATES
    elif dominant == "temp" and s_temp > 0.1:
        templates = _TEMP_TEMPLATES
    else:
        templates = _GENERIC_TEMPLATES

    template = random.choice(templates)
    return template.format(primary=primary, secondary=secondary, domain=domain_label)


def _find_evidence(
    paper_sections: list[dict],
    keywords: list[str],
    n: int = 5,
) -> list[str]:
    """
    Find sentences from papers mentioning gap keywords.
    paper_sections: [{"sentences": [str,...], "section": str}]
    """
    evidence: list[str] = []
    kw_lower = [k.lower() for k in keywords]
    for item in paper_sections:
        for sent in item.get("sentences", []):
            if len(evidence) >= n:
                return evidence
            sent_lower = sent.lower()
            if any(kw in sent_lower for kw in kw_lower):
                evidence.append(sent.strip())
    return evidence


def _find_bordering_papers(
    topic_paper_ids: list[int],
    all_paper_ids: list[int],
    embeddings_map: dict[int, np.ndarray],
    topic_centroid: list[float],
    k: int = 5,
) -> list[int]:
    """
    Find papers outside this cluster whose embeddings are closest to the cluster centroid.
    These are 'neighbouring' papers on adjacent topics — useful pointers for gap bridging.
    """
    outside = [pid for pid in all_paper_ids if pid not in topic_paper_ids]
    if not outside or not topic_centroid:
        return []

    centroid = np.array(topic_centroid, dtype=np.float32).reshape(1, -1)
    scored: list[tuple[float, int]] = []
    for pid in outside:
        emb = embeddings_map.get(pid)
        if emb is None:
            continue
        sim = float(cosine_similarity(emb.reshape(1, -1), centroid)[0][0])
        scored.append((sim, pid))

    scored.sort(reverse=True)
    return [pid for _, pid in scored[:k]]


def score_gaps(
    topics: list[dict],
    corpus_centroid: list[float],
    graph_metrics: dict[int, dict],
    paper_years: dict[int, Optional[int]],
    paper_sections_map: dict[int, dict[str, list[str]]],
    embeddings_map: dict[int, np.ndarray],
    all_paper_ids: list[int],
    weights: tuple[float, float, float] = (0.40, 0.35, 0.25),
) -> list[dict]:
    """
    Compute gap scores for every topic cluster and return ranked gap list.

    topics: output from topic_cluster.cluster_papers()["topics"]
    Returns list of gap dicts sorted by gap_score descending.
    """
    from services.citation_graph import compute_struct_score

    scored_gaps: list[dict] = []

    for topic in topics:
        tid = topic["topic_id"]
        pids = topic["paper_ids"]
        keywords = topic["keywords"]
        centroid = topic.get("centroid_embedding", [])

        if tid == -1 or not pids:
            continue  # Skip BERTopic noise cluster

        s_struct = compute_struct_score(pids, graph_metrics)
        s_sem = compute_s_sem(centroid, corpus_centroid)
        s_temp = compute_s_temp([paper_years.get(p) for p in pids])
        gap_score = compute_gap_score(s_struct, s_sem, s_temp, *weights)

        # Gather sentences from all papers in this cluster
        cluster_sections: list[dict] = []
        for pid in pids:
            secs = paper_sections_map.get(pid, {})
            for sec_name, sents in secs.items():
                cluster_sections.append({"section": sec_name, "sentences": sents})

        evidence = _find_evidence(cluster_sections, keywords)
        bordering = _find_bordering_papers(
            pids, all_paper_ids, embeddings_map, centroid
        )
        question = _generate_question(
            keywords,
            topic.get("label", ""),
            s_struct=s_struct,
            s_sem=s_sem,
            s_temp=s_temp,
        )

        scored_gaps.append({
            "topic_id": tid,
            "label": topic.get("label", ""),
            "keywords": keywords[:10],
            "gap_score": gap_score,
            "struct_score": round(s_struct, 4),
            "sem_score": round(s_sem, 4),
            "temp_score": round(s_temp, 4),
            "paper_ids": pids,
            "supporting_evidence": evidence,
            "bordering_papers": bordering,
            "suggested_question": question,
        })

    # Rank by gap_score descending
    scored_gaps.sort(key=lambda g: g["gap_score"], reverse=True)
    for rank, gap in enumerate(scored_gaps, start=1):
        gap["rank"] = rank

    return scored_gaps
