from __future__ import annotations

import os
import csv
from pathlib import Path

import google.auth
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class SheetConfigurationError(RuntimeError):
    """Raised when Google Sheets configuration is missing or invalid."""


HEADERS = ["Submitted at", "Name", "Class", "Level", "Alignment", "Notes"]


def append_local_csv(values: list[str]) -> None:
    """Append a row to a CSV file for credential-free local testing."""
    csv_path = Path(os.getenv("LOCAL_CSV_FILE", "local-data/characters.csv"))
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not csv_path.exists() or csv_path.stat().st_size == 0

    with csv_path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        if needs_header:
            writer.writerow(HEADERS)
        writer.writerow(values)


def save_character(values: list[str]) -> None:
    backend = os.getenv("STORAGE_BACKEND", "google_sheets").strip().lower()

    if backend == "csv":
        append_local_csv(values)
        return
    if backend == "google_sheets":
        append_character(values)
        return

    raise SheetConfigurationError(
        "STORAGE_BACKEND must be either 'csv' or 'google_sheets'."
    )


def append_character(values: list[str]) -> None:
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()
    sheet_name = os.getenv("GOOGLE_SHEET_NAME", "Characters").strip()
    credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "").strip()

    if not sheet_id:
        raise SheetConfigurationError("GOOGLE_SHEET_ID is not configured.")

    if credentials_file:
        credentials_path = Path(credentials_file)
        if not credentials_path.is_file():
            raise SheetConfigurationError(
                f"Google credentials file was not found at '{credentials_path}'."
            )
        credentials = Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES
        )
    else:
        # Cloud Run supplies Application Default Credentials from the service
        # account assigned to the running service. No JSON key is needed.
        credentials, _ = google.auth.default(scopes=SCOPES)

    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"'{sheet_name}'!A:F",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [values]},
    ).execute()
