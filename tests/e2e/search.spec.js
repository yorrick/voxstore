const { test, expect } = require("@playwright/test");

test.describe("Search", () => {
    test("searches products by text", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');
        const initialCount = await page.locator('[data-testid="product-card"]').count();
        await page.fill('[data-testid="search-input"]', "headphones");
        await expect(async () => {
            const cards = await page.locator('[data-testid="product-card"]').count();
            expect(cards).toBeGreaterThan(0);
            expect(cards).toBeLessThan(initialCount);
        }).toPass({ timeout: 5000 });
        await page.screenshot({
            path: "test-results/screenshots/search-headphones.png",
            fullPage: true,
        });
    });

    test("shows no results for nonexistent query", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');
        await page.fill('[data-testid="search-input"]', "xyznonexistent999");
        await expect(async () => {
            const cards = await page.locator('[data-testid="product-card"]').count();
            expect(cards).toBe(0);
        }).toPass({ timeout: 5000 });
        await page.screenshot({
            path: "test-results/screenshots/search-no-results.png",
            fullPage: true,
        });
    });

    test("clearing search restores all products", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');
        const initialCount = await page.locator('[data-testid="product-card"]').count();
        await page.fill('[data-testid="search-input"]', "headphones");
        await expect(async () => {
            const cards = await page.locator('[data-testid="product-card"]').count();
            expect(cards).toBeLessThan(initialCount);
        }).toPass({ timeout: 5000 });
        await page.fill('[data-testid="search-input"]', "");
        await expect(async () => {
            const cards = await page.locator('[data-testid="product-card"]').count();
            expect(cards).toBe(initialCount);
        }).toPass({ timeout: 5000 });
    });

    test("search is case insensitive", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');
        await page.fill('[data-testid="search-input"]', "KEYBOARD");
        await expect(async () => {
            const cards = await page.locator('[data-testid="product-card"]').count();
            expect(cards).toBeGreaterThan(0);
        }).toPass({ timeout: 5000 });
    });
});
