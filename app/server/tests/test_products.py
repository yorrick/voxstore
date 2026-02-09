from core.db import SEED_PRODUCTS


def test_list_all_products(client):
    res = client.get("/api/products")
    assert res.status_code == 200
    products = res.json()
    assert len(products) == len(SEED_PRODUCTS)


def test_list_products_by_category(client):
    res = client.get("/api/products?category=Electronics")
    assert res.status_code == 200
    products = res.json()
    assert len(products) > 0
    assert all(p["category"] == "Electronics" for p in products)


def test_list_products_by_price_range(client):
    res = client.get("/api/products?min_price=20&max_price=50")
    assert res.status_code == 200
    products = res.json()
    assert len(products) > 0
    assert all(20 <= p["price"] <= 50 for p in products)


def test_list_products_sort_price_asc(client):
    res = client.get("/api/products?sort=price_asc")
    assert res.status_code == 200
    products = res.json()
    prices = [p["price"] for p in products]
    assert prices == sorted(prices)


def test_list_products_sort_price_desc(client):
    res = client.get("/api/products?sort=price_desc")
    assert res.status_code == 200
    products = res.json()
    prices = [p["price"] for p in products]
    assert prices == sorted(prices, reverse=True)


def test_list_products_sort_rating(client):
    res = client.get("/api/products?sort=rating")
    assert res.status_code == 200
    products = res.json()
    ratings = [p["rating"] for p in products]
    assert ratings == sorted(ratings, reverse=True)


def test_get_product_by_id(client):
    res = client.get("/api/products/1")
    assert res.status_code == 200
    product = res.json()
    assert product["id"] == 1
    assert product["name"] == SEED_PRODUCTS[0][0]


def test_get_product_not_found(client):
    res = client.get("/api/products/9999")
    assert res.status_code == 404


def test_combined_filters(client):
    res = client.get("/api/products?category=Electronics&max_price=100&sort=price_asc")
    assert res.status_code == 200
    products = res.json()
    assert all(p["category"] == "Electronics" and p["price"] <= 100 for p in products)
    prices = [p["price"] for p in products]
    assert prices == sorted(prices)
