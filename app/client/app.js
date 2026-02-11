// VoxStore - Voice-Powered Product Catalog

const API_BASE = "/api";

// Strip punctuation and extra whitespace from voice transcripts
function cleanTranscript(text) {
    return text
        .replace(/[.,!?;:]+$/g, "")
        .replace(/\s+/g, " ")
        .trim();
}

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
const ratingFilter = document.getElementById("rating-filter");

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

async function extractSearchIntent(transcript) {
    var res = await fetch(API_BASE + "/voice/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript: transcript }),
    });
    if (!res.ok) throw new Error("Failed to extract search intent");
    return res.json();
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
    if (ratingFilter.value) params.min_rating = ratingFilter.value;

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
                renderProducts(filterAndSort(results));
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
var isRecording = false;
var activeStream = null;
var activeAudioCtx = null;
var activeWebSocket = null;
var activeSource = null;
var activeProcessor = null;
var recordingTriggeredBy = null; // 'button' or 'spacebar'
var partialTranscriptEl = document.getElementById("partial-transcript");
var voiceHint = document.getElementById("voice-hint");
var accumulatedTranscript = "";
var commitTimeoutId = null;

// Initialize browser SpeechRecognition as fallback
try {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = "en-US";

        recognition.onresult = function (event) {
            var transcript = cleanTranscript(event.results[0][0].transcript);
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
    }
} catch (e) {
    console.warn("Speech recognition not supported:", e);
}

var hasMicrophone = navigator.mediaDevices && navigator.mediaDevices.getUserMedia;

if (!hasMicrophone && !recognition) {
    voiceBtn.style.display = "none";
    if (voiceHint) voiceHint.style.display = "none";
}

function setVoiceStatus(message) {
    voiceIndicator.querySelector("span").textContent = message;
}

function setPartialTranscript(text) {
    if (partialTranscriptEl) {
        partialTranscriptEl.textContent = text;
    }
}

function startListening(triggeredBy) {
    if (isRecording) return;
    isRecording = true;
    recordingTriggeredBy = triggeredBy || "button";
    accumulatedTranscript = "";
    if (commitTimeoutId) {
        clearTimeout(commitTimeoutId);
        commitTimeoutId = null;
    }

    startWebSocketRecording();
}

// --- WebSocket-based realtime transcription (primary path) ---

