from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
import os
import secrets

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from app.sheets import SheetConfigurationError, save_character


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="D&D Character Registry", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class CharacterSubmission(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    character_class: str = Field(min_length=1, max_length=40)
    level: int = Field(ge=1, le=20)
    alignment: str = Field(min_length=1, max_length=40)
    notes: str = Field(default="", max_length=500)

    @field_validator("name", "character_class", "alignment", "notes")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/characters", status_code=201)
def create_character(
    character: CharacterSubmission,
    x_integration_secret: str = Header(default=""),
) -> dict[str, str]:
    expected_secret = os.getenv("WORDPRESS_INTEGRATION_SECRET", "")
    if expected_secret and not secrets.compare_digest(
        x_integration_secret, expected_secret
    ):
        raise HTTPException(status_code=401, detail="Unauthorized submission.")

    submitted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    row = [
        submitted_at,
        character.name,
        character.character_class,
        str(character.level),
        character.alignment,
        character.notes,
    ]

    try:
        save_character(row)
    except SheetConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        # Avoid exposing credentials or Google API internals to the browser.
        print(f"Google Sheets append failed: {exc}")
        raise HTTPException(
            status_code=502,
            detail="Could not save the character to Google Sheets.",
        ) from exc

    return {"message": f"{character.name} was added to the guild registry!"}
