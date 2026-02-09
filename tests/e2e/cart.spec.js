const { test, expect } = require('@playwright/test');

test.describe('Cart', () => {
  test.beforeEach(async ({ page, request }) => {
    // Clear cart via API before each test
    const cartResponse = await request.get('/api/cart');
    const cartItems = await cartResponse.json();
    for (const item of cartItems) {
      await request.delete(`/api/cart/${item.id}`);
    }
    await page.goto('/');
    await page.waitForSelector('[data-testid="product-card"]');
  });

  test('cart is empty initially', async ({ page }) => {
    await expect(page.locator('[data-testid="cart-count"]')).toHaveText('0');
  });

  test('adds product to cart', async ({ page }) => {
    await page.locator('[data-testid="add-to-cart-btn"]').first().click();
    await page.waitForTimeout(300);
    await expect(page.locator('[data-testid="cart-count"]')).toHaveText('1');
  });

  test('opens and closes cart panel', async ({ page }) => {
    await page.click('[data-testid="cart-button"]');
    await expect(page.locator('[data-testid="cart-panel"]')).toHaveClass(/open/);
    await expect(page.locator('[data-testid="cart-overlay"]')).toHaveClass(/open/);
    await page.screenshot({ path: 'test-results/screenshots/cart-panel-open.png' });

    await page.click('[data-testid="close-cart"]');
    await expect(page.locator('[data-testid="cart-panel"]')).not.toHaveClass(/open/);
  });

  test('closes cart via overlay click', async ({ page }) => {
    await page.click('[data-testid="cart-button"]');
    await expect(page.locator('[data-testid="cart-panel"]')).toHaveClass(/open/);
    await page.click('[data-testid="cart-overlay"]');
    await expect(page.locator('[data-testid="cart-panel"]')).not.toHaveClass(/open/);
  });

  test('displays cart item with correct details', async ({ page }) => {
    // Add first product
    await page.locator('[data-testid="add-to-cart-btn"]').first().click();
    await page.waitForTimeout(300);

    // Open cart
    await page.click('[data-testid="cart-button"]');
    await page.waitForTimeout(300);

    const cartItems = page.locator('[data-testid="cart-item"]');
    await expect(cartItems).toHaveCount(1);

    // Cart total should be > 0
    const total = await page.locator('[data-testid="cart-total"]').textContent();
    expect(parseFloat(total)).toBeGreaterThan(0);
  });

  test('adds multiple products to cart', async ({ page }) => {
    const buttons = page.locator('[data-testid="add-to-cart-btn"]');
    await buttons.nth(0).click();
    await page.waitForTimeout(200);
    await buttons.nth(1).click();
    await page.waitForTimeout(200);
    await buttons.nth(2).click();
    await page.waitForTimeout(200);

    await expect(page.locator('[data-testid="cart-count"]')).toHaveText('3');
  });

  test('removes item from cart', async ({ page }) => {
    // Add product
    await page.locator('[data-testid="add-to-cart-btn"]').first().click();
    await page.waitForTimeout(300);

    // Open cart and remove
    await page.click('[data-testid="cart-button"]');
    await page.waitForTimeout(300);
    await page.locator('.cart-item-remove').first().click();
    await page.waitForTimeout(300);

    await expect(page.locator('[data-testid="cart-count"]')).toHaveText('0');
    await expect(page.locator('.empty-cart')).toBeVisible();
  });

  test('empty cart shows message', async ({ page }) => {
    await page.click('[data-testid="cart-button"]');
    await expect(page.locator('.empty-cart')).toBeVisible();
    await expect(page.locator('[data-testid="cart-total"]')).toHaveText('0.00');
  });
});
