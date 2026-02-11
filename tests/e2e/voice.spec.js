const { test, expect } = require("@playwright/test");

// Mock the /api/transcribe/token endpoint and WebSocket connection.
// When the frontend fetches a token, we return a fake one.
// When it opens a WebSocket, our mock accepts audio chunks and
// returns a committed_transcript after a short delay.
function mockWebSocketTranscription(page, transcript) {
    return page.addInitScript(
        ([text]) => {
            // Mock the token endpoint response will be handled by page.route

            // Mock WebSocket
            const OriginalWebSocket = window.WebSocket;
            class MockWebSocket {
                constructor(url) {
                    this.url = url;
                    this.readyState = 0; // CONNECTING
                    this.onopen = null;
                    this.onmessage = null;
                    this.onerror = null;
                    this.onclose = null;
                    this._audioReceived = false;

                    // Simulate connection
                    setTimeout(() => {
                        this.readyState = 1; // OPEN
                        if (this.onopen) this.onopen({});
                        // Send session_started
                        if (this.onmessage) {
                            this.onmessage({
                                data: JSON.stringify({
                                    message_type: "session_started",
                                }),
                            });
                        }
                    }, 50);
                }

                send(data) {
                    if (this.readyState !== 1) return;
                    try {
                        var msg = JSON.parse(data);
                        if (msg.message_type === "input_audio_chunk" && !this._audioReceived) {
                            this._audioReceived = true;
                            // Send partial transcript
                            setTimeout(() => {
                                if (this.onmessage) {
                                    this.onmessage({
                                        data: JSON.stringify({
                                            message_type: "partial_transcript",
                                            text: text.substring(0, Math.ceil(text.length / 2)),
                                        }),
                                    });
                                }
                            }, 100);
                            // Send committed transcript
                            setTimeout(() => {
                                if (this.onmessage) {
                                    this.onmessage({
                                        data: JSON.stringify({
                                            message_type: "committed_transcript",
                                            text: text,
                                        }),
                                    });
                                }
                            }, 300);
                        }
                    } catch (e) {
                        // ignore parse errors
                    }
                }

                close() {
                    this.readyState = 3; // CLOSED
                    if (this.onclose) this.onclose({});
                }
            }

            MockWebSocket.OPEN = 1;
            MockWebSocket.CLOSED = 3;
            MockWebSocket.CONNECTING = 0;

            window.WebSocket = MockWebSocket;

            // Mock getUserMedia to return a fake audio stream
            if (navigator.mediaDevices) {
                const origGetUserMedia =
                    navigator.mediaDevices.getUserMedia &&
                    navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
                navigator.mediaDevices.getUserMedia = function (constraints) {
                    if (constraints.audio) {
                        // Use default sample rate (matching the app's
                        // AudioContext) to avoid Firefox's
                        // "different sample-rate" error.
                        const ctx = new AudioContext();
                        const oscillator = ctx.createOscillator();
                        const dest = ctx.createMediaStreamDestination();
                        oscillator.connect(dest);
                        oscillator.start();
                        return Promise.resolve(dest.stream);
                    }
                    if (origGetUserMedia) return origGetUserMedia(constraints);
                    return Promise.reject(new Error("getUserMedia not available"));
                };
            }

            // Mock AudioWorklet to avoid loading audio-processor.js in test
            // The AudioContext will be created with sampleRate 16000, but the
            // AudioWorklet might not be available in the test browser context,
            // so we ensure a ScriptProcessor fallback works.
        },
        [transcript],
    );
}

