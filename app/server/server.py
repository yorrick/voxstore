import logging
import os
import sys
from datetime import datetime

import sentry_sdk
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.db import get_connection, init_db
from core.embeddings import init_embeddings
from core.llm_extraction import LLMExtractionError, extract_voice_search
from core.models import (
    AddToCartRequest,
    CartItem,
    HealthCheckResponse,
    Product,
    SearchResponse,
    TranscribeResponse,
    VoiceExtractRequest,
    VoiceSearchExtraction,
    WebSocketTokenResponse,
)
from core.search import search_products
from core.transcribe import TranscriptionError, get_websocket_token, transcribe_audio

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Initialize Sentry
sentry_dsn = os.environ.get("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
        send_default_pii=True,
    )
    logger.info("[SENTRY] Initialized with DSN")
else:
    logger.info("[SENTRY] No DSN configured, error tracking disabled")

app = FastAPI(
    title="VoxStore API",
    description="Voice-powered product catalog backend",
    version="1.0.0",
)

# CORS
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "")
allowed_origins: list[str] = []
if allowed_origins_env:
    allowed_origins.extend([o.strip() for o in allowed_origins_env.split(",") if o.strip()])
if not os.environ.get("RENDER"):
    frontend_port = os.environ.get("FRONTEND_PORT", "5173")
    allowed_origins.extend([f"http://localhost:{frontend_port}", "http://localhost:8000"])
logger.info("[CORS] Allowed origins: %s", allowed_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app_start_time = datetime.now()

# Initialize database on startup
init_db()
logger.info("[STARTUP] Database initialized with seed data")

# Initialize semantic search embeddings
try:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    all_products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    init_embeddings(all_products)
except Exception as e:
    logger.warning("[STARTUP] Failed to initialize embeddings: %s", e)


# --- Product endpoints ---


@app.get("/api/products", response_model=list[Product])
async def list_products(
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort: str | None = None,
    min_rating: float | None = None,
):
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM products WHERE 1=1"
    params: list = []

    if category:
        query += " AND category = ?"
        params.append(category)
    if min_price is not None:
        query += " AND price >= ?"
        params.append(min_price)
    if max_price is not None:
        query += " AND price <= ?"
        params.append(max_price)
    if min_rating is not None:
        query += " AND rating >= ?"
        params.append(min_rating)

    if sort == "price_asc":
        query += " ORDER BY price ASC"
    elif sort == "price_desc":
        query += " ORDER BY price DESC"
    elif sort == "rating":
        query += " ORDER BY rating DESC"
    else:
        query += " ORDER BY id ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/products/{product_id}", response_model=Product)
async def get_product(product_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Product not found")
    return dict(row)


@app.get("/api/search", response_model=SearchResponse)
async def search(q: str = ""):
    if not q.strip():
        return SearchResponse(products=[], total=0, query=q)
    results = search_products(q)
    return SearchResponse(products=[Product(**r) for r in results], total=len(results), query=q)


@app.get("/api/categories")
async def list_categories():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM products ORDER BY category")
    rows = cursor.fetchall()
    conn.close()
    return [row["category"] for row in rows]


# --- Transcription endpoint ---


@app.post("/api/transcribe", response_model=TranscribeResponse)
async def transcribe_endpoint(file: UploadFile = File(...)):
    """Transcribe audio using ElevenLabs Scribe v2."""
    if not file.content_type or not file.content_type.startswith("audio/"):
        return TranscribeResponse(text="", success=False, error="Invalid file type. Must be audio.")

    try:
        audio_data = await file.read()
        if len(audio_data) == 0:
            return TranscribeResponse(text="", success=False, error="Empty audio file")

        text = await transcribe_audio(audio_data, file.content_type)
        return TranscribeResponse(text=text, success=True)
    except TranscriptionError as e:
        logger.warning("[TRANSCRIBE] %s", e)
        return TranscribeResponse(text="", success=False, error=str(e))


@app.post("/api/transcribe/token", response_model=WebSocketTokenResponse)
async def transcribe_token_endpoint():
    """Get a single-use WebSocket token for realtime transcription."""
    try:
        result = await get_websocket_token()
        return result
    except TranscriptionError as e:
        logger.warning("[TRANSCRIBE TOKEN] %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


# --- Voice extraction endpoint ---


@app.post("/api/voice/extract", response_model=VoiceSearchExtraction)
async def extract_voice_endpoint(request: VoiceExtractRequest):
    """Extract structured search parameters from a voice transcript using LLM."""
    if not request.transcript.strip():
        raise HTTPException(400, "Transcript is required")
    try:
        result = await extract_voice_search(request.transcript)
        return result
    except LLMExtractionError as e:
        logger.warning("[VOICE_EXTRACT] %s", e)
        return VoiceSearchExtraction(query=request.transcript)


# --- Cart endpoints ---


@app.get("/api/cart", response_model=list[CartItem])
async def get_cart():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cart")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/api/cart", response_model=CartItem)
async def add_to_cart(request: AddToCartRequest):
    conn = get_connection()
    cursor = conn.cursor()

    # Check product exists
    cursor.execute("SELECT id FROM products WHERE id = ?", (request.product_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(404, "Product not found")

    # Check if product already in cart
    cursor.execute("SELECT id, quantity FROM cart WHERE product_id = ?", (request.product_id,))
    existing = cursor.fetchone()

    if existing:
        new_qty = existing["quantity"] + request.quantity
        cursor.execute("UPDATE cart SET quantity = ? WHERE id = ?", (new_qty, existing["id"]))
        conn.commit()
        cart_id = existing["id"]
        quantity = new_qty
    else:
        cursor.execute(
            "INSERT INTO cart (product_id, quantity) VALUES (?, ?)",
            (request.product_id, request.quantity),
        )
        conn.commit()
        cart_id = cursor.lastrowid or 0
        quantity = request.quantity

    conn.close()
    return CartItem(id=cart_id, product_id=request.product_id, quantity=quantity)


@app.delete("/api/cart/{item_id}")
async def remove_from_cart(item_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE id = ?", (item_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(404, "Cart item not found")
    conn.commit()
    conn.close()
    return {"message": "Item removed from cart"}


# --- Config ---


@app.get("/api/config")
async def get_config():
    """Return public client configuration (e.g. Sentry DSN)."""
    return {"sentry_dsn": os.environ.get("SENTRY_DSN", "")}


# --- Health ---


@app.get("/api/health", response_model=HealthCheckResponse)
async def health_check():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM products")
    count = cursor.fetchone()["count"]
    conn.close()
    uptime = (datetime.now() - app_start_time).total_seconds()
    return HealthCheckResponse(status="ok", products_count=count, uptime_seconds=uptime)


@app.get("/sentry-debug")
async def trigger_error():
    """Trigger a test error to verify Sentry is working."""
    _ = 1 / 0


# --- Serve static frontend ---

CLIENT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client")

if os.path.isdir(CLIENT_DIR):

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(CLIENT_DIR, "index.html"))

    app.mount("/", StaticFiles(directory=CLIENT_DIR), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=int(os.environ.get("BACKEND_PORT", "8000")),
        reload=True,
    )
