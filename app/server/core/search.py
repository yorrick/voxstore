from .db import get_connection


def search_products(query: str) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    pattern = f"%{query}%"
    cursor.execute(
        "SELECT * FROM products WHERE name LIKE ? OR description LIKE ? OR category LIKE ?",
        (pattern, pattern, pattern),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
