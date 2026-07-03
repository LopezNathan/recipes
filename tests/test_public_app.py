"""The public app is read-only: write routes must not be reachable.

This guards the key invariant of the dual-API design — public_app shares
the read routes but never registers the write routes, so mutating requests
are rejected by routing (405 for methods on an existing read path, 404 for
paths that only exist on private_app).
"""

RECIPE = {
    "name": "Pasta",
    "recipeIngredient": ["400g pasta"],
    "recipeInstructions": "Boil and serve",
}


def test_public_app_mode_is_public(public_client):
    assert public_client.get("/app-mode").json() == {"mode": "public"}


def test_public_app_can_read(public_client):
    resp = public_client.get("/recipes")
    assert resp.status_code == 200


def test_public_app_rejects_create(public_client):
    # /recipes exists (GET), so POST is Method Not Allowed
    assert public_client.post("/recipes", json=RECIPE).status_code == 405


def test_public_app_rejects_update(public_client):
    assert public_client.put("/recipes/1", json=RECIPE).status_code == 405


def test_public_app_rejects_delete(public_client):
    assert public_client.delete("/recipes/1").status_code == 405


def test_public_app_hides_import_route(public_client):
    # /import only exists on private_app → the path is unknown here
    assert public_client.post("/import", json={"url": "https://example.com"}).status_code == 404


def test_public_app_hides_paste_route(public_client):
    assert public_client.post("/paste", json={"content": "# Recipe"}).status_code == 404


def test_private_app_mode_is_private(client):
    assert client.get("/app-mode").json() == {"mode": "private"}
