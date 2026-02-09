def test_cart_empty_initially(client):
    res = client.get("/api/cart")
    assert res.status_code == 200
    assert res.json() == []


def test_add_to_cart(client):
    res = client.post("/api/cart", json={"product_id": 1})
    assert res.status_code == 200
    item = res.json()
    assert item["product_id"] == 1
    assert item["quantity"] == 1


def test_add_to_cart_with_quantity(client):
    res = client.post("/api/cart", json={"product_id": 1, "quantity": 3})
    assert res.status_code == 200
    item = res.json()
    assert item["quantity"] == 3


def test_add_to_cart_increments_quantity(client):
    client.post("/api/cart", json={"product_id": 1, "quantity": 2})
    res = client.post("/api/cart", json={"product_id": 1, "quantity": 3})
    assert res.status_code == 200
    item = res.json()
    assert item["quantity"] == 5


def test_add_to_cart_nonexistent_product(client):
    res = client.post("/api/cart", json={"product_id": 9999})
    assert res.status_code == 404


def test_remove_from_cart(client):
    add_res = client.post("/api/cart", json={"product_id": 1})
    cart_id = add_res.json()["id"]

    res = client.delete(f"/api/cart/{cart_id}")
    assert res.status_code == 200

    cart = client.get("/api/cart").json()
    assert len(cart) == 0


def test_remove_from_cart_not_found(client):
    res = client.delete("/api/cart/9999")
    assert res.status_code == 404


def test_cart_multiple_products(client):
    client.post("/api/cart", json={"product_id": 1})
    client.post("/api/cart", json={"product_id": 2})
    client.post("/api/cart", json={"product_id": 3})

    cart = client.get("/api/cart").json()
    assert len(cart) == 3
    product_ids = {item["product_id"] for item in cart}
    assert product_ids == {1, 2, 3}
