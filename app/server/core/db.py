import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "voxstore.db")

SEED_PRODUCTS = [
    (
        "Wireless Noise-Cancelling Headphones",
        "Premium over-ear headphones with 30-hour battery life and active noise cancellation.",
        149.99,
        "Electronics",
        "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop",
        True,
        4.7,
    ),
    (
        "Mechanical Keyboard",
        "RGB backlit mechanical keyboard with Cherry MX switches and USB-C.",
        89.99,
        "Electronics",
        "https://images.unsplash.com/photo-1526920929362-5b26677c148c?w=400&h=400&fit=crop",
        True,
        4.5,
    ),
    (
        "Portable Bluetooth Speaker",
        "Waterproof speaker with 360-degree sound and 12-hour battery.",
        59.99,
        "Electronics",
        "https://images.unsplash.com/photo-1589273705736-1bd0a0bcf116?w=400&h=400&fit=crop",
        True,
        3.8,
    ),
    (
        "USB-C Hub Adapter",
        "7-in-1 hub with HDMI, USB 3.0, SD card reader and PD charging.",
        34.99,
        "Electronics",
        "https://images.unsplash.com/photo-1616578273518-450dd375759b?w=400&h=400&fit=crop",
        True,
        2.9,
    ),
    (
        "Smart Watch Fitness Tracker",
        "Heart rate monitor, GPS, sleep tracking and 7-day battery.",
        199.99,
        "Electronics",
        "https://images.unsplash.com/photo-1557935728-e6d1eaabe558?w=400&h=400&fit=crop",
        True,
        4.6,
    ),
    (
        "Webcam 1080p HD",
        "Full HD webcam with auto-focus and built-in microphone.",
        49.99,
        "Electronics",
        "https://images.unsplash.com/photo-1564540574859-0dfb63985953?w=400&h=400&fit=crop",
        False,
        3.2,
    ),
    (
        "Cotton Crew Neck T-Shirt",
        "Soft 100% organic cotton tee in classic fit.",
        24.99,
        "Clothing",
        "https://images.unsplash.com/photo-1581655353564-df123a1eb820?w=400&h=400&fit=crop",
        True,
        4.1,
    ),
    (
        "Slim Fit Jeans",
        "Stretch denim jeans with a modern slim fit.",
        54.99,
        "Clothing",
        "https://images.unsplash.com/photo-1605518216938-7c31b7b14ad0?w=400&h=400&fit=crop",
        True,
        2.4,
    ),
    (
        "Lightweight Running Jacket",
        "Breathable windbreaker with reflective details.",
        79.99,
        "Clothing",
        "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=400&h=400&fit=crop",
        True,
        4.5,
    ),
    (
        "Wool Blend Beanie",
        "Warm knitted beanie for cold weather.",
        19.99,
        "Clothing",
        "https://images.unsplash.com/photo-1544967919-44c1ef2f9e7a?w=400&h=400&fit=crop",
        True,
        1.8,
    ),
    (
        "Canvas Sneakers",
        "Classic low-top canvas shoes with rubber sole.",
        44.99,
        "Clothing",
        "https://images.unsplash.com/photo-1526113141918-63428b17f8c2?w=400&h=400&fit=crop",
        True,
        3.5,
    ),
    (
        "Ceramic Pour-Over Coffee Set",
        "Handmade ceramic dripper with thermal carafe.",
        39.99,
        "Home",
        "https://images.unsplash.com/photo-1504469089401-14f795f6ddee?w=400&h=400&fit=crop",
        True,
        4.8,
    ),
    (
        "Bamboo Desk Organizer",
        "Eco-friendly bamboo organizer with 5 compartments.",
        29.99,
        "Home",
        "https://images.unsplash.com/photo-1533090161767-e6ffed986c88?w=400&h=400&fit=crop",
        True,
        3.9,
    ),
    (
        "LED Desk Lamp",
        "Dimmable LED lamp with adjustable color temperature.",
        44.99,
        "Home",
        "https://images.unsplash.com/photo-1562034475-0292da13283a?w=400&h=400&fit=crop",
        True,
        4.2,
    ),
    (
        "Scented Soy Candle Set",
        "Set of 3 hand-poured soy candles in glass jars.",
        27.99,
        "Home",
        "https://images.unsplash.com/photo-1665124197613-ffbb755f4ac2?w=400&h=400&fit=crop",
        True,
        4.7,
    ),
    (
        "Indoor Herb Garden Kit",
        "Self-watering planter with basil, mint, and cilantro seeds.",
        34.99,
        "Home",
        "https://images.unsplash.com/photo-1615224571885-7802e8b86d1b?w=400&h=400&fit=crop",
        True,
        2.1,
    ),
    (
        "Cast Iron Skillet 12-inch",
        "Pre-seasoned cast iron pan for stovetop and oven.",
        42.99,
        "Home",
        "https://images.unsplash.com/photo-1565636290659-d5b15f864f64?w=400&h=400&fit=crop",
        True,
        4.9,
    ),
    (
        "The Pragmatic Programmer",
        "Classic software development book, 20th Anniversary Edition.",
        39.99,
        "Books",
        "https://images.unsplash.com/photo-1499447155021-4907f71b9ef5?w=400&h=400&fit=crop",
        True,
        4.8,
    ),
    (
        "Atomic Habits",
        "Proven framework for building good habits and breaking bad ones.",
        16.99,
        "Books",
        "https://images.unsplash.com/photo-1711843250811-a7d0bb485a42?w=400&h=400&fit=crop",
        True,
        4.9,
    ),
    (
        "Designing Data-Intensive Applications",
        "Deep dive into distributed systems and data architecture.",
        44.99,
        "Books",
        "https://images.unsplash.com/photo-1732714403349-05fc43b67042?w=400&h=400&fit=crop",
        True,
        4.8,
    ),
    (
        "The Art of War",
        "Ancient classic on strategy, newly translated.",
        9.99,
        "Books",
        "https://images.unsplash.com/photo-1698954634383-eba274a1b1c7?w=400&h=400&fit=crop",
        True,
        3.1,
    ),
    (
        "Yoga Mat Premium",
        "Non-slip 6mm thick mat with carrying strap.",
        34.99,
        "Sports",
        "https://images.unsplash.com/photo-1633707236776-1188a396f223?w=400&h=400&fit=crop",
        True,
        4.6,
    ),
    (
        "Resistance Bands Set",
        "5-piece set with varying resistance levels and carrying bag.",
        24.99,
        "Sports",
        "https://images.unsplash.com/photo-1595909315417-2edd382a56dc?w=400&h=400&fit=crop",
        True,
        3.6,
    ),
    (
        "Stainless Steel Water Bottle",
        "Insulated 32oz bottle keeps drinks cold 24 hours.",
        29.99,
        "Sports",
        "https://images.unsplash.com/photo-1649867219867-3faeab653df9?w=400&h=400&fit=crop",
        True,
        4.7,
    ),
    (
        "Jump Rope Speed Cable",
        "Adjustable steel cable jump rope with ball bearings.",
        14.99,
        "Sports",
        "https://images.unsplash.com/photo-1514994667787-b48ca37155f0?w=400&h=400&fit=crop",
        True,
        1.5,
    ),
    (
        "Foam Roller Recovery",
        "High-density EVA foam roller for muscle recovery.",
        22.99,
        "Sports",
        "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=400&h=400&fit=crop",
        True,
        3.3,
    ),
    # ── Additional Electronics ──
    (
        "Budget Wired Headphones",
        "Lightweight on-ear headphones with inline mic and tangle-free cable.",
        19.99,
        "Electronics",
        "https://images.unsplash.com/photo-1558756520-22cfe5d382ca?w=400&h=400&fit=crop",
        True,
        2.3,
    ),
    (
        "Studio Monitor Headphones",
        "Professional open-back headphones for mixing and mastering.",
        249.99,
        "Electronics",
        "https://images.unsplash.com/photo-1524678606370-a47ad25cb82a?w=400&h=400&fit=crop",
        True,
        4.9,
    ),
    (
        "Compact Wireless Keyboard",
        "Slim Bluetooth keyboard with rechargeable battery and multi-device pairing.",
        49.99,
        "Electronics",
        "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=400&h=400&fit=crop",
        True,
        3.4,
    ),
    (
        "Ergonomic Split Keyboard",
        "Curved split-layout keyboard with wrist rest and programmable keys.",
        159.99,
        "Electronics",
        "https://images.unsplash.com/photo-1595225476474-87563907a212?w=400&h=400&fit=crop",
        True,
        4.3,
    ),
    (
        "Mini Bluetooth Speaker",
        "Pocket-sized speaker with carabiner clip and 8-hour battery.",
        24.99,
        "Electronics",
        "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400&h=400&fit=crop",
        True,
        2.7,
    ),
    (
        "Premium Bookshelf Speakers",
        "Pair of powered bookshelf speakers with Bluetooth 5.0 and wood finish.",
        179.99,
        "Electronics",
        "https://images.unsplash.com/photo-1545454675-3531b543be5d?w=400&h=400&fit=crop",
        True,
        4.8,
    ),
    (
        "Wireless Earbuds",
        "True wireless earbuds with active noise cancellation and 6-hour battery.",
        79.99,
        "Electronics",
        "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop",
        True,
        4.1,
    ),
    # ── Additional Clothing ──
    (
        "Merino Wool T-Shirt",
        "Odor-resistant merino wool tee for travel and outdoor activities.",
        69.99,
        "Clothing",
        "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=400&fit=crop",
        True,
        4.6,
    ),
    (
        "Graphic Print T-Shirt",
        "Bold graphic tee made from soft ring-spun cotton.",
        14.99,
        "Clothing",
        "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=400&h=400&fit=crop",
        True,
        3.2,
    ),
    (
        "Relaxed Fit Jeans",
        "Comfortable straight-leg jeans with classic five-pocket design.",
        39.99,
        "Clothing",
        "https://images.unsplash.com/photo-1542272604-787c3835535d?w=400&h=400&fit=crop",
        True,
        4.0,
    ),
    (
        "Premium Selvedge Jeans",
        "Japanese selvedge denim with raw indigo finish.",
        129.99,
        "Clothing",
        "https://images.unsplash.com/photo-1604176354204-9268737828e4?w=400&h=400&fit=crop",
        True,
        4.8,
    ),
    (
        "Waterproof Running Jacket",
        "Fully seam-sealed jacket with packable hood and ventilation zips.",
        149.99,
        "Clothing",
        "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=400&h=400&fit=crop",
        True,
        4.7,
    ),
    (
        "Leather High-Top Sneakers",
        "Premium leather sneakers with padded collar and cushioned insole.",
        89.99,
        "Clothing",
        "https://images.unsplash.com/photo-1520256862855-398228c41684?w=400&h=400&fit=crop",
        True,
        4.3,
    ),
    (
        "Budget Running Shoes",
        "Lightweight mesh running shoes with EVA foam midsole.",
        34.99,
        "Clothing",
        "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop",
        True,
        2.8,
    ),
    # ── Additional Home ──
    (
        "French Press Coffee Maker",
        "Borosilicate glass French press with stainless steel plunger.",
        24.99,
        "Home",
        "https://images.unsplash.com/photo-1572119865084-43c285814d63?w=400&h=400&fit=crop",
        True,
        4.4,
    ),
    (
        "Espresso Machine",
        "15-bar pump espresso machine with built-in milk frother.",
        189.99,
        "Home",
        "https://images.unsplash.com/photo-1610889556528-9a770e32642f?w=400&h=400&fit=crop",
        True,
        4.6,
    ),
    (
        "Clip-On Desk Lamp",
        "Flexible gooseneck LED lamp with USB charging and clamp mount.",
        18.99,
        "Home",
        "https://images.unsplash.com/photo-1513506003901-1e6a229e2d15?w=400&h=400&fit=crop",
        True,
        3.1,
    ),
    (
        "Smart Floor Lamp",
        "WiFi-connected RGB floor lamp with voice assistant compatibility.",
        89.99,
        "Home",
        "https://images.unsplash.com/photo-1543198126-a8c6889a9848?w=400&h=400&fit=crop",
        True,
        4.5,
    ),
    (
        "Vanilla Beeswax Candle",
        "Hand-rolled beeswax candle with natural vanilla scent.",
        12.99,
        "Home",
        "https://images.unsplash.com/photo-1602874801006-e26c052a64e3?w=400&h=400&fit=crop",
        True,
        2.6,
    ),
    (
        "Stainless Steel Skillet 10-inch",
        "Tri-ply stainless steel pan with stay-cool handle.",
        64.99,
        "Home",
        "https://images.unsplash.com/photo-1556909172-54557c7e4fb7?w=400&h=400&fit=crop",
        True,
        3.7,
    ),
    (
        "Non-Stick Skillet 8-inch",
        "Ceramic non-stick pan with silicone grip handle.",
        22.99,
        "Home",
        "https://images.unsplash.com/photo-1574739782594-db4ead022697?w=400&h=400&fit=crop",
        True,
        2.2,
    ),
    # ── Additional Books ──
    (
        "Clean Code",
        "A handbook of agile software craftsmanship by Robert C. Martin.",
        34.99,
        "Books",
        "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=400&h=400&fit=crop",
        True,
        4.5,
    ),
    (
        "JavaScript: The Good Parts",
        "Concise guide to the best features of JavaScript.",
        19.99,
        "Books",
        "https://images.unsplash.com/photo-1579468118864-1b9ea3c0db4a?w=400&h=400&fit=crop",
        True,
        3.8,
    ),
    (
        "Deep Work",
        "Rules for focused success in a distracted world by Cal Newport.",
        14.99,
        "Books",
        "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400&h=400&fit=crop",
        True,
        4.7,
    ),
    (
        "The Mythical Man-Month",
        "Classic essays on software engineering and project management.",
        29.99,
        "Books",
        "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=400&h=400&fit=crop",
        True,
        4.2,
    ),
    (
        "Cracking the Coding Interview",
        "189 programming questions and solutions for tech interviews.",
        26.99,
        "Books",
        "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400&h=400&fit=crop",
        True,
        4.4,
    ),
    (
        "The Phoenix Project",
        "A novel about IT, DevOps, and helping your business win.",
        12.99,
        "Books",
        "https://images.unsplash.com/photo-1589998059171-988d887df646?w=400&h=400&fit=crop",
        True,
        3.5,
    ),
    (
        "Introduction to Algorithms",
        "Comprehensive textbook covering a broad range of algorithms.",
        79.99,
        "Books",
        "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=400&h=400&fit=crop",
        True,
        4.1,
    ),
    # ── Additional Sports ──
    (
        "Collapsible Water Bottle",
        "Silicone foldable bottle with carabiner, BPA-free, 20oz.",
        12.99,
        "Sports",
        "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=400&h=400&fit=crop",
        True,
        2.4,
    ),
    (
        "Glass Water Bottle with Sleeve",
        "Borosilicate glass bottle with protective silicone sleeve, 24oz.",
        22.99,
        "Sports",
        "https://images.unsplash.com/photo-1523362628745-0c100150b504?w=400&h=400&fit=crop",
        True,
        3.9,
    ),
    (
        "Premium Insulated Water Bottle",
        "Vacuum-insulated 40oz bottle with wide mouth and straw lid.",
        44.99,
        "Sports",
        "https://images.unsplash.com/photo-1570831739435-6601aa3fa4fb?w=400&h=400&fit=crop",
        True,
        4.8,
    ),
    (
        "Travel Yoga Mat",
        "Ultra-thin 2mm foldable mat that fits in a carry-on.",
        24.99,
        "Sports",
        "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=400&h=400&fit=crop",
        True,
        3.2,
    ),
    (
        "Extra Thick Yoga Mat",
        "12mm cushioned mat with alignment markers and carrying strap.",
        54.99,
        "Sports",
        "https://images.unsplash.com/photo-1518611012118-696072aa579a?w=400&h=400&fit=crop",
        True,
        4.5,
    ),
    (
        "Adjustable Dumbbell Set",
        "Pair of adjustable dumbbells from 5 to 25 lbs each with quick-lock.",
        149.99,
        "Sports",
        "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=400&h=400&fit=crop",
        True,
        4.4,
    ),
    (
        "Speed Jump Rope Pro",
        "Weighted handles with bearing system and adjustable steel cable.",
        29.99,
        "Sports",
        "https://images.unsplash.com/photo-1434596922112-19c563067271?w=400&h=400&fit=crop",
        True,
        4.1,
    ),
]


_db_initialized = False


def get_connection() -> sqlite3.Connection:
    global _db_initialized
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if not _db_initialized:
        _ensure_tables(conn)
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
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

    conn.commit()


def init_db():
    global _db_initialized
    conn = get_connection()
    _ensure_tables(conn)

    cursor = conn.cursor()

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
    _db_initialized = True
