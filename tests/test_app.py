from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_character_validation() -> None:
    response = client.post(
        "/api/characters",
        json={
            "name": "Test Hero",
            "character_class": "Wizard",
            "level": 21,
            "alignment": "Neutral Good",
            "notes": "",
        },
    )
    assert response.status_code == 422


def test_valid_character_is_written(monkeypatch) -> None:
    monkeypatch.delenv("WORDPRESS_INTEGRATION_SECRET", raising=False)
    captured: list[list[str]] = []
    monkeypatch.setattr("app.main.save_character", captured.append)

    response = client.post(
        "/api/characters",
        json={
            "name": "  Elara Moonshadow  ",
            "character_class": "Wizard",
            "level": 7,
            "alignment": "Neutral Good",
            "notes": "Keeper of the silver key",
        },
    )

    assert response.status_code == 201
    assert response.json()["message"] == "Elara Moonshadow was added to the guild registry!"
    assert len(captured) == 1
    assert captured[0][1:] == [
        "Elara Moonshadow",
        "Wizard",
        "7",
        "Neutral Good",
        "Keeper of the silver key",
    ]


def test_configured_integration_secret_is_required(monkeypatch) -> None:
    monkeypatch.setenv("WORDPRESS_INTEGRATION_SECRET", "test-secret")

    response = client.post(
        "/api/characters",
        json={
            "name": "Elara",
            "character_class": "Wizard",
            "level": 7,
            "alignment": "Neutral Good",
            "notes": "",
        },
    )

    assert response.status_code == 401
