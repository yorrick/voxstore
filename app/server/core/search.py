import logging

from .db import get_connection
from .embeddings import is_available, semantic_search

logger = logging.getLogger(__name__)


def search_products(query: str) -> list[dict]:
    """Search products using semantic vector search."""
    if not is_available():
        logger.warning("[SEARCH] Embeddings not available, returning empty results")
        return []

    matches = semantic_search(query)
    if not matches:
        return []

    conn = get_connection()
    try:
        cursor = conn.cursor()
        ids = [product_id for product_id, _ in matches]
        placeholders = ",".join("?" * len(ids))
        cursor.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", ids)
        rows = cursor.fetchall()
    finally:
        conn.close()

    # Build a map for ordering by score
    row_map = {row["id"]: dict(row) for row in rows}
    results = [row_map[pid] for pid, _ in matches if pid in row_map]

    # Log top result for search quality monitoring
    if results:
        top = results[0]
        logger.info("[SEARCH] query=%r top=%s score=%.3f", query, top["name"], top["score"])

    return results
