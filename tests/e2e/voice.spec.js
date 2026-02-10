const { test, expect } = require("@playwright/test");

// Mock MediaRecorder and getUserMedia so voice tests work without a real mic.
// When mediaRecorder.start() is called, it immediately fires ondataavailable
// with a tiny valid WAV blob (1s silence), then fires onstop after a short delay
// (simulating the user clicking stop).
function mockMediaRecorder(page) {
    return page.addInitScript(() => {
        // Build a minimal valid WAV file (16-bit PCM, 16kHz, 1 channel, 0.1s silence)
        function createSilentWav() {
            const sampleRate = 16000;
            const numSamples = sampleRate / 10; // 0.1 seconds
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
            view.setUint16(20, 1, true); // PCM
            view.setUint16(22, 1, true); // mono
            view.setUint32(24, sampleRate, true);
            view.setUint32(28, sampleRate * 2, true);
            view.setUint16(32, 2, true);
            view.setUint16(34, 16, true);
            writeString(36, "data");
            view.setUint32(40, dataSize, true);
            // samples are all zeros (silence)

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
                // Provide audio data immediately
                const blob = createSilentWav();
                setTimeout(() => {
                    if (this.ondataavailable) {
                        this.ondataavailable({ data: blob });
                    }
                }, 50);
                // Auto-stop after a short delay (simulates silence detection)
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
                // Stop the stream tracks
                this.stream.getTracks().forEach((t) => t.stop());
                setTimeout(() => {
                    if (this.onstop) {
                        this.onstop();
                    }
                }, 50);
            }
        }

        // Replace globals
        window.MediaRecorder = MockMediaRecorder;

        // Mock getUserMedia to return a fake stream
        const originalGetUserMedia =
            navigator.mediaDevices &&
            navigator.mediaDevices.getUserMedia &&
            navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);

        if (navigator.mediaDevices) {
            navigator.mediaDevices.getUserMedia = function (constraints) {
                if (constraints.audio) {
                    // Create a fake audio stream using AudioContext
                    const ctx = new AudioContext();
                    const oscillator = ctx.createOscillator();
                    const dest = ctx.createMediaStreamDestination();
                    oscillator.connect(dest);
                    oscillator.start();
                    return Promise.resolve(dest.stream);
                }
                if (originalGetUserMedia) {
                    return originalGetUserMedia(constraints);
                }
                return Promise.reject(new Error("getUserMedia not available"));
            };
        }
    });
}

test.describe("Voice Search", () => {
    test("transcribes audio and searches products", async ({ page }) => {
        await mockMediaRecorder(page);

        // Intercept /api/transcribe and return a mocked transcript
        await page.route("**/api/transcribe", async (route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    text: "headphones",
                    success: true,
                    error: null,
                }),
            });
        });

        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        // Count initial products
        const initialCount = await page.locator('[data-testid="product-card"]').count();
        expect(initialCount).toBe(26);

        // Click voice button — recording starts and auto-stops via silence detection
        await page.click('[data-testid="voice-button"]');

        // Wait for auto-stop, upload, and search debounce to settle
        await page.waitForTimeout(2000);

        // Search input should be populated with the transcript
        await expect(page.locator('[data-testid="search-input"]')).toHaveValue("headphones");

        // Should show filtered results
        const filteredCount = await page.locator('[data-testid="product-card"]').count();
        expect(filteredCount).toBeGreaterThan(0);
        expect(filteredCount).toBeLessThan(26);
    });

    test("shows transcribing state during upload", async ({ page }) => {
        await mockMediaRecorder(page);

        // Delay the transcribe response to observe the "Transcribing..." state
        await page.route("**/api/transcribe", async (route) => {
            await new Promise((r) => setTimeout(r, 500));
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    text: "keyboard",
                    success: true,
                    error: null,
                }),
            });
        });

        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        // Start recording — auto-stops, then transitions to "Transcribing..."
        await page.click('[data-testid="voice-button"]');
        await expect(page.locator('[data-testid="voice-indicator"] span')).toHaveText(
            "Transcribing...",
            { timeout: 3000 },
        );

        // After response, indicator should disappear
        await expect(page.locator('[data-testid="voice-indicator"]')).toBeHidden({
            timeout: 3000,
        });

        // Search input should have the transcript
        await expect(page.locator('[data-testid="search-input"]')).toHaveValue("keyboard");
    });

    test("handles API failure gracefully", async ({ page }) => {
        await mockMediaRecorder(page);

        // Make /api/transcribe fail
        await page.route("**/api/transcribe", async (route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    text: "",
                    success: false,
                    error: "ELEVENLABS_API_KEY not configured",
                }),
            });
        });

        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        // Start recording — auto-stops, upload fails, fallback logic runs
        await page.click('[data-testid="voice-button"]');

        // Wait for auto-stop + API response + fallback logic to settle
        await page.waitForTimeout(2000);

        // App should not be broken — products should still be visible
        const cards = await page.locator('[data-testid="product-card"]').count();
        expect(cards).toBe(26);

        // If browser fallback started (Chrome), click to stop it.
        // If no fallback (Firefox), indicator is already hidden.
        if (await page.locator('[data-testid="voice-indicator"]').isVisible()) {
            await page.click('[data-testid="voice-button"]');
        }
        await expect(page.locator('[data-testid="voice-indicator"]')).toBeHidden({
            timeout: 3000,
        });
    });

    test("manual stop still works before auto-stop", async ({ page }) => {
        await mockMediaRecorder(page);

        await page.route("**/api/transcribe", async (route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    text: "speaker",
                    success: true,
                    error: null,
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

        // Should still complete the transcription flow
        await page.waitForTimeout(1500);
        await expect(page.locator('[data-testid="search-input"]')).toHaveValue("speaker");
    });
});
