import hashlib
import logging
import os

import numpy as np
from openai import OpenAI

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "baai/bge-large-en-v1.5"
_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db")

# In-memory cache: product_id -> normalized embedding vector
_product_embeddings: dict[int, np.ndarray] = {}
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY environment variable is not set")
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
    return _client


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def _cache_key(texts: list[str]) -> str:
    """Compute a hash over product texts + model name to invalidate on change."""
    h = hashlib.sha256()
    h.update(EMBEDDING_MODEL.encode())
    for t in texts:
        h.update(t.encode())
    return h.hexdigest()[:16]


def _cache_path(key: str) -> str:
    return os.path.join(_CACHE_DIR, f"embeddings_{key}.npz")


def _load_cache(products: list[dict], texts: list[str]) -> bool:
    """Try to load embeddings from disk cache. Returns True if successful."""
    key = _cache_key(texts)
    path = _cache_path(key)
    if not os.path.exists(path):
        return False
    try:
        data = np.load(path)
        ids = data["ids"]
        vecs = data["vecs"]
        for i, product_id in enumerate(ids):
            _product_embeddings[int(product_id)] = vecs[i]
        logger.info("[EMBEDDINGS] Loaded %d embeddings from disk cache", len(ids))
        return True
    except Exception as e:
        logger.warning("[EMBEDDINGS] Failed to load cache: %s", e)
        return False


def _save_cache(texts: list[str]) -> None:
    """Persist current in-memory embeddings to disk."""
    key = _cache_key(texts)
    path = _cache_path(key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ids = np.array(list(_product_embeddings.keys()), dtype=np.int64)
    vecs = np.stack(list(_product_embeddings.values()))
    np.savez(path, ids=ids, vecs=vecs)
    logger.info("[EMBEDDINGS] Saved cache to %s", os.path.basename(path))


def init_embeddings(products: list[dict]) -> None:
    """Embed all products at startup, using disk cache when available."""
    if not products:
        logger.warning("[EMBEDDINGS] No products to embed")
        return

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.warning("[EMBEDDINGS] OPENROUTER_API_KEY not set, semantic search disabled")
        return

    texts = [f"{p['name']} {p['description']} {p['category']}" for p in products]

    if _load_cache(products, texts):
        return

    client = _get_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)

    for i, product in enumerate(products):
        vec = np.array(response.data[i].embedding, dtype=np.float32)
        _product_embeddings[product["id"]] = _normalize(vec)

    logger.info("[EMBEDDINGS] Computed embeddings for %d products", len(_product_embeddings))
    _save_cache(texts)


def embed_query(query: str) -> np.ndarray:
    """Embed a search query."""
    client = _get_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=query)
    vec = np.array(response.data[0].embedding, dtype=np.float32)
    return _normalize(vec)


def semantic_search(query: str, threshold: float = 0.55) -> list[tuple[int, float]]:
    """Return product IDs with similarity scores above threshold, sorted by score."""
    if not _product_embeddings:
        return []

    query_vec = embed_query(query)

    results: list[tuple[int, float]] = []
    for product_id, product_vec in _product_embeddings.items():
        score = float(np.dot(query_vec, product_vec))
        if score >= threshold:
            results.append((product_id, score))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def is_available() -> bool:
    """Check if semantic search is available (embeddings loaded)."""
    return len(_product_embeddings) > 0


def clear_cache() -> None:
    """Clear cached embeddings and client. Used for testing."""
    global _client
    _product_embeddings.clear()
    _client = None
