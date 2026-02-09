const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  retries: 1,
  use: {
    baseURL: 'http://localhost:8000',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'cd app/server && uv run python server.py',
    port: 8000,
    timeout: 15000,
    reuseExistingServer: !process.env.CI,
    env: {
      SENTRY_DSN: '',
      BACKEND_PORT: '8000',
    },
  },
  outputDir: 'test-results/',
  reporter: [['html', { outputFolder: 'playwright-report' }]],
});