function int16ToBase64(int16Array) {
    var bytes = new Uint8Array(int16Array.buffer);
    var binary = "";
    for (var i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

function startWebSocketRecording() {
    voiceBtn.classList.add("listening");
    voiceIndicator.style.display = "block";
    setVoiceStatus("Connecting...");
    setPartialTranscript("");

    // Step 1: Get token from backend
    fetch(API_BASE + "/transcribe/token", { method: "POST" })
        .then(function (res) {
            if (!res.ok) throw new Error("Token request failed: " + res.status);
            return res.json();
        })
        .then(function (data) {
            if (!isRecording) return; // user cancelled
            connectWebSocket(data.ws_url);
        })
        .catch(function (err) {
            console.warn("WebSocket token failed, falling back:", err);
            fallbackToMediaRecorder();
        });
}

function connectWebSocket(wsUrl) {
    console.log("[VOICE] Connecting WebSocket to:", wsUrl.substring(0, 60) + "...");
    var ws = new WebSocket(wsUrl);
    activeWebSocket = ws;

    ws.onopen = function () {
        console.log("[VOICE] WebSocket connected");
        if (!isRecording) {
            ws.close();
            return;
        }
        // Wait for session_started before capturing audio
    };

    ws.onmessage = function (event) {
        var msg;
        try {
            msg = JSON.parse(event.data);
        } catch (e) {
            return;
        }

        console.log("[VOICE] WS message:", msg.message_type, msg.text || "");

        if (msg.message_type === "session_started") {
            console.log("[VOICE] Session config:", JSON.stringify(msg.config));
            setVoiceStatus("Listening...");
            if (isRecording) {
                startAudioCapture(ws);
            }
        } else if (msg.message_type === "partial_transcript") {
            if (msg.text) {
                setPartialTranscript(msg.text);
            }
        } else if (msg.message_type === "committed_transcript") {
            var text = cleanTranscript(msg.text || "");
            if (text) {
                accumulatedTranscript += (accumulatedTranscript ? " " : "") + text;
                setPartialTranscript(accumulatedTranscript);
            }
        } else if (
            msg.message_type === "error" ||
            msg.message_type === "auth_error" ||
            msg.message_type === "quota_exceeded"
        ) {
            console.warn("[VOICE] WebSocket error:", msg);
            stopListening();
        }
    };

    ws.onerror = function (evt) {
        console.warn("[VOICE] WebSocket connection error", evt);
        ws.close();
        if (isRecording) {
            fallbackToMediaRecorder();
        }
    };

    ws.onclose = function (evt) {
        console.log("[VOICE] WebSocket closed, code:", evt.code, "reason:", evt.reason);
        if (activeWebSocket === ws) {
            activeWebSocket = null;
        }
    };
}

function startAudioCapture(ws) {
    console.log("[VOICE] Starting audio capture...");
    navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then(function (stream) {
            console.log("[VOICE] Got microphone stream");
            if (!isRecording) {
                stream.getTracks().forEach(function (t) {
                    t.stop();
                });
                return;
            }

            activeStream = stream;
            // Use default (native) sample rate — downsampling to 16kHz
            // happens in the AudioWorklet / ScriptProcessor.
            // Requesting sampleRate: 16000 fails in Firefox when the
            // mic stream was captured at a different rate.
            var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            activeAudioCtx = audioCtx;
            console.log("[VOICE] AudioContext sampleRate:", audioCtx.sampleRate);

            // Try AudioWorklet, fall back to ScriptProcessor
            if (audioCtx.audioWorklet) {
                audioCtx.audioWorklet
                    .addModule("audio-processor.js")
                    .then(function () {
                        if (!isRecording) return;
                        var source = audioCtx.createMediaStreamSource(stream);
                        var processor = new AudioWorkletNode(audioCtx, "pcm-processor");
                        activeSource = source;
                        activeProcessor = processor;
                        var chunkCount = 0;
                        processor.port.onmessage = function (e) {
                            if (ws.readyState === WebSocket.OPEN && e.data.pcmChunk) {
                                chunkCount++;
                                var chunk = e.data.pcmChunk;
                                if (chunkCount <= 5 || chunkCount % 50 === 0) {
                                    var maxAmp = 0;
                                    for (var j = 0; j < chunk.length; j++) {
                                        var abs = Math.abs(chunk[j]);
                                        if (abs > maxAmp) maxAmp = abs;
                                    }
                                    console.log(
                                        "[VOICE] Chunk #" + chunkCount,
                                        "size:",
                                        chunk.length,
                                        "maxAmp:",
                                        maxAmp,
                                    );
                                }
                                ws.send(
                                    JSON.stringify({
                                        message_type: "input_audio_chunk",
                                        audio_base_64: int16ToBase64(e.data.pcmChunk),
                                        commit: false,
                                        sample_rate: 16000,
                                    }),
                                );
                            }
                        };
                        source.connect(processor);
                        processor.connect(audioCtx.destination);
                    })
                    .catch(function () {
                        setupScriptProcessor(audioCtx, stream, ws);
                    });
            } else {
                setupScriptProcessor(audioCtx, stream, ws);
            }
        })
        .catch(function (err) {
            console.warn("Microphone access failed:", err);
            stopListening();
        });
}

function setupScriptProcessor(audioCtx, stream, ws) {
    var source = audioCtx.createMediaStreamSource(stream);
    var processor = audioCtx.createScriptProcessor(4096, 1, 1);
    activeSource = source;
    activeProcessor = processor;
    var ratio = audioCtx.sampleRate / 16000;

    processor.onaudioprocess = function (e) {
        if (ws.readyState !== WebSocket.OPEN) return;
        var input = e.inputBuffer.getChannelData(0);
        var outputLen = Math.floor(input.length / ratio);
        var output = new Int16Array(outputLen);
        for (var i = 0; i < outputLen; i++) {
            var idx = Math.floor(i * ratio);
            var sample = Math.max(-1, Math.min(1, input[idx]));
            output[i] = sample * 32767;
        }
        ws.send(
            JSON.stringify({
                message_type: "input_audio_chunk",
                audio_base_64: int16ToBase64(output),
                commit: false,
                sample_rate: 16000,
            }),
        );
    };

    source.connect(processor);
    processor.connect(audioCtx.destination);
}

// --- MediaRecorder fallback (used when WebSocket fails) ---

var hasMediaRecorder = typeof MediaRecorder !== "undefined" && hasMicrophone;

var SILENCE_THRESHOLD = 10;
var SILENCE_DURATION = 1500;
var MIN_RECORDING_MS = 1500;
var MAX_RECORDING_MS = 10000;

var mediaRecorder = null;

function fallbackToMediaRecorder() {
    // Clean up any WebSocket state
    if (activeWebSocket) {
        activeWebSocket.close();
        activeWebSocket = null;
    }
    cleanupAudio();

    if (hasMediaRecorder) {
        startMediaRecorderFallback();
    } else if (recognition) {
        isRecording = false;
        startBrowserRecognition();
    } else {
        stopListening();
    }
}

function startMediaRecorderFallback() {
    var chunks = [];
    navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then(function (stream) {
            if (!isRecording) {
                stream.getTracks().forEach(function (t) {
                    t.stop();
                });
                return;
            }

            activeStream = stream;
            mediaRecorder = new MediaRecorder(stream);

            mediaRecorder.ondataavailable = function (event) {
                if (event.data.size > 0) {
                    chunks.push(event.data);
                }
            };

            mediaRecorder.onstop = function () {
                stream.getTracks().forEach(function (track) {
                    track.stop();
                });
                activeStream = null;
                if (chunks.length === 0) {
                    stopListening();
                    return;
                }
                var audioBlob = new Blob(chunks, {
                    type: mediaRecorder.mimeType || "audio/webm",
                });
                uploadAudio(audioBlob);
            };

            mediaRecorder.start();
            voiceBtn.classList.add("listening");
            voiceIndicator.style.display = "block";
            setVoiceStatus("Listening...");

            monitorSilence(stream);
        })
        .catch(function (err) {
            console.warn("Microphone access failed:", err);
            isRecording = false;
            if (recognition) {
                startBrowserRecognition();
            }
        });
}

function monitorSilence(stream) {
    var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    var source = audioCtx.createMediaStreamSource(stream);
    var analyser = audioCtx.createAnalyser();
    analyser.fftSize = 512;
    source.connect(analyser);

    var dataArray = new Uint8Array(analyser.fftSize);
    var speechDetected = false;
    var silenceSince = null;
    var startedAt = Date.now();
    var maxTimer = setTimeout(function () {
        if (mediaRecorder && mediaRecorder.state === "recording") {
            mediaRecorder.stop();
        }
        cleanup();
    }, MAX_RECORDING_MS);

    function cleanup() {
        clearTimeout(maxTimer);
        source.disconnect();
        audioCtx.close();
    }

    function checkLevel() {
        if (!isRecording || !mediaRecorder || mediaRecorder.state !== "recording") {
            cleanup();
            return;
        }

        analyser.getByteTimeDomainData(dataArray);

        var sum = 0;
        for (var i = 0; i < dataArray.length; i++) {
            var val = (dataArray[i] - 128) / 128;
            sum += val * val;
        }
        var rms = Math.sqrt(sum / dataArray.length) * 100;

        var elapsed = Date.now() - startedAt;

        if (rms > SILENCE_THRESHOLD) {
            speechDetected = true;
            silenceSince = null;
        } else if (speechDetected && elapsed > MIN_RECORDING_MS) {
            if (!silenceSince) {
                silenceSince = Date.now();
            } else if (Date.now() - silenceSince > SILENCE_DURATION) {
                if (mediaRecorder && mediaRecorder.state === "recording") {
                    mediaRecorder.stop();
                }
                cleanup();
                return;
            }
        }

        requestAnimationFrame(checkLevel);
    }

    checkLevel();
}

function startBrowserRecognition() {
    if (!recognition) return;
    isRecording = true;
    recognition.start();
    voiceBtn.classList.add("listening");
    voiceIndicator.style.display = "block";
    setVoiceStatus("Listening...");
}

function cleanupAudio() {
    if (activeProcessor) {
        activeProcessor.disconnect();
        activeProcessor = null;
    }
    if (activeSource) {
        activeSource.disconnect();
        activeSource = null;
    }
    if (activeStream) {
        activeStream.getTracks().forEach(function (t) {
            t.stop();
        });
        activeStream = null;
    }
    if (activeAudioCtx) {
        activeAudioCtx.close().catch(function () {});
        activeAudioCtx = null;
    }
}

function commitAndStop() {
    // Stop capturing audio but keep the WebSocket open so ElevenLabs can
    // return the final transcript.  Send a commit message to force
    // transcription of whatever audio has been received.
    isRecording = false;
    recordingTriggeredBy = null;
    voiceBtn.classList.remove("listening");
    cleanupAudio();

    if (activeWebSocket && activeWebSocket.readyState === WebSocket.OPEN) {
        setVoiceStatus("Transcribing...");
        console.log("[VOICE] Sending commit, waiting for transcript...");
        activeWebSocket.send(
            JSON.stringify({
                message_type: "input_audio_chunk",
                audio_base_64: "",
                commit: true,
            }),
        );
        // Wait briefly for final committed_transcript, then process
        var ws = activeWebSocket;
        commitTimeoutId = setTimeout(function () {
            commitTimeoutId = null;
            if (activeWebSocket === ws) {
                console.log("[VOICE] Processing accumulated transcript");
                processAccumulatedTranscript().then(function () {
                    stopListening();
                });
            }
        }, 2000);
    } else {
        processAccumulatedTranscript().then(function () {
            stopListening();
        });
    }
}

function processAccumulatedTranscript() {
    var transcript = accumulatedTranscript.trim();
    accumulatedTranscript = "";
    if (transcript) {
        return applyVoiceSearchExtraction(transcript);
    }
    return Promise.resolve();
}

function stopListening() {
    isRecording = false;
    recordingTriggeredBy = null;
    accumulatedTranscript = "";
    if (commitTimeoutId) {
        clearTimeout(commitTimeoutId);
        commitTimeoutId = null;
    }
    voiceBtn.classList.remove("listening");
    voiceIndicator.style.display = "none";
    setPartialTranscript("");

    if (activeWebSocket) {
        activeWebSocket.close();
        activeWebSocket = null;
    }
    cleanupAudio();
}

function fallbackToBrowser() {
    stopListening();
    if (recognition) {
        startBrowserRecognition();
    }
}

function uploadAudio(audioBlob) {
    setVoiceStatus("Transcribing...");

    var formData = new FormData();
    formData.append("file", audioBlob, "recording.webm");

    fetch(API_BASE + "/transcribe", {
        method: "POST",
        body: formData,
    })
        .then(function (res) {
            return res.json();
        })
        .then(function (data) {
            if (data.success && data.text) {
                searchInput.value = cleanTranscript(data.text);
                searchInput.dispatchEvent(new Event("input"));
                stopListening();
            } else {
                console.warn("Transcription failed:", data.error);
                fallbackToBrowser();
            }
        })
        .catch(function (err) {
            console.warn("Transcription request failed:", err);
            fallbackToBrowser();
        });
}

async function applyVoiceSearchExtraction(transcript) {
    try {
        setVoiceStatus("Understanding...");
        voiceIndicator.style.display = "block";
        var extraction = await extractSearchIntent(transcript);

        // Apply extracted query to search input
        if (extraction.query) {
            searchInput.value = extraction.query;
        }

        // Apply extracted filters to dropdowns
        if (extraction.category) {
            categoryFilter.value = extraction.category;
        }
        if (extraction.sort) {
            sortFilter.value = extraction.sort;
        }
        if (extraction.min_rating) {
            ratingFilter.value = String(Math.floor(extraction.min_rating));
        }

        // Trigger search with all applied filters
        if (extraction.query) {
            var results = await searchProducts(extraction.query);
            renderProducts(filterAndSort(results));
        } else {
            await loadProducts();
        }
    } catch (err) {
        console.error("Voice extraction failed, falling back:", err);
        // Fallback: just do regular search with raw transcript
        searchInput.value = transcript;
        searchInput.dispatchEvent(new Event("input"));
    } finally {
        voiceIndicator.style.display = "none";
        setPartialTranscript("");
    }
}

voiceBtn.addEventListener("click", function () {
    if (isRecording) {
        if (activeWebSocket) {
            commitAndStop();
        } else if (mediaRecorder && mediaRecorder.state === "recording") {
            mediaRecorder.stop();
        } else if (recognition) {
            recognition.stop();
            stopListening();
        }
    } else {
        startListening("button");
    }
});

// --- Spacebar push-to-talk ---

function isTextInputFocused() {
    var el = document.activeElement;
    if (!el) return false;
    var tag = el.tagName.toUpperCase();
    return tag === "INPUT" || tag === "TEXTAREA" || el.contentEditable === "true";
}

document.addEventListener("keydown", function (e) {
    if (e.key !== "Alt") return;
    if (e.repeat) return;
    if (isRecording) return;

    if (isTextInputFocused()) {
        document.activeElement.blur();
    }

    e.preventDefault();
    startListening("hotkey");
});

document.addEventListener("keyup", function (e) {
    if (e.key !== "Alt") return;
    if (recordingTriggeredBy !== "hotkey") return;

    e.preventDefault();
    if (isRecording) {
        commitAndStop();
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

categoryFilter.addEventListener("change", applyFilters);
sortFilter.addEventListener("change", applyFilters);
ratingFilter.addEventListener("change", applyFilters);

async function applyFilters() {
    var query = searchInput.value.trim();
    if (query) {
        try {
            var results = await searchProducts(query);
            renderProducts(filterAndSort(results));
        } catch (err) {
            console.error("Search failed:", err);
        }
    } else {
        await loadProducts();
    }
}

function filterAndSort(items) {
    var filtered = items.slice();
    var cat = categoryFilter.value;
    var minRating = ratingFilter.value ? parseFloat(ratingFilter.value) : null;
    var sort = sortFilter.value;

    if (cat) {
        filtered = filtered.filter(function (p) {
            return p.category === cat;
        });
    }
    if (minRating) {
        filtered = filtered.filter(function (p) {
            return p.rating >= minRating;
        });
    }
    if (sort === "price_asc") {
        filtered.sort(function (a, b) {
            return a.price - b.price;
        });
    } else if (sort === "price_desc") {
        filtered.sort(function (a, b) {
            return b.price - a.price;
        });
    } else if (sort === "rating") {
        filtered.sort(function (a, b) {
            return b.rating - a.rating;
        });
    }
    return filtered;
}

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
        // If search input has a pre-filled value (e.g. browser autofill on refresh),
        // perform that search instead of loading all products
        var initialQuery = searchInput.value.trim();
        if (initialQuery) {
            var results = await searchProducts(initialQuery);
            renderProducts(results);
        } else {
            await loadProducts();
        }
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
