// VoxStore - Voice-Powered Product Catalog

const API_BASE = "/api";

// State
let products = [];
let cart = [];
let productsMap = {};

// DOM elements
const productsGrid = document.getElementById("products-grid");
const searchInput = document.getElementById("search-input");
const voiceBtn = document.getElementById("voice-btn");
const voiceIndicator = document.getElementById("voice-indicator");
const cartBtn = document.getElementById("cart-btn");
const cartPanel = document.getElementById("cart-panel");
const cartOverlay = document.getElementById("cart-overlay");
const closeCartBtn = document.getElementById("close-cart");
const cartItemsEl = document.getElementById("cart-items");
const cartCountEl = document.getElementById("cart-count");
const cartTotalEl = document.getElementById("cart-total");
const categoryFilter = document.getElementById("category-filter");
const sortFilter = document.getElementById("sort-filter");

// --- API calls ---

async function fetchProducts(params = {}) {
    const url = new URL(API_BASE + "/products", window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
        if (v) url.searchParams.set(k, v);
    });
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch products");
    return res.json();
}

async function searchProducts(query) {
    const res = await fetch(API_BASE + "/search?q=" + encodeURIComponent(query));
    if (!res.ok) throw new Error("Failed to search products");
    const data = await res.json();
    return data.products;
}

async function fetchCategories() {
    const res = await fetch(API_BASE + "/categories");
    if (!res.ok) throw new Error("Failed to fetch categories");
    return res.json();
}

async function fetchCart() {
    const res = await fetch(API_BASE + "/cart");
    if (!res.ok) throw new Error("Failed to fetch cart");
    return res.json();
}

async function addToCartAPI(productId) {
    const res = await fetch(API_BASE + "/cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId, quantity: 1 }),
    });
    if (!res.ok) throw new Error("Failed to add to cart");
    return res.json();
}

async function removeFromCartAPI(itemId) {
    var res = await fetch(API_BASE + "/cart/" + itemId, {
        method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to remove from cart");
}

// --- Rendering ---

function renderProducts(items) {
    productsGrid.innerHTML = "";

    if (items.length === 0) {
        productsGrid.innerHTML =
            '<p style="grid-column:1/-1;text-align:center;color:#888;padding:40px;">No products found</p>';
        return;
    }

    items.forEach(function (product) {
        var card = document.createElement("div");
        card.className = "product-card";
        card.setAttribute("data-testid", "product-card");

        var stockHTML = product.in_stock ? "" : '<span class="out-of-stock">Out of Stock</span>';

        var stars = "";
        for (var i = 0; i < 5; i++) {
            stars += i < Math.round(product.rating) ? "★" : "☆";
        }

        card.innerHTML =
            '<img src="' +
            product.image_url +
            '" alt="' +
            product.name +
            '" loading="lazy">' +
            '<div class="product-info">' +
            '<span class="product-category">' +
            product.category +
            "</span>" +
            '<h3 class="product-name">' +
            product.name +
            "</h3>" +
            '<p class="product-description">' +
            product.description +
            "</p>" +
            '<div class="product-footer">' +
            '<span class="product-price">$' +
            product.price.toFixed(2) +
            "</span>" +
            '<span class="product-rating">' +
            stars +
            " " +
            product.rating +
            "</span>" +
            stockHTML +
            "</div>" +
            '<button class="add-to-cart-btn" data-testid="add-to-cart-btn" data-id="' +
            product.id +
            '"' +
            (product.in_stock ? "" : " disabled") +
            ">" +
            (product.in_stock ? "Add to Cart" : "Unavailable") +
            "</button>" +
            "</div>";

        productsGrid.appendChild(card);
    });

    // Attach add-to-cart handlers
    document.querySelectorAll(".add-to-cart-btn").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            e.stopPropagation();
            var id = parseInt(btn.getAttribute("data-id"));
            addToCart(id);
        });
    });
}

