const { defineConfig, devices } = require("@playwright/test");

const port = Number(process.env.BACKEND_PORT) || 8000;

module.exports = defineConfig({
    testDir: "./tests/e2e",
    timeout: 30000,
    retries: 1,
    workers: 1,
    use: {
        baseURL: `http://localhost:${port}`,
        screenshot: "only-on-failure",
        trace: "retain-on-failure",
    },
    projects: [
        { name: "chromium", use: { ...devices["Desktop Chrome"] } },
        { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    ],
    webServer: {
        command: "cd app/server && uv run python server.py",
        port,
        timeout: 15000,
        reuseExistingServer: !process.env.CI,
        env: {
            SENTRY_DSN: "",
            BACKEND_PORT: String(port),
        },
    },
    outputDir: "test-results/",
    reporter: [["html", { outputFolder: "playwright-report" }]],
});