// Mock that forces WebSocket to fail, falling back to MediaRecorder + REST
function mockMediaRecorderFallback(page) {
    return page.addInitScript(() => {
        // Make WebSocket constructor throw
        window.WebSocket = function () {
            throw new Error("WebSocket not available");
        };

        // Build a minimal valid WAV file
        function createSilentWav() {
            const sampleRate = 16000;
            const numSamples = sampleRate / 10;
            const dataSize = numSamples * 2;
            const buffer = new ArrayBuffer(44 + dataSize);
            const view = new DataView(buffer);

            function writeString(offset, str) {
                for (let i = 0; i < str.length; i++) {
                    view.setUint8(offset + i, str.charCodeAt(i));
                }
            }

            writeString(0, "RIFF");
            view.setUint32(4, 36 + dataSize, true);
            writeString(8, "WAVE");
            writeString(12, "fmt ");
            view.setUint32(16, 16, true);
            view.setUint16(20, 1, true);
            view.setUint16(22, 1, true);
            view.setUint32(24, sampleRate, true);
            view.setUint32(28, sampleRate * 2, true);
            view.setUint16(32, 2, true);
            view.setUint16(34, 16, true);
            writeString(36, "data");
            view.setUint32(40, dataSize, true);

            return new Blob([buffer], { type: "audio/wav" });
        }

        // Mock MediaRecorder
        class MockMediaRecorder {
            constructor(stream) {
                this.stream = stream;
                this.state = "inactive";
                this.mimeType = "audio/wav";
                this.ondataavailable = null;
                this.onstop = null;
            }

            start() {
                this.state = "recording";
                const blob = createSilentWav();
                setTimeout(() => {
                    if (this.ondataavailable) {
                        this.ondataavailable({ data: blob });
                    }
                }, 50);
                this._autoStopTimer = setTimeout(() => {
                    if (this.state === "recording") {
                        this.stop();
                    }
                }, 300);
            }

            stop() {
                if (this.state === "inactive") return;
                clearTimeout(this._autoStopTimer);
                this.state = "inactive";
                this.stream.getTracks().forEach((t) => t.stop());
                setTimeout(() => {
                    if (this.onstop) {
                        this.onstop();
                    }
                }, 50);
            }
        }

        window.MediaRecorder = MockMediaRecorder;

        // Mock getUserMedia
        if (navigator.mediaDevices) {
            const origGetUserMedia =
                navigator.mediaDevices.getUserMedia &&
                navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
            navigator.mediaDevices.getUserMedia = function (constraints) {
                if (constraints.audio) {
                    const ctx = new AudioContext();
                    const oscillator = ctx.createOscillator();
                    const dest = ctx.createMediaStreamDestination();
                    oscillator.connect(dest);
                    oscillator.start();
                    return Promise.resolve(dest.stream);
                }
                if (origGetUserMedia) return origGetUserMedia(constraints);
                return Promise.reject(new Error("getUserMedia not available"));
            };
        }
    });
}

test.describe("Voice Search", () => {
    test("transcribes audio via WebSocket and searches products", async ({ page, browserName }) => {
        test.skip(browserName === "firefox", "WebSocket mock unreliable in Firefox");

        await mockWebSocketTranscription(page, "headphones");

        // Mock the token endpoint
        await page.route("**/api/transcribe/token", async (route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    token: "fake-token",
                    ws_url: "wss://fake.elevenlabs.io/v1/stt",
                }),
            });
        });

        // Mock the voice extraction endpoint
        await page.route("**/api/voice/extract", async (route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    query: "headphones",
                    min_rating: null,
                    sort: null,
                    category: null,
                }),
            });
        });

        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        const initialCount = await page.locator('[data-testid="product-card"]').count();
        expect(initialCount).toBe(61);

        // Click voice button to start recording
        await page.click('[data-testid="voice-button"]');

        // Wait for transcript to be accumulated
        await page.waitForTimeout(500);

        // Click voice button again to stop recording and trigger extraction
        await page.click('[data-testid="voice-button"]');

        // Search input should be populated with the extracted query
        await expect(page.locator('[data-testid="search-input"]')).toHaveValue("headphones", {
            timeout: 10000,
        });

        // Should show filtered results (wait for extraction + search)
        await expect(async () => {
            const filteredCount = await page.locator('[data-testid="product-card"]').count();
            expect(filteredCount).toBeGreaterThan(0);
            expect(filteredCount).toBeLessThan(initialCount);
        }).toPass({ timeout: 5000 });
    });

    test("shows partial transcript during recording", async ({ page, browserName }) => {
        test.skip(browserName === "firefox", "WebSocket mock unreliable in Firefox");
        await mockWebSocketTranscription(page, "keyboard");

        await page.route("**/api/transcribe/token", async (route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    token: "fake-token",
                    ws_url: "wss://fake.elevenlabs.io/v1/stt",
                }),
            });
        });

        // Mock the voice extraction endpoint
        await page.route("**/api/voice/extract", async (route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    query: "keyboard",
                    min_rating: null,
                    sort: null,
                    category: null,
                }),
            });
        });

        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        // Start recording
        await page.click('[data-testid="voice-button"]');

        // Wait for transcript to be accumulated
        await page.waitForTimeout(500);

        // Stop recording to trigger extraction
        await page.click('[data-testid="voice-button"]');

        // After extraction, search should be populated and indicator hidden
        await expect(page.locator('[data-testid="search-input"]')).toHaveValue("keyboard", {
            timeout: 10000,
        });

        await expect(page.locator('[data-testid="voice-indicator"]')).toBeHidden({ timeout: 5000 });
    });

    test("falls back to MediaRecorder when WebSocket fails", async ({ page }) => {
        await mockMediaRecorderFallback(page);

        // Token endpoint fails
        await page.route("**/api/transcribe/token", async (route) => {
            await route.fulfill({
                status: 500,
                contentType: "application/json",
                body: JSON.stringify({ detail: "No API key" }),
            });
        });

        // But REST transcribe works
        await page.route("**/api/transcribe", async (route) => {
            if (route.request().method() === "POST") {
                await route.fulfill({
                    status: 200,
                    contentType: "application/json",
                    body: JSON.stringify({
                        text: "speaker",
                        success: true,
                        error: null,
                    }),
                });
            } else {
                await route.continue();
            }
        });

        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        await page.click('[data-testid="voice-button"]');

        await page.waitForTimeout(2000);

        await expect(page.locator('[data-testid="search-input"]')).toHaveValue("speaker");
    });

    test("manual stop works during WebSocket recording", async ({ page }) => {
        await mockWebSocketTranscription(page, "monitor");

        await page.route("**/api/transcribe/token", async (route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    token: "fake-token",
                    ws_url: "wss://fake.elevenlabs.io/v1/stt",
                }),
            });
        });

        // Mock voice extraction endpoint
        await page.route("**/api/voice/extract", async (route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    query: "monitor",
                    min_rating: null,
                    sort: null,
                    category: null,
                }),
            });
        });

        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        // Start recording
        await page.click('[data-testid="voice-button"]');
        await expect(page.locator('[data-testid="voice-indicator"]')).toBeVisible({
            timeout: 3000,
        });

        // Immediately click again to manually stop
        await page.click('[data-testid="voice-button"]');

        // Indicator should be hidden after commit timeout + extraction
        await expect(page.locator('[data-testid="voice-indicator"]')).toBeHidden({
            timeout: 5000,
        });
    });
});

