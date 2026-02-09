const { test, expect } = require("@playwright/test");

test.describe("Visual Snapshots", () => {
    test("homepage with products loaded", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');
        await page.waitForTimeout(500); // wait for images
        await expect(page).toHaveScreenshot("homepage.png", {
            fullPage: true,
            maxDiffPixelRatio: 0.1,
        });
    });

    test("cart panel open with item", async ({ page, request }) => {
        // Clear cart via API to ensure deterministic state
        const cartResponse = await request.get("/api/cart");
        const cartItems = await cartResponse.json();
        for (const item of cartItems) {
            await request.delete(`/api/cart/${item.id}`);
        }
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');
        await page.locator('[data-testid="add-to-cart-btn"]').first().click();
        await page.waitForTimeout(300);
        await page.click('[data-testid="cart-button"]');
        await page.waitForTimeout(300);
        await expect(page).toHaveScreenshot("cart-open.png", { maxDiffPixelRatio: 0.1 });
    });
});
