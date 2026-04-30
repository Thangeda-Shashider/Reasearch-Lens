"""
Citation graph module.
Builds a directed graph (NetworkX DiGraph) from in-corpus and extracted reference data.
Computes: in-degree, out-degree, PageRank, citation density per cluster.
"""
import logging
import re
from difflib import SequenceMatcher
from typing import Optional

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


def _title_similarity(a: str, b: str) -> float:
    a = a.lower().strip()
    b = b.lower().strip()
    return SequenceMatcher(None, a, b).ratio()


def match_reference_to_corpus(
    ref_string: str, corpus_papers: list[dict]
) -> Optional[int]:
    """
    Try to match a raw reference string to a paper in the corpus by title similarity.
    Returns paper_id or None.
    """
    best_score = 0.0
    best_id: Optional[int] = None
    for paper in corpus_papers:
        title = paper.get("title") or ""
        if not title:
            continue
        score = _title_similarity(ref_string, title)
        # Also try matching a substring
        if title.lower() in ref_string.lower():
            score = max(score, 0.85)
        if score > best_score:
            best_score = score
            best_id = paper["id"]
    return best_id if best_score >= 0.65 else None


def build_citation_graph(
    papers: list[dict],
    citations: list[dict],
) -> nx.DiGraph:
    """
    Build a directed citation graph.

    papers: [{"id": int, "title": str, ...}]
    citations: [{"citing_paper_id": int, "cited_paper_id": int | None}]
    """
    G = nx.DiGraph()

    # Add all corpus papers as nodes
    for p in papers:
        G.add_node(p["id"], title=p.get("title", ""), year=p.get("year"))

    # Add edges for in-corpus citations only (cited_paper_id is not None)
    for cit in citations:
        src = cit.get("citing_paper_id")
        dst = cit.get("cited_paper_id")
        if src and dst and G.has_node(src) and G.has_node(dst):
            G.add_edge(src, dst)

    return G


def compute_graph_metrics(G: nx.DiGraph) -> dict[int, dict]:
    """
    Returns per-node metrics:
      {node_id: {"in_degree": int, "out_degree": int, "pagerank": float}}
    """
    if len(G) == 0:
        return {}

    try:
        pagerank = nx.pagerank(G, alpha=0.85, max_iter=200)
    except nx.PowerIterationFailedConvergence:
        pagerank = {n: 1.0 / len(G) for n in G.nodes()}

    metrics: dict[int, dict] = {}
    for node in G.nodes():
        metrics[node] = {
            "in_degree": G.in_degree(node),
            "out_degree": G.out_degree(node),
            "pagerank": pagerank.get(node, 0.0),
        }
    return metrics


def compute_struct_score(
    cluster_paper_ids: list[int],
    metrics: dict[int, dict],
) -> float:
    """
    Citation sparsity score for a topic cluster.
    S_struct(Tk) = (1/|Tk|) * sum(1 / (1 + in_degree(v))) for v in Tk
    Higher score = sparser citations = bigger potential gap.
    """
    if not cluster_paper_ids:
        return 0.0
    total = sum(
        1.0 / (1.0 + metrics.get(pid, {}).get("in_degree", 0))
        for pid in cluster_paper_ids
    )
    return float(total / len(cluster_paper_ids))


def get_weakly_connected_components(G: nx.DiGraph) -> list[list[int]]:
    return [list(c) for c in nx.weakly_connected_components(G)]


def graph_to_json(G: nx.DiGraph, metrics: dict[int, dict], topic_map: dict[int, int]) -> dict:
    """
    Serialize graph for the frontend force-directed visualisation.
    topic_map: {paper_id -> topic_id}
    """
    nodes = []
    for node in G.nodes():
        m = metrics.get(node, {})
        nodes.append({
            "id": node,
            "title": G.nodes[node].get("title", f"Paper {node}"),
            "year": G.nodes[node].get("year"),
            "in_degree": m.get("in_degree", 0),
            "out_degree": m.get("out_degree", 0),
            "pagerank": round(m.get("pagerank", 0.0), 6),
            "topic_id": topic_map.get(node),
        })

    links = [
        {"source": u, "target": v}
        for u, v in G.edges()
    ]

    return {"nodes": nodes, "links": links}