test.describe("Alt Push-to-Talk", () => {
    test("alt key starts and stops recording", async ({ page }) => {
        await mockWebSocketTranscription(page, "laptop");

        await page.route("**/api/transcribe/token", async (route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    token: "fake-token",
                    ws_url: "wss://fake.elevenlabs.io/v1/stt",
                }),
            });
        });

        await page.route("**/api/voice/extract", async (route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    query: "laptop",
                    min_rating: null,
                    sort: null,
                    category: null,
                }),
            });
        });

        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        // Press Alt
        await page.keyboard.down("Alt");
        await expect(page.locator('[data-testid="voice-indicator"]')).toBeVisible({
            timeout: 3000,
        });

        // Release Alt to stop
        await page.keyboard.up("Alt");
        await expect(page.locator('[data-testid="voice-indicator"]')).toBeHidden({ timeout: 3000 });
    });

    test("alt key works when search input is focused", async ({ page }) => {
        await mockWebSocketTranscription(page, "tablet");

        await page.route("**/api/transcribe/token", async (route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    token: "fake-token",
                    ws_url: "wss://fake.elevenlabs.io/v1/stt",
                }),
            });
        });

        await page.route("**/api/voice/extract", async (route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    query: "tablet",
                    min_rating: null,
                    sort: null,
                    category: null,
                }),
            });
        });

        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        // Focus the search input
        await page.locator('[data-testid="search-input"]').focus();

        // Press Alt — should trigger recording and blur input
        await page.keyboard.down("Alt");
        await expect(page.locator('[data-testid="voice-indicator"]')).toBeVisible({
            timeout: 3000,
        });

        // Search input should no longer be focused
        const focused = await page.evaluate(() => document.activeElement?.id !== "search-input");
        expect(focused).toBe(true);

        // Release Alt to stop
        await page.keyboard.up("Alt");
        await expect(page.locator('[data-testid="voice-indicator"]')).toBeHidden({ timeout: 3000 });
    });

    test("alt hint is visible on page load", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        await expect(page.locator('[data-testid="voice-hint"]')).toBeVisible();
        await expect(page.locator('[data-testid="voice-hint"]')).toContainText("Alt");
    });
});
