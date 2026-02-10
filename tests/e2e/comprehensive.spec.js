const { test, expect } = require("@playwright/test");

// Run serially to avoid cart shared state conflicts
test.describe.configure({ mode: "serial" });

test.describe("Comprehensive Feature Tests", () => {
    test.beforeEach(async ({ page, request }) => {
        // Clear cart via API before each test
        const cartResponse = await request.get("/api/cart");
        const cartItems = await cartResponse.json();
        for (const item of cartItems) {
            await request.delete(`/api/cart/${item.id}`);
        }
    });

    // ── Initial Page Load ──

    test("homepage loads products without JS errors", async ({ page }) => {
        const jsErrors = [];
        page.on("pageerror", (err) => jsErrors.push(err.message));

        const apiResponses = [];
        page.on("response", (resp) => {
            if (resp.url().includes("/api/")) {
                apiResponses.push({ url: resp.url(), status: resp.status() });
            }
        });

        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]', {
            timeout: 5000,
        });

        const count = await page.locator('[data-testid="product-card"]').count();
        expect(count).toBe(26);

        // All API calls should succeed
        for (const resp of apiResponses) {
            expect(resp.status).toBeLessThan(400);
        }

        // No JS runtime errors
        expect(jsErrors).toEqual([]);
    });

    test("products display correct data fields", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        const firstCard = page.locator('[data-testid="product-card"]').first();

        await expect(firstCard.locator("img")).toBeVisible();
        await expect(firstCard.locator(".product-name")).toBeVisible();
        await expect(firstCard.locator(".product-description")).toBeVisible();
        await expect(firstCard.locator(".product-price")).toBeVisible();
        await expect(firstCard.locator(".product-rating")).toBeVisible();
        await expect(firstCard.locator(".product-category")).toBeVisible();

        const price = await firstCard.locator(".product-price").textContent();
        expect(price).toMatch(/^\$\d+\.\d{2}$/);

        const rating = await firstCard.locator(".product-rating").textContent();
        expect(rating).toMatch(/[★☆]/);
    });

    test("all categories are loaded in filter dropdown", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        const options = await page
            .locator('[data-testid="category-filter"] option')
            .allTextContents();

        expect(options).toContain("All Categories");
        expect(options).toContain("Electronics");
        expect(options).toContain("Clothing");
        expect(options).toContain("Home");
        expect(options).toContain("Books");
        expect(options).toContain("Sports");
        expect(options.length).toBe(6);
    });

    // ── Sorting ──

    test("sort by price ascending shows correct order", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        await page.selectOption('[data-testid="sort-filter"]', "price_asc");

        await expect(async () => {
            const prices = await page.locator(".product-price").allTextContents();
            const nums = prices.map((p) => parseFloat(p.replace("$", "")));
            expect(nums.length).toBe(26);
            expect(nums[0]).toBeLessThanOrEqual(nums[1]);
        }).toPass({ timeout: 3000 });

        const prices = await page.locator(".product-price").allTextContents();
        const nums = prices.map((p) => parseFloat(p.replace("$", "")));
        for (let i = 1; i < nums.length; i++) {
            expect(nums[i]).toBeGreaterThanOrEqual(nums[i - 1]);
        }
    });

    test("sort by price descending shows correct order", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        await page.selectOption('[data-testid="sort-filter"]', "price_desc");

        await expect(async () => {
            const prices = await page.locator(".product-price").allTextContents();
            const nums = prices.map((p) => parseFloat(p.replace("$", "")));
            expect(nums.length).toBe(26);
            expect(nums[0]).toBeGreaterThanOrEqual(nums[1]);
        }).toPass({ timeout: 3000 });

        const prices = await page.locator(".product-price").allTextContents();
        const nums = prices.map((p) => parseFloat(p.replace("$", "")));
        for (let i = 1; i < nums.length; i++) {
            expect(nums[i]).toBeLessThanOrEqual(nums[i - 1]);
        }
    });

    test("sort by rating shows highest rated first", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        await page.selectOption('[data-testid="sort-filter"]', "rating");

        await expect(async () => {
            const ratings = await page.locator(".product-rating").allTextContents();
            const nums = ratings.map((r) => parseFloat(r.split(" ").pop()));
            expect(nums.length).toBe(26);
            expect(nums[0]).toBeGreaterThanOrEqual(nums[1]);
        }).toPass({ timeout: 3000 });

        const ratings = await page.locator(".product-rating").allTextContents();
        const nums = ratings.map((r) => parseFloat(r.split(" ").pop()));
        for (let i = 1; i < nums.length; i++) {
            expect(nums[i]).toBeLessThanOrEqual(nums[i - 1]);
        }
    });

    test("changing sort back to default restores original order", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        const defaultNames = await page.locator(".product-name").allTextContents();

        await page.selectOption('[data-testid="sort-filter"]', "price_asc");

        // Wait for sort to take effect
        await expect(async () => {
            const names = await page.locator(".product-name").allTextContents();
            expect(names[0]).not.toBe(defaultNames[0]);
        }).toPass({ timeout: 3000 });

        await page.selectOption('[data-testid="sort-filter"]', "");

        // Wait for default order to restore
        await expect(async () => {
            const names = await page.locator(".product-name").allTextContents();
            expect(names[0]).toBe(defaultNames[0]);
        }).toPass({ timeout: 3000 });

        const restoredNames = await page.locator(".product-name").allTextContents();
        expect(restoredNames).toEqual(defaultNames);
    });

    // ── Category Filtering ──

    test("filtering by category shows only matching products", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        const categories = ["Electronics", "Clothing", "Home", "Books", "Sports"];

        for (const cat of categories) {
            await page.selectOption('[data-testid="category-filter"]', cat);

            await expect(async () => {
                const count = await page.locator('[data-testid="product-card"]').count();
                expect(count).toBeGreaterThan(0);
                expect(count).toBeLessThan(26);
            }).toPass({ timeout: 3000 });

            const cardCategories = await page.locator(".product-category").allTextContents();
            for (const displayed of cardCategories) {
                expect(displayed.trim().toUpperCase()).toBe(cat.toUpperCase());
            }
        }
    });

    test("selecting 'All Categories' shows all products", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        await page.selectOption('[data-testid="category-filter"]', "Books");

        await expect(async () => {
            const count = await page.locator('[data-testid="product-card"]').count();
            expect(count).toBeLessThan(26);
        }).toPass({ timeout: 3000 });

        await page.selectOption('[data-testid="category-filter"]', "");

        await expect(async () => {
            const count = await page.locator('[data-testid="product-card"]').count();
            expect(count).toBe(26);
        }).toPass({ timeout: 3000 });
    });

    // ── Combined Sort + Filter ──

    test("sort works within a filtered category", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        await page.selectOption('[data-testid="category-filter"]', "Electronics");

        await expect(async () => {
            const cats = await page.locator(".product-category").allTextContents();
            expect(cats.length).toBeGreaterThan(0);
            expect(cats.length).toBeLessThan(26);
        }).toPass({ timeout: 3000 });

        await page.selectOption('[data-testid="sort-filter"]', "price_asc");

        await expect(async () => {
            const prices = await page.locator(".product-price").allTextContents();
            const nums = prices.map((p) => parseFloat(p.replace("$", "")));
            expect(nums.length).toBeGreaterThan(1);
            expect(nums[0]).toBeLessThanOrEqual(nums[1]);
        }).toPass({ timeout: 3000 });

        const prices = await page.locator(".product-price").allTextContents();
        const nums = prices.map((p) => parseFloat(p.replace("$", "")));
        for (let i = 1; i < nums.length; i++) {
            expect(nums[i]).toBeGreaterThanOrEqual(nums[i - 1]);
        }

        const categories = await page.locator(".product-category").allTextContents();
        for (const cat of categories) {
            expect(cat.trim().toUpperCase()).toBe("ELECTRONICS");
        }
    });

    // ── Search ──

    test("search returns relevant results", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        await page.fill('[data-testid="search-input"]', "headphones");

        await expect(async () => {
            const count = await page.locator('[data-testid="product-card"]').count();
            expect(count).toBeGreaterThan(0);
            expect(count).toBeLessThan(26);
        }).toPass({ timeout: 10000 });

        const names = await page.locator(".product-name").allTextContents();
        const descriptions = await page.locator(".product-description").allTextContents();
        const allText = [...names, ...descriptions].join(" ").toLowerCase();
        expect(allText).toContain("headphones");
    });

    test("search for nonexistent product shows empty state", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        await page.fill('[data-testid="search-input"]', "xyznonexistent999");

        await expect(page.locator('[data-testid="products-grid"]')).toContainText(
            "No products found",
            { timeout: 10000 },
        );

        const count = await page.locator('[data-testid="product-card"]').count();
        expect(count).toBe(0);
    });

    test("clearing search restores all products", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        await page.fill('[data-testid="search-input"]', "headphones");

        await expect(async () => {
            const count = await page.locator('[data-testid="product-card"]').count();
            expect(count).toBeLessThan(26);
        }).toPass({ timeout: 10000 });

        await page.fill('[data-testid="search-input"]', "");

        await expect(async () => {
            const count = await page.locator('[data-testid="product-card"]').count();
            expect(count).toBe(26);
        }).toPass({ timeout: 10000 });
    });

    test("search is case insensitive", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        await page.fill('[data-testid="search-input"]', "KEYBOARD");

        await expect(async () => {
            const count = await page.locator('[data-testid="product-card"]').count();
            expect(count).toBeGreaterThan(0);
        }).toPass({ timeout: 3000 });
    });

    // ── Cart ──

    test("add to cart updates count badge", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        await expect(page.locator('[data-testid="cart-count"]')).toHaveText("0");

        await page.locator('[data-testid="add-to-cart-btn"]').first().click();

        await expect(page.locator('[data-testid="cart-count"]')).toHaveText("1", {
            timeout: 3000,
        });
    });

    test("cart shows correct item and total", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        const firstPrice = await page.locator(".product-price").first().textContent();
        const expectedPrice = parseFloat(firstPrice.replace("$", ""));

        await page.locator('[data-testid="add-to-cart-btn"]').first().click();

        await expect(page.locator('[data-testid="cart-count"]')).toHaveText("1", {
            timeout: 3000,
        });

        await page.click('[data-testid="cart-button"]');
        await expect(page.locator('[data-testid="cart-panel"]')).toHaveClass(/open/);

        await expect(page.locator('[data-testid="cart-item"]')).toHaveCount(1);

        const total = await page.locator('[data-testid="cart-total"]').textContent();
        expect(parseFloat(total)).toBeCloseTo(expectedPrice, 2);
    });

    test("adding same product twice increases quantity", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        const firstPrice = await page.locator(".product-price").first().textContent();
        const price = parseFloat(firstPrice.replace("$", ""));

        await page.locator('[data-testid="add-to-cart-btn"]').first().click();
        await expect(page.locator('[data-testid="cart-count"]')).toHaveText("1", {
            timeout: 3000,
        });

        await page.locator('[data-testid="add-to-cart-btn"]').first().click();
        await expect(page.locator('[data-testid="cart-count"]')).toHaveText("2", {
            timeout: 3000,
        });

        await page.click('[data-testid="cart-button"]');
        await expect(page.locator('[data-testid="cart-item"]')).toHaveCount(1);

        const total = await page.locator('[data-testid="cart-total"]').textContent();
        expect(parseFloat(total)).toBeCloseTo(price * 2, 2);
    });

    test("adds multiple different products to cart", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

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

    test("remove item from cart", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

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
        await expect(page.locator('[data-testid="cart-total"]')).toHaveText("0.00");
    });

    test("out of stock products have disabled add button", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        const outOfStockCards = page
            .locator('[data-testid="product-card"]')
            .filter({ hasText: "Out of Stock" });
        const count = await outOfStockCards.count();
        expect(count).toBeGreaterThan(0);

        const btn = outOfStockCards.first().locator('[data-testid="add-to-cart-btn"]');
        await expect(btn).toBeDisabled();
        await expect(btn).toHaveText("Unavailable");
    });

    // ── Cart Panel Open/Close ──

    test("cart opens and closes via X button", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        await page.click('[data-testid="cart-button"]');
        await expect(page.locator('[data-testid="cart-panel"]')).toHaveClass(/open/);
        await expect(page.locator('[data-testid="cart-overlay"]')).toHaveClass(/open/);

        await page.click('[data-testid="close-cart"]');
        await expect(page.locator('[data-testid="cart-panel"]')).not.toHaveClass(/open/);
    });

    test("cart closes via overlay click", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        await page.click('[data-testid="cart-button"]');
        await expect(page.locator('[data-testid="cart-panel"]')).toHaveClass(/open/);

        await page.click('[data-testid="cart-overlay"]');
        await expect(page.locator('[data-testid="cart-panel"]')).not.toHaveClass(/open/);
    });

    test("empty cart shows message", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        await page.click('[data-testid="cart-button"]');
        await expect(page.locator(".empty-cart")).toBeVisible();
        await expect(page.locator('[data-testid="cart-total"]')).toHaveText("0.00");
    });

    // ── API Direct Tests ──

    test("API returns correct product structure", async ({ request }) => {
        const resp = await request.get("/api/products");
        expect(resp.status()).toBe(200);
        const products = await resp.json();
        expect(Array.isArray(products)).toBe(true);
        expect(products.length).toBe(26);

        const p = products[0];
        expect(p).toHaveProperty("id");
        expect(p).toHaveProperty("name");
        expect(p).toHaveProperty("description");
        expect(p).toHaveProperty("price");
        expect(p).toHaveProperty("category");
        expect(p).toHaveProperty("image_url");
        expect(p).toHaveProperty("in_stock");
        expect(p).toHaveProperty("rating");
    });

    test("API sorting works correctly", async ({ request }) => {
        const ascResp = await request.get("/api/products?sort=price_asc");
        const asc = await ascResp.json();
        for (let i = 1; i < asc.length; i++) {
            expect(asc[i].price).toBeGreaterThanOrEqual(asc[i - 1].price);
        }

        const descResp = await request.get("/api/products?sort=price_desc");
        const desc = await descResp.json();
        for (let i = 1; i < desc.length; i++) {
            expect(desc[i].price).toBeLessThanOrEqual(desc[i - 1].price);
        }

        const ratingResp = await request.get("/api/products?sort=rating");
        const rated = await ratingResp.json();
        for (let i = 1; i < rated.length; i++) {
            expect(rated[i].rating).toBeLessThanOrEqual(rated[i - 1].rating);
        }
    });

    test("API category filtering works correctly", async ({ request }) => {
        const resp = await request.get("/api/products?category=Electronics");
        expect(resp.status()).toBe(200);
        const products = await resp.json();
        expect(products.length).toBeGreaterThan(0);
        for (const p of products) {
            expect(p.category).toBe("Electronics");
        }
    });

    test("API search returns expected results", async ({ request }) => {
        const resp = await request.get("/api/search?q=headphones");
        expect(resp.status()).toBe(200);
        const data = await resp.json();
        expect(data.products.length).toBeGreaterThan(0);
        expect(data.query).toBe("headphones");
        expect(data.total).toBe(data.products.length);
    });

    // ── Rapid Interactions ──

    test("rapid sort changes settle correctly", async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector('[data-testid="product-card"]');

        await page.selectOption('[data-testid="sort-filter"]', "price_asc");
        await page.selectOption('[data-testid="sort-filter"]', "price_desc");
        await page.selectOption('[data-testid="sort-filter"]', "rating");
        await page.selectOption('[data-testid="sort-filter"]', "");

        // Wait for final state to settle
        await expect(async () => {
            const count = await page.locator('[data-testid="product-card"]').count();
            expect(count).toBe(26);
        }).toPass({ timeout: 3000 });
    });

    // ── Fresh Page Load ──

    test("products load on fresh navigation", async ({ page }) => {
        await page.context().clearCookies();

        const jsErrors = [];
        page.on("pageerror", (err) => jsErrors.push(err.message));

        await page.goto("/", { waitUntil: "networkidle" });
        await page.waitForSelector('[data-testid="product-card"]', {
            timeout: 5000,
        });

        const count = await page.locator('[data-testid="product-card"]').count();
        expect(count).toBe(26);
        expect(jsErrors).toEqual([]);
    });
});
