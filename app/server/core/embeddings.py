import logging
import os

import numpy as np
from openai import OpenAI

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "baai/bge-large-en-v1.5"

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


def init_embeddings(products: list[dict]) -> None:
    """Embed all products at startup and cache in memory."""
    if not products:
        logger.warning("[EMBEDDINGS] No products to embed")
        return

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.warning("[EMBEDDINGS] OPENROUTER_API_KEY not set, semantic search disabled")
        return

    client = _get_client()
    texts = [f"{p['name']} {p['description']} {p['category']}" for p in products]

    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)

    for i, product in enumerate(products):
        vec = np.array(response.data[i].embedding, dtype=np.float32)
        _product_embeddings[product["id"]] = _normalize(vec)

    logger.info("[EMBEDDINGS] Cached embeddings for %d products", len(_product_embeddings))


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
