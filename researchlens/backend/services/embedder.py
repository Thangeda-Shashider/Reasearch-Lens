"""
SPECTER2 embedding service.
Generates 768-dim paper embeddings from title + abstract.
Caches in Redis (if available) or falls back to an in-memory dict.
Computes corpus centroid for semantic novelty scoring.
"""
import json
import logging
import hashlib
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# In-memory cache fallback when Redis is unavailable
_mem_cache: dict[str, list[float]] = {}
_model = None  # Lazy-loaded sentence-transformer model
_redis_client = None
_redis_tried = False


def _get_redis(redis_url: str):
    global _redis_client, _redis_tried
    if _redis_tried:
        return _redis_client
    _redis_tried = True
    if not redis_url:
        return None
    try:
        import redis as redis_lib
        client = redis_lib.Redis.from_url(redis_url, decode_responses=True)
        client.ping()
        _redis_client = client
        logger.info("Redis connected: %s", redis_url)
    except Exception as e:
        logger.warning("Redis unavailable, using memory cache: %s", e)
    return _redis_client


def _get_model(model_name: str):
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s (first run may download weights)", model_name)
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(model_name)
    return _model


def _cache_key(text: str) -> str:
    return "emb:" + hashlib.md5(text.encode()).hexdigest()


def _cache_get(key: str, redis) -> Optional[list[float]]:
    if redis:
        val = redis.get(key)
        if val:
            return json.loads(val)
    return _mem_cache.get(key)


def _cache_set(key: str, embedding: list[float], redis) -> None:
    if redis:
        redis.set(key, json.dumps(embedding), ex=86400 * 7)
    else:
        _mem_cache[key] = embedding


def embed_paper(
    title: str,
    abstract: str,
    model_name: str = "allenai/specter2_base",
    redis_url: str = "",
) -> np.ndarray:
    """
    Generate a single 768-dim embedding for a paper.
    Input format follows SPECTER2 convention: "title [SEP] abstract"
    """
    text = f"{title} [SEP] {abstract}"
    key = _cache_key(text)
    redis = _get_redis(redis_url)

    cached = _cache_get(key, redis)
    if cached is not None:
        return np.array(cached, dtype=np.float32)

    model = _get_model(model_name)
    embedding = model.encode(text, normalize_embeddings=True)
    _cache_set(key, embedding.tolist(), redis)
    return embedding.astype(np.float32)


def embed_batch(
    papers: list[dict],
    model_name: str = "allenai/specter2_base",
    redis_url: str = "",
) -> np.ndarray:
    """
    Embed a list of {title, abstract} dicts.
    Returns ndarray of shape (n_papers, 768).
    Uses cache per paper; only encodes uncached papers in a single batch call.
    """
    redis = _get_redis(redis_url)
    texts: list[str] = []
    keys: list[str] = []
    embeddings: dict[str, np.ndarray] = {}

    for p in papers:
        text = f"{p.get('title', '')} [SEP] {p.get('abstract', '')}"
        key = _cache_key(text)
        keys.append(key)
        cached = _cache_get(key, redis)
        if cached is not None:
            embeddings[key] = np.array(cached, dtype=np.float32)
        else:
            texts.append(text)

    if texts:
        model = _get_model(model_name)
        batch_embs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        # Pair each new embedding back with its key
        uncached_keys = [k for k in keys if k not in embeddings]
        for k, emb in zip(uncached_keys, batch_embs):
            _cache_set(k, emb.tolist(), redis)
            embeddings[k] = emb.astype(np.float32)

    return np.stack([embeddings[k] for k in keys])


def compute_corpus_centroid(embeddings: np.ndarray) -> np.ndarray:
    """Mean of all paper embeddings, L2-normalised."""
    centroid = embeddings.mean(axis=0)
    norm = np.linalg.norm(centroid)
    return (centroid / norm) if norm > 0 else centroid
