"""Tests for the /health liveness and /health/ready readiness endpoints."""


def test_health_on_private_app(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_on_public_app(public_client):
    resp = public_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ready_on_private_app(client):
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready"}


def test_ready_on_public_app(public_client):
    resp = public_client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready"}


def test_ready_returns_503_when_db_unreachable(client, monkeypatch):
    async def broken_pool():
        raise ConnectionError("db down")

    monkeypatch.setattr("main.get_pool", broken_pool)

    resp = client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json() == {"detail": "Database unavailable"}


def test_health_still_ok_when_db_unreachable(client, monkeypatch):
    async def broken_pool():
        raise ConnectionError("db down")

    monkeypatch.setattr("main.get_pool", broken_pool)

    resp = client.get("/health")
    assert resp.status_code == 200
