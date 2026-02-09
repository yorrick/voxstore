import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "voxstore.db")

SEED_PRODUCTS = [
    (
        "Wireless Noise-Cancelling Headphones",
        "Premium over-ear headphones with 30-hour battery life and active noise cancellation.",
        149.99,
        "Electronics",
        "https://picsum.photos/seed/headphones/400/400",
        True,
        4.7,
    ),
    (
        "Mechanical Keyboard",
        "RGB backlit mechanical keyboard with Cherry MX switches and USB-C.",
        89.99,
        "Electronics",
        "https://picsum.photos/seed/keyboard/400/400",
        True,
        4.5,
    ),
    (
        "Portable Bluetooth Speaker",
        "Waterproof speaker with 360-degree sound and 12-hour battery.",
        59.99,
        "Electronics",
        "https://picsum.photos/seed/speaker/400/400",
        True,
        4.3,
    ),
    (
        "USB-C Hub Adapter",
        "7-in-1 hub with HDMI, USB 3.0, SD card reader and PD charging.",
        34.99,
        "Electronics",
        "https://picsum.photos/seed/usbhub/400/400",
        True,
        4.1,
    ),
    (
        "Smart Watch Fitness Tracker",
        "Heart rate monitor, GPS, sleep tracking and 7-day battery.",
        199.99,
        "Electronics",
        "https://picsum.photos/seed/smartwatch/400/400",
        True,
        4.6,
    ),
    (
        "Webcam 1080p HD",
        "Full HD webcam with auto-focus and built-in microphone.",
        49.99,
        "Electronics",
        "https://picsum.photos/seed/webcam/400/400",
        False,
        4.2,
    ),
    (
        "Cotton Crew Neck T-Shirt",
        "Soft 100% organic cotton tee in classic fit.",
        24.99,
        "Clothing",
        "https://picsum.photos/seed/tshirt/400/400",
        True,
        4.4,
    ),
    (
        "Slim Fit Jeans",
        "Stretch denim jeans with a modern slim fit.",
        54.99,
        "Clothing",
        "https://picsum.photos/seed/jeans/400/400",
        True,
        4.3,
    ),
    (
        "Lightweight Running Jacket",
        "Breathable windbreaker with reflective details.",
        79.99,
        "Clothing",
        "https://picsum.photos/seed/jacket/400/400",
        True,
        4.5,
    ),
    (
        "Wool Blend Beanie",
        "Warm knitted beanie for cold weather.",
        19.99,
        "Clothing",
        "https://picsum.photos/seed/beanie/400/400",
        True,
        4.6,
    ),
    (
        "Canvas Sneakers",
        "Classic low-top canvas shoes with rubber sole.",
        44.99,
        "Clothing",
        "https://picsum.photos/seed/sneakers/400/400",
        True,
        4.2,
    ),
    (
        "Ceramic Pour-Over Coffee Set",
        "Handmade ceramic dripper with thermal carafe.",
        39.99,
        "Home",
        "https://picsum.photos/seed/coffee/400/400",
        True,
        4.8,
    ),
    (
        "Bamboo Desk Organizer",
        "Eco-friendly bamboo organizer with 5 compartments.",
        29.99,
        "Home",
        "https://picsum.photos/seed/organizer/400/400",
        True,
        4.4,
    ),
    (
        "LED Desk Lamp",
        "Dimmable LED lamp with adjustable color temperature.",
        44.99,
        "Home",
        "https://picsum.photos/seed/lamp/400/400",
        True,
        4.5,
    ),
    (
        "Scented Soy Candle Set",
        "Set of 3 hand-poured soy candles in glass jars.",
        27.99,
        "Home",
        "https://picsum.photos/seed/candles/400/400",
        True,
        4.7,
    ),
    (
        "Indoor Herb Garden Kit",
        "Self-watering planter with basil, mint, and cilantro seeds.",
        34.99,
        "Home",
        "https://picsum.photos/seed/herbs/400/400",
        True,
        4.3,
    ),
    (
        "Cast Iron Skillet 12-inch",
        "Pre-seasoned cast iron pan for stovetop and oven.",
        42.99,
        "Home",
        "https://picsum.photos/seed/skillet/400/400",
        True,
        4.9,
    ),
    (
        "The Pragmatic Programmer",
        "Classic software development book, 20th Anniversary Edition.",
        39.99,
        "Books",
        "https://picsum.photos/seed/pragprog/400/400",
        True,
        4.8,
    ),
    (
        "Atomic Habits",
        "Proven framework for building good habits and breaking bad ones.",
        16.99,
        "Books",
        "https://picsum.photos/seed/atomichabits/400/400",
        True,
        4.9,
    ),
    (
        "Designing Data-Intensive Applications",
        "Deep dive into distributed systems and data architecture.",
        44.99,
        "Books",
        "https://picsum.photos/seed/ddia/400/400",
        True,
        4.8,
    ),
    (
        "The Art of War",
        "Ancient classic on strategy, newly translated.",
        9.99,
        "Books",
        "https://picsum.photos/seed/artofwar/400/400",
        True,
        4.5,
    ),
    (
        "Yoga Mat Premium",
        "Non-slip 6mm thick mat with carrying strap.",
        34.99,
        "Sports",
        "https://picsum.photos/seed/yogamat/400/400",
        True,
        4.6,
    ),
    (
        "Resistance Bands Set",
        "5-piece set with varying resistance levels and carrying bag.",
        24.99,
        "Sports",
        "https://picsum.photos/seed/bands/400/400",
        True,
        4.4,
    ),
    (
        "Stainless Steel Water Bottle",
        "Insulated 32oz bottle keeps drinks cold 24 hours.",
        29.99,
        "Sports",
        "https://picsum.photos/seed/bottle/400/400",
        True,
        4.7,
    ),
    (
        "Jump Rope Speed Cable",
        "Adjustable steel cable jump rope with ball bearings.",
        14.99,
        "Sports",
        "https://picsum.photos/seed/jumprope/400/400",
        True,
        4.3,
    ),
    (
        "Foam Roller Recovery",
        "High-density EVA foam roller for muscle recovery.",
        22.99,
        "Sports",
        "https://picsum.photos/seed/foamroller/400/400",
        True,
        4.5,
    ),
]


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            image_url TEXT NOT NULL,
            in_stock BOOLEAN DEFAULT 1,
            rating REAL DEFAULT 0.0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # Seed products if table is empty
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO products (name, description, price, category, image_url, in_stock, rating)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            SEED_PRODUCTS,
        )

    conn.commit()
    conn.close()
