const { test, expect } = require("@playwright/test");

test.describe("Product Browsing", () => {
    test("loads product grid on homepage", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');
        const cards = await page.locator('[data-testid="product-card"]').count();
        expect(cards).toBe(61);
        await page.screenshot({
            path: "test-results/screenshots/product-grid-loaded.png",
            fullPage: true,
        });
    });

    test("filters by category", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');
        await page.selectOption('[data-testid="category-filter"]', "Electronics");
        await page.waitForTimeout(500);
        const cards = page.locator('[data-testid="product-card"]');
        const count = await cards.count();
        expect(count).toBeGreaterThan(0);
        expect(count).toBeLessThan(61);
        // Verify all visible products are Electronics
        for (let i = 0; i < count; i++) {
            const category = await cards.nth(i).locator(".product-category").textContent();
            expect(category.trim().toUpperCase()).toBe("ELECTRONICS");
        }
        await page.screenshot({
            path: "test-results/screenshots/filtered-electronics.png",
            fullPage: true,
        });
    });

    test("sorts by price ascending", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');
        await page.selectOption('[data-testid="sort-filter"]', "price_asc");
        await page.waitForTimeout(500);
        const prices = await page.locator(".product-price").allTextContents();
        const nums = prices.map((p) => parseFloat(p.replace("$", "")));
        for (let i = 1; i < nums.length; i++) {
            expect(nums[i]).toBeGreaterThanOrEqual(nums[i - 1]);
        }
    });

    test("sorts by price descending", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');
        await page.selectOption('[data-testid="sort-filter"]', "price_desc");
        await page.waitForTimeout(500);
        const prices = await page.locator(".product-price").allTextContents();
        const nums = prices.map((p) => parseFloat(p.replace("$", "")));
        for (let i = 1; i < nums.length; i++) {
            expect(nums[i]).toBeLessThanOrEqual(nums[i - 1]);
        }
    });

    test("sorts by rating", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');
        await page.selectOption('[data-testid="sort-filter"]', "rating");
        await page.waitForTimeout(500);
        const ratings = await page.locator(".product-rating").allTextContents();
        const nums = ratings.map((r) => parseFloat(r.split(" ").pop()));
        for (let i = 1; i < nums.length; i++) {
            expect(nums[i]).toBeLessThanOrEqual(nums[i - 1]);
        }
    });
});
