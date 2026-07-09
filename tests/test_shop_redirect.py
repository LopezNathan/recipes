"""The /shop endpoint redirects grocery shop links to store search pages.

Shop links go through our own domain (then a server-side 302) so iOS never
treats them as universal links and hands them to a store app that drops the
search term. Only whitelisted store ids are redirectable — the endpoint must
never act as an open redirect.
"""


def test_shop_redirects_to_freshdirect(client):
    resp = client.get(
        "/shop", params={"store": "freshdirect", "q": "milk"}, follow_redirects=False
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://www.freshdirect.com/search?search=milk"


def test_shop_redirects_to_heb(client):
    resp = client.get(
        "/shop", params={"store": "heb", "q": "olive oil"}, follow_redirects=False
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://www.heb.com/search?q=olive%20oil"


def test_shop_encodes_term_so_it_cannot_alter_the_url(client):
    resp = client.get(
        "/shop",
        params={"store": "heb", "q": "a/b&x=1#frag"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://www.heb.com/search?q=a/b%26x%3D1%23frag"


def test_shop_rejects_unknown_store(client):
    resp = client.get(
        "/shop",
        params={"store": "https://evil.example", "q": "milk"},
        follow_redirects=False,
    )
    assert resp.status_code == 404


def test_shop_rejects_empty_term(client):
    resp = client.get("/shop", params={"store": "heb", "q": ""}, follow_redirects=False)
    assert resp.status_code == 422


def test_shop_available_on_public_app(public_client):
    resp = public_client.get(
        "/shop", params={"store": "freshdirect", "q": "eggs"}, follow_redirects=False
    )
    assert resp.status_code == 302
