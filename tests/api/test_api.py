

def test_produit_detail_et_404(client):
    assert client.get("/products/mug").status_code == 200
    assert client.get("/products/inconnu").status_code == 404


def test_cart_quote_nominal_et_erreurs(client):
    ok = client.post("/cart/quote", json={"items": [{"product_id": "mug", "qty": 2}], "coupon": "WELCOME10"})
    assert ok.status_code == 200
    assert ok.json()["total"] == "27.40"

    assert client.post("/cart/quote", json={"items": [{"product_id": "inconnu", "qty": 1}]}).status_code == 404
    assert client.post("/cart/quote", json={"items": [{"product_id": "mug", "qty": 1}], "coupon": "NOEL"}).status_code == 422
