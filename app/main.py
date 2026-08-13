from __future__ import annotations

import json
import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from app.sheets import (
    CHARACTER_HEADERS,
    EVALUATION_HEADERS,
    SheetConfigurationError,
    save_record,
)


load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="FormBridge API", version="2.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


class AbilityScores(BaseModel):
    strength: int = Field(ge=1, le=20)
    dexterity: int = Field(ge=1, le=20)
    constitution: int = Field(ge=1, le=20)
    intelligence: int = Field(ge=1, le=20)
    wisdom: int = Field(ge=1, le=20)
    charisma: int = Field(ge=1, le=20)


class CharacterSubmission(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    player_name: str = Field(default="Anonymous", min_length=1, max_length=80)
    character_class: str = Field(min_length=1, max_length=40)
    level: int = Field(ge=1, le=20)
    alignment: str = Field(min_length=1, max_length=40)
    abilities: AbilityScores = Field(default_factory=lambda: AbilityScores(
        strength=10, dexterity=10, constitution=10,
        intelligence=10, wisdom=10, charisma=10,
    ))
    notes: str = Field(default="", max_length=500)

    @field_validator("name", "player_name", "character_class", "alignment", "notes")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()


class RubricCriterion(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    score: float = Field(ge=0)
    weight: float = Field(gt=0, le=1)
    maximum_score: float = Field(default=5, gt=0)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def score_within_maximum(self):
        if self.score > self.maximum_score:
            raise ValueError("score cannot exceed maximum_score")
        return self


class EvaluationSubmission(BaseModel):
    subject: str = Field(min_length=1, max_length=150)
    evaluator: str = Field(min_length=1, max_length=100)
    criteria: list[RubricCriterion] = Field(min_length=1, max_length=20)

    @field_validator("subject", "evaluator")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def weights_total_one(self):
        if abs(sum(item.weight for item in self.criteria) - 1) > 0.0001:
            raise ValueError("criterion weights must total 1.0")
        names = [item.name.casefold() for item in self.criteria]
        if len(names) != len(set(names)):
            raise ValueError("criterion names must be unique")
        return self


def _authorize(secret: str) -> None:
    expected = os.getenv("WORDPRESS_INTEGRATION_SECRET", "")
    if expected and not secrets.compare_digest(secret, expected):
        raise HTTPException(status_code=401, detail="Unauthorized submission.")


def _identifiers(idempotency_key: str) -> tuple[str, str]:
    key = idempotency_key.strip() or str(uuid.uuid4())
    if len(key) > 128:
        raise HTTPException(status_code=400, detail="Invalid idempotency key.")
    submission_id = f"FB-{uuid.uuid5(uuid.NAMESPACE_URL, key).hex[:12].upper()}"
    return key, submission_id


def _save(*args, **kwargs):
    try:
        return save_record(*args, **kwargs)
    except SheetConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        print(f"Storage write failed: {type(exc).__name__}")
        raise HTTPException(status_code=502, detail="Could not save the submission.") from exc


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}


@app.post("/api/characters", status_code=201)
def create_character(
    character: CharacterSubmission,
    x_integration_secret: str = Header(default=""),
    x_idempotency_key: str = Header(default=""),
) -> dict:
    _authorize(x_integration_secret)
    key, submission_id = _identifiers(x_idempotency_key)
    submitted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    scores = character.abilities.model_dump()
    mods = {name: ability_modifier(score) for name, score in scores.items()}
    row = [
        key, submission_id, submitted_at, character.name, character.player_name,
        character.character_class, character.level, character.alignment,
        scores["strength"], mods["strength"], scores["dexterity"], mods["dexterity"],
        scores["constitution"], mods["constitution"], scores["intelligence"], mods["intelligence"],
        scores["wisdom"], mods["wisdom"], scores["charisma"], mods["charisma"],
        sum(scores.values()), character.notes,
    ]
    result = _save("Characters", CHARACTER_HEADERS, row, key, submission_id)
    return {
        "message": (
            f"{character.name} was added to the guild registry!"
            if result.created else "This character submission was already recorded."
        ),
        "submission_id": result.submission_id,
        "duplicate": not result.created,
        "ability_modifiers": mods,
        "ability_total": sum(scores.values()),
    }


@app.post("/api/evaluations", status_code=201)
def create_evaluation(
    evaluation: EvaluationSubmission,
    x_integration_secret: str = Header(default=""),
    x_idempotency_key: str = Header(default=""),
) -> dict:
    _authorize(x_integration_secret)
    key, submission_id = _identifiers(x_idempotency_key)
    submitted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    normalized = sum(
        (item.score / item.maximum_score) * item.weight
        for item in evaluation.criteria
    )
    maximum_score = max(item.maximum_score for item in evaluation.criteria)
    final_score = round(normalized * maximum_score, 2)
    criteria_json = json.dumps(
        [item.model_dump() for item in evaluation.criteria], ensure_ascii=False
    )
    row = [
        key, submission_id, submitted_at, evaluation.subject, evaluation.evaluator,
        final_score, maximum_score, criteria_json,
    ]
    result = _save("Evaluations", EVALUATION_HEADERS, row, key, submission_id)
    return {
        "message": (
            "Evaluation recorded successfully."
            if result.created else "This evaluation was already recorded."
        ),
        "submission_id": result.submission_id,
        "duplicate": not result.created,
        "final_score": final_score,
        "maximum_score": maximum_score,
    }
