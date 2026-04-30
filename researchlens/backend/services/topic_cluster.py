"""
Topic clustering via BERTopic + HDBSCAN + UMAP on SPECTER2 embeddings.
Returns cluster assignments, 2D UMAP coordinates, and per-topic keywords.
Gracefully degrades to K-Means when corpus is too small for HDBSCAN.
"""
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def _bertopic_cluster(
    docs: list[str],
    embeddings: np.ndarray,
    min_cluster_size: int,
) -> tuple[list[int], np.ndarray, object]:
    """Run BERTopic. Returns (topics, umap_2d, topic_model)."""
    from bertopic import BERTopic
    from umap import UMAP
    from hdbscan import HDBSCAN

    umap_model = UMAP(
        n_components=2,
        n_neighbors=min(15, max(2, len(docs) - 1)),
        min_dist=0.0,
        random_state=42,
        metric="cosine",
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=min(min_cluster_size, max(2, len(docs) // 2)),
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )
    topic_model = BERTopic(
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        top_n_words=10,
        verbose=False,
        calculate_probabilities=False,
    )
    topics, _ = topic_model.fit_transform(docs, embeddings)
    umap_2d: np.ndarray = umap_model.embedding_  # shape (n, 2)
    return topics, umap_2d, topic_model


def _kmeans_fallback(
    embeddings: np.ndarray,
    n_clusters: int,
) -> tuple[list[int], np.ndarray]:
    """K-Means fallback for very small corpora (<10 papers)."""
    from sklearn.cluster import KMeans

    n_clusters = min(n_clusters, len(embeddings))
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = km.fit_predict(embeddings).tolist()

    if len(embeddings) < 4:
        if len(embeddings) == 1:
            umap_2d = np.zeros((1, 2))
        else:
            from sklearn.decomposition import PCA
            pca = PCA(n_components=2, random_state=42)
            umap_2d = pca.fit_transform(embeddings)
    else:
        from umap import UMAP
        n_neighbors = min(3, max(2, len(embeddings) - 1))
        umap_model = UMAP(n_components=2, n_neighbors=n_neighbors, random_state=42)
        umap_2d = umap_model.fit_transform(embeddings)
        
    return labels, umap_2d


def cluster_papers(
    paper_ids: list[int],
    docs: list[str],           # title + abstract per paper
    embeddings: np.ndarray,
    min_cluster_size: int = 3,
) -> dict:
    """
    Cluster papers and return structured topic data.

    Returns:
    {
      "topic_assignments": {paper_id: topic_id},
      "umap_coords": {paper_id: {"x": float, "y": float}},
      "topics": [
        {
          "topic_id": int,
          "keywords": [str, ...],
          "paper_ids": [int, ...],
          "centroid_embedding": [float, ...],
        }
      ]
    }
    """
    n = len(paper_ids)
    logger.info("Clustering %d papers (min_cluster_size=%d)", n, min_cluster_size)

    topic_labels: Optional[list[int]] = None
    umap_2d: Optional[np.ndarray] = None
    topic_model = None

    if n >= 6:
        try:
            topic_labels, umap_2d, topic_model = _bertopic_cluster(
                docs, embeddings, min_cluster_size
            )
        except Exception as e:
            logger.warning("BERTopic failed, falling back to K-Means: %s", e)

    if topic_labels is None:
        n_clusters = max(2, n // 2)
        topic_labels, umap_2d = _kmeans_fallback(embeddings, n_clusters)

    # Build topic → paper_ids mapping
    topic_to_papers: dict[int, list[int]] = {}
    for pid, tid in zip(paper_ids, topic_labels):
        topic_to_papers.setdefault(tid, []).append(pid)

    # Get keywords per topic
    topics_out = []
    for tid, pids in topic_to_papers.items():
        if topic_model is not None and tid != -1:
            try:
                topic_info = topic_model.get_topic(tid)
                if topic_info:
                    # BERTopic 0.17+ returns a dict/Mapping; older versions return list of tuples
                    if isinstance(topic_info, dict):
                        keywords = list(topic_info.keys())[:10]
                    else:
                        keywords = [word for word, _ in list(topic_info)[:10]]
                else:
                    keywords = []
            except Exception:
                keywords = []
        else:
            keywords = []

        # Fallback keywords from TF across paper docs in this cluster
        if not keywords:
            from sklearn.feature_extraction.text import TfidfVectorizer
            cluster_docs = [docs[paper_ids.index(p)] for p in pids if p in paper_ids]
            if cluster_docs:
                try:
                    tv = TfidfVectorizer(max_features=10, stop_words="english")
                    tv.fit_transform(cluster_docs)
                    keywords = tv.get_feature_names_out().tolist()
                except Exception:
                    keywords = []

        # Compute centroid
        indices = [paper_ids.index(p) for p in pids if p in paper_ids]
        centroid = embeddings[indices].mean(axis=0).tolist() if indices else []

        label = ", ".join(keywords[:5]) if keywords else f"Topic {tid}"
        topics_out.append({
            "topic_id": int(tid),
            "label": label,
            "keywords": keywords,
            "paper_ids": pids,
            "centroid_embedding": centroid,
        })

    # Sort topics by size
    topics_out.sort(key=lambda t: len(t["paper_ids"]), reverse=True)

    # UMAP coordinates per paper
    umap_coords = {}
    for i, pid in enumerate(paper_ids):
        umap_coords[pid] = {
            "x": float(umap_2d[i, 0]),
            "y": float(umap_2d[i, 1]),
        }

    return {
        "topic_assignments": {pid: int(tid) for pid, tid in zip(paper_ids, topic_labels)},
        "umap_coords": umap_coords,
        "topics": topics_out,
    }
