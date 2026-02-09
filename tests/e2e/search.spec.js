const { test, expect } = require('@playwright/test');

test.describe('Search', () => {
  test('searches products by text', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="product-card"]');
    await page.fill('[data-testid="search-input"]', 'headphones');
    await page.waitForTimeout(600); // debounce is 400ms
    const cards = await page.locator('[data-testid="product-card"]').count();
    expect(cards).toBeGreaterThan(0);
    expect(cards).toBeLessThan(26);
    await page.screenshot({ path: 'test-results/screenshots/search-headphones.png', fullPage: true });
  });

  test('shows no results for nonexistent query', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="product-card"]');
    await page.fill('[data-testid="search-input"]', 'xyznonexistent999');
    await page.waitForTimeout(600);
    const cards = await page.locator('[data-testid="product-card"]').count();
    expect(cards).toBe(0);
    await page.screenshot({ path: 'test-results/screenshots/search-no-results.png', fullPage: true });
  });

  test('clearing search restores all products', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="product-card"]');
    await page.fill('[data-testid="search-input"]', 'headphones');
    await page.waitForTimeout(600);
    await page.fill('[data-testid="search-input"]', '');
    await page.waitForTimeout(600);
    const cards = await page.locator('[data-testid="product-card"]').count();
    expect(cards).toBe(26);
  });

  test('search is case insensitive', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="product-card"]');
    await page.fill('[data-testid="search-input"]', 'KEYBOARD');
    await page.waitForTimeout(600);
    const cards = await page.locator('[data-testid="product-card"]').count();
    expect(cards).toBeGreaterThan(0);
  });
});