function renderCart() {
    if (cart.length === 0) {
        cartItemsEl.innerHTML = '<p class="empty-cart">Your cart is empty</p>';
        cartCountEl.textContent = "0";
        cartTotalEl.textContent = "0.00";
        return;
    }

    var total = 0;
    var totalQty = 0;
    cartItemsEl.innerHTML = "";

    cart.forEach(function (item) {
        var product = productsMap[item.product_id];
        if (!product) return;

        var itemTotal = product.price * item.quantity;
        total += itemTotal;
        totalQty += item.quantity;

        var div = document.createElement("div");
        div.className = "cart-item";
        div.setAttribute("data-testid", "cart-item");
        div.innerHTML =
            '<div class="cart-item-info">' +
            '<div class="cart-item-name">' +
            product.name +
            "</div>" +
            '<div class="cart-item-price">$' +
            product.price.toFixed(2) +
            " × " +
            item.quantity +
            "</div>" +
            "</div>" +
            '<button class="cart-item-remove" data-id="' +
            item.id +
            '">×</button>';

        cartItemsEl.appendChild(div);
    });

    cartCountEl.textContent = totalQty;
    cartTotalEl.textContent = total.toFixed(2);

    // Remove handlers
    document.querySelectorAll(".cart-item-remove").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var id = parseInt(btn.getAttribute("data-id"));
            removeFromCart(id);
        });
    });
}

// --- Actions ---

async function addToCart(productId) {
    try {
        await addToCartAPI(productId);
        cart = await fetchCart();
        renderCart();
    } catch (err) {
        console.error("Add to cart failed:", err);
    }
}

async function removeFromCart(itemId) {
    try {
        await removeFromCartAPI(itemId);
        cart = await fetchCart();
        renderCart();
    } catch (err) {
        console.error("Remove from cart failed:", err);
    }
}

async function loadProducts() {
    var params = {};
    if (categoryFilter.value) params.category = categoryFilter.value;
    if (sortFilter.value) params.sort = sortFilter.value;

    products = await fetchProducts(params);
    products.forEach(function (p) {
        productsMap[p.id] = p;
    });
    renderProducts(products);
}

// --- Search with debounce ---

var searchTimeout;
searchInput.addEventListener("input", function () {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async function () {
        var query = searchInput.value.trim();
        try {
            if (query) {
                var results = await searchProducts(query);
                renderProducts(results);
            } else {
                await loadProducts();
            }
        } catch (err) {
            console.error("Search failed:", err);
        }
    }, 400);
});

// --- Voice search ---

var recognition = null;

try {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = "en-US";

        recognition.onresult = function (event) {
            var transcript = event.results[0][0].transcript;
            searchInput.value = transcript;
            searchInput.dispatchEvent(new Event("input"));
            stopListening();
        };

        recognition.onerror = function () {
            stopListening();
        };

        recognition.onend = function () {
            stopListening();
        };
    } else {
        voiceBtn.style.display = "none";
    }
} catch (e) {
    console.warn("Speech recognition not supported:", e);
    voiceBtn.style.display = "none";
}

function startListening() {
    if (!recognition) return;
    recognition.start();
    voiceBtn.classList.add("listening");
    voiceIndicator.style.display = "block";
}

function stopListening() {
    voiceBtn.classList.remove("listening");
    voiceIndicator.style.display = "none";
}

voiceBtn.addEventListener("click", function () {
    if (voiceBtn.classList.contains("listening")) {
        recognition.stop();
        stopListening();
    } else {
        startListening();
    }
});

// --- Cart panel ---

cartBtn.addEventListener("click", function () {
    cartPanel.classList.add("open");
    cartOverlay.classList.add("open");
});

closeCartBtn.addEventListener("click", closeCart);
cartOverlay.addEventListener("click", closeCart);

function closeCart() {
    cartPanel.classList.remove("open");
    cartOverlay.classList.remove("open");
}

// --- Filters ---

categoryFilter.addEventListener("change", loadProducts);
sortFilter.addEventListener("change", loadProducts);

// --- Init ---

async function init() {
    try {
        // Load categories
        var categories = await fetchCategories();
        categories.forEach(function (cat) {
            var opt = document.createElement("option");
            opt.value = cat;
            opt.textContent = cat;
            categoryFilter.appendChild(opt);
        });
    } catch (err) {
        console.error("Failed to load categories:", err);
    }

    try {
        // Load products
        await loadProducts();
    } catch (err) {
        console.error("Failed to load products:", err);
    }

    try {
        // Load cart
        cart = await fetchCart();
        renderCart();
    } catch (err) {
        console.error("Failed to load cart:", err);
    }
}

init();
