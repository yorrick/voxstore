const { test, expect } = require("@playwright/test");

test.describe("Cart", () => {
    test.beforeEach(async ({ page, request }) => {
        // Clear cart via API before each test
        const cartResponse = await request.get("/api/cart");
        const cartItems = await cartResponse.json();
        for (const item of cartItems) {
            await request.delete(`/api/cart/${item.id}`);
        }
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');
    });

    test("cart is empty initially", async ({ page }) => {
        await expect(page.locator('[data-testid="cart-count"]')).toHaveText("0");
    });

    test("adds product to cart", async ({ page }) => {
        await page.locator('[data-testid="add-to-cart-btn"]').first().click();
        await expect(page.locator('[data-testid="cart-count"]')).toHaveText("1", {
            timeout: 3000,
        });
    });

    test("opens and closes cart panel", async ({ page }) => {
        await page.click('[data-testid="cart-button"]');
        await expect(page.locator('[data-testid="cart-panel"]')).toHaveClass(/open/);
        await expect(page.locator('[data-testid="cart-overlay"]')).toHaveClass(/open/);

        await page.click('[data-testid="close-cart"]');
        await expect(page.locator('[data-testid="cart-panel"]')).not.toHaveClass(/open/);
    });

    test("closes cart via overlay click", async ({ page }) => {
        await page.click('[data-testid="cart-button"]');
        await expect(page.locator('[data-testid="cart-panel"]')).toHaveClass(/open/);
        await page.click('[data-testid="cart-overlay"]');
        await expect(page.locator('[data-testid="cart-panel"]')).not.toHaveClass(/open/);
    });

    test("displays cart item with correct details", async ({ page }) => {
        await page.locator('[data-testid="add-to-cart-btn"]').first().click();
        await expect(page.locator('[data-testid="cart-count"]')).toHaveText("1", {
            timeout: 3000,
        });

        await page.click('[data-testid="cart-button"]');
        await expect(page.locator('[data-testid="cart-item"]')).toHaveCount(1);

        const total = await page.locator('[data-testid="cart-total"]').textContent();
        expect(parseFloat(total)).toBeGreaterThan(0);
    });

    test("adds multiple products to cart", async ({ page }) => {
        const buttons = page.locator('[data-testid="add-to-cart-btn"]');

        await buttons.nth(0).click();
        await expect(page.locator('[data-testid="cart-count"]')).toHaveText("1", {
            timeout: 3000,
        });

        await buttons.nth(1).click();
        await expect(page.locator('[data-testid="cart-count"]')).toHaveText("2", {
            timeout: 3000,
        });

        await buttons.nth(2).click();
        await expect(page.locator('[data-testid="cart-count"]')).toHaveText("3", {
            timeout: 3000,
        });
    });

    test("removes item from cart", async ({ page }) => {
        await page.locator('[data-testid="add-to-cart-btn"]').first().click();
        await expect(page.locator('[data-testid="cart-count"]')).toHaveText("1", {
            timeout: 3000,
        });

        await page.click('[data-testid="cart-button"]');
        await expect(page.locator('[data-testid="cart-item"]')).toHaveCount(1);

        await page.locator(".cart-item-remove").first().click();

        await expect(page.locator('[data-testid="cart-count"]')).toHaveText("0", {
            timeout: 3000,
        });
        await expect(page.locator(".empty-cart")).toBeVisible();
    });

    test("empty cart shows message", async ({ page }) => {
        await page.click('[data-testid="cart-button"]');
        await expect(page.locator(".empty-cart")).toBeVisible();
        await expect(page.locator('[data-testid="cart-total"]')).toHaveText("0.00");
    });
});
