from fastapi.testclient import TestClient

from app.main import ability_modifier, app
from app.sheets import SaveResult
from app.sheets import save_record


client = TestClient(app)


CHARACTER = {
    "name": "Elara Moonshadow",
    "player_name": "Vinicius",
    "character_class": "Wizard",
    "level": 7,
    "alignment": "Neutral Good",
    "abilities": {
        "strength": 8,
        "dexterity": 14,
        "constitution": 13,
        "intelligence": 18,
        "wisdom": 12,
        "charisma": 10,
    },
    "notes": "Keeper of the silver key",
}


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "2.0.0"}


def test_ability_modifier_rounds_down() -> None:
    assert ability_modifier(8) == -1
    assert ability_modifier(9) == -1
    assert ability_modifier(10) == 0
    assert ability_modifier(18) == 4


def test_character_validation() -> None:
    invalid = {**CHARACTER, "level": 21}
    response = client.post("/api/characters", json=invalid)
    assert response.status_code == 422


def test_ability_validation() -> None:
    invalid = {**CHARACTER, "abilities": {**CHARACTER["abilities"], "strength": 21}}
    response = client.post("/api/characters", json=invalid)
    assert response.status_code == 422


def test_valid_character_calculates_and_writes(monkeypatch) -> None:
    monkeypatch.delenv("WORDPRESS_INTEGRATION_SECRET", raising=False)
    captured = []

    def fake_save(*args):
        captured.append(args)
        return SaveResult(True, args[-1])

    monkeypatch.setattr("app.main.save_record", fake_save)
    response = client.post(
        "/api/characters",
        json=CHARACTER,
        headers={"X-Idempotency-Key": "character-test-1"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["duplicate"] is False
    assert body["submission_id"].startswith("FB-")
    assert body["ability_modifiers"] == {
        "strength": -1,
        "dexterity": 2,
        "constitution": 1,
        "intelligence": 4,
        "wisdom": 1,
        "charisma": 0,
    }
    assert body["ability_total"] == 75
    assert captured[0][0] == "Characters"


def test_duplicate_character_returns_original_id(monkeypatch) -> None:
    monkeypatch.delenv("WORDPRESS_INTEGRATION_SECRET", raising=False)
    monkeypatch.setattr(
        "app.main.save_record",
        lambda *args: SaveResult(False, "FB-EXISTING123"),
    )
    response = client.post(
        "/api/characters",
        json=CHARACTER,
        headers={"X-Idempotency-Key": "same-retry-key"},
    )
    assert response.status_code == 201
    assert response.json()["duplicate"] is True
    assert response.json()["submission_id"] == "FB-EXISTING123"


def test_weighted_rubric_calculation(monkeypatch) -> None:
    monkeypatch.delenv("WORDPRESS_INTEGRATION_SECRET", raising=False)
    monkeypatch.setattr(
        "app.main.save_record",
        lambda *args: SaveResult(True, args[-1]),
    )
    response = client.post(
        "/api/evaluations",
        headers={"X-Idempotency-Key": "rubric-test-1"},
        json={
            "subject": "Acme Corp",
            "evaluator": "Judge One",
            "criteria": [
                {"name": "Quality", "score": 4, "weight": 0.30, "maximum_score": 5},
                {"name": "Innovation", "score": 3, "weight": 0.25, "maximum_score": 5},
                {"name": "Impact", "score": 5, "weight": 0.45, "maximum_score": 5},
            ],
        },
    )
    assert response.status_code == 201
    assert response.json()["final_score"] == 4.2
    assert response.json()["maximum_score"] == 5


def test_rubric_weights_must_total_one() -> None:
    response = client.post(
        "/api/evaluations",
        json={
            "subject": "Acme Corp",
            "evaluator": "Judge One",
            "criteria": [
                {"name": "Quality", "score": 4, "weight": 0.3},
                {"name": "Impact", "score": 5, "weight": 0.3},
            ],
        },
    )
    assert response.status_code == 422


def test_configured_integration_secret_is_required(monkeypatch) -> None:
    monkeypatch.setenv("WORDPRESS_INTEGRATION_SECRET", "test-secret")
    response = client.post("/api/characters", json=CHARACTER)
    assert response.status_code == 401


def test_csv_storage_prevents_duplicate_rows(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "csv")
    monkeypatch.setenv("LOCAL_CSV_DIR", str(tmp_path))
    headers = ["Idempotency Key", "Submission ID", "Value"]
    row = ["retry-key", "FB-CSVTEST", "first"]

    first = save_record("TestRecords", headers, row, "retry-key", "FB-CSVTEST")
    second = save_record(
        "TestRecords", headers, ["retry-key", "FB-OTHER", "second"],
        "retry-key", "FB-OTHER",
    )

    assert first.created is True
    assert second.created is False
    assert second.submission_id == "FB-CSVTEST"
    assert (tmp_path / "testrecords.csv").read_text(encoding="utf-8").count("retry-key") == 1
