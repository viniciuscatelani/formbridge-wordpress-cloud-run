from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import google.auth
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

CHARACTER_HEADERS = [
    "Idempotency Key", "Submission ID", "Submitted At", "Character Name",
    "Player Name", "Class", "Level", "Alignment", "Strength", "STR Mod",
    "Dexterity", "DEX Mod", "Constitution", "CON Mod", "Intelligence",
    "INT Mod", "Wisdom", "WIS Mod", "Charisma", "CHA Mod", "Ability Total",
    "Notes",
]

EVALUATION_HEADERS = [
    "Idempotency Key", "Submission ID", "Submitted At", "Subject", "Evaluator",
    "Final Score", "Maximum Score", "Criteria JSON",
]
LEGACY_CHARACTER_HEADERS = [
    "Submitted at", "Name", "Class", "Level", "Alignment", "Notes"
]


class SheetConfigurationError(RuntimeError):
    """Raised when storage configuration is missing or invalid."""


@dataclass(frozen=True)
class SaveResult:
    created: bool
    submission_id: str


def _credentials() -> Any:
    credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "").strip()
    if credentials_file:
        path = Path(credentials_file)
        if not path.is_file():
            raise SheetConfigurationError(
                f"Google credentials file was not found at '{path}'."
            )
        return Credentials.from_service_account_file(path, scopes=SCOPES)

    credentials, _ = google.auth.default(scopes=SCOPES)
    return credentials


def _service():
    return build(
        "sheets", "v4", credentials=_credentials(), cache_discovery=False
    ).spreadsheets()


def _sheet_id() -> str:
    value = os.getenv("GOOGLE_SHEET_ID", "").strip()
    if not value:
        raise SheetConfigurationError("GOOGLE_SHEET_ID is not configured.")
    return value


def _ensure_worksheet(service, title: str, headers: list[str]) -> int:
    spreadsheet_id = _sheet_id()
    metadata = service.get(spreadsheetId=spreadsheet_id).execute()
    matching = [
        sheet for sheet in metadata.get("sheets", [])
        if sheet["properties"]["title"] == title
    ]

    if matching:
        worksheet_id = matching[0]["properties"]["sheetId"]
    else:
        response = service.batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
        ).execute()
        worksheet_id = response["replies"][0]["addSheet"]["properties"]["sheetId"]

    current = service.values().get(
        spreadsheetId=spreadsheet_id, range=f"'{title}'!1:1"
    ).execute().get("values", [])
    if title == "Characters" and current and current[0] == LEGACY_CHARACTER_HEADERS:
        legacy_rows = service.values().get(
            spreadsheetId=spreadsheet_id, range=f"'{title}'!A2:F"
        ).execute().get("values", [])
        migrated = [headers]
        for index, legacy in enumerate(legacy_rows, start=2):
            padded = legacy + [""] * (6 - len(legacy))
            submitted_at, name, character_class, level, alignment, notes = padded
            migrated.append([
                f"legacy-row-{index}", f"LEGACY-{index:06d}", submitted_at,
                name, "Legacy import", character_class, level, alignment,
                "", "", "", "", "", "", "", "", "", "", "", "", "", notes,
            ])
        service.values().clear(
            spreadsheetId=spreadsheet_id,
            range=f"'{title}'!A:V",
            body={},
        ).execute()
        service.values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{title}'!A1",
            valueInputOption="RAW",
            body={"values": migrated},
        ).execute()
        current = [headers]
    if not current or current[0] != headers:
        service.values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{title}'!A1",
            valueInputOption="RAW",
            body={"values": [headers]},
        ).execute()
        service.batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": worksheet_id,
                                "startRowIndex": 0,
                                "endRowIndex": 1,
                                "startColumnIndex": 0,
                                "endColumnIndex": len(headers),
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "backgroundColor": {"red": .16, "green": .13, "blue": .10},
                                    "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                                }
                            },
                            "fields": "userEnteredFormat",
                        }
                    },
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": worksheet_id,
                                "gridProperties": {"frozenRowCount": 1},
                            },
                            "fields": "gridProperties.frozenRowCount",
                        }
                    },
                ]
            },
        ).execute()
    return worksheet_id


def _ensure_dashboard(service) -> None:
    title = os.getenv("GOOGLE_DASHBOARD_SHEET_NAME", "Dashboard").strip()
    sheet_id = _ensure_worksheet(service, title, ["FormBridge Dashboard"])
    spreadsheet_id = _sheet_id()
    existing = service.values().get(
        spreadsheetId=spreadsheet_id, range=f"'{title}'!A2:B8"
    ).execute().get("values", [])
    if not existing:
        values = [
            ["Metric", "Value"],
            ["Total characters", "=MAX(COUNTA(Characters!B:B)-1,0)"],
            ["Average level", "=IFERROR(AVERAGE(Characters!G2:G),0)"],
            ["Average ability total", "=IFERROR(AVERAGE(Characters!U2:U),0)"],
            ["Total evaluations", "=MAX(COUNTA(Evaluations!B:B)-1,0)"],
            ["Average evaluation score", "=IFERROR(AVERAGE(Evaluations!F2:F),0)"],
            ["Last refreshed", "=NOW()"],
        ]
        service.values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{title}'!A2",
            valueInputOption="USER_ENTERED",
            body={"values": values},
        ).execute()
        service.values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{title}'!D2",
            valueInputOption="USER_ENTERED",
            body={"values": [["Class", "Characters"], ["=QUERY(Characters!F2:F,\"select F,count(F) where F is not null group by F label count(F) ''\",0)"]]},
        ).execute()
    metadata = service.get(spreadsheetId=spreadsheet_id).execute()
    dashboard_sheet = next(
        item for item in metadata.get("sheets", [])
        if item["properties"]["sheetId"] == sheet_id
    )
    requests = [
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 0, "endColumnIndex": 2},
                "cell": {"userEnteredFormat": {"backgroundColor": {"red": .49, "green": .16, "blue": .22}, "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}}},
                "fields": "userEnteredFormat",
            }
        },
        {
            "autoResizeDimensions": {
                "dimensions": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 2}
            }
        },
    ]
    if not dashboard_sheet.get("charts"):
        requests.append({
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Characters by Class",
                        "basicChart": {
                            "chartType": "BAR",
                            "legendPosition": "NO_LEGEND",
                            "axis": [
                                {"position": "BOTTOM_AXIS", "title": "Characters"},
                                {"position": "LEFT_AXIS", "title": "Class"},
                            ],
                            "domains": [{"domain": {"sourceRange": {"sources": [{"sheetId": sheet_id, "startRowIndex": 2, "endRowIndex": 20, "startColumnIndex": 3, "endColumnIndex": 4}]}}}],
                            "series": [{"series": {"sourceRange": {"sources": [{"sheetId": sheet_id, "startRowIndex": 2, "endRowIndex": 20, "startColumnIndex": 4, "endColumnIndex": 5}]}}}],
                            "headerCount": 0,
                        },
                    },
                    "position": {"overlayPosition": {"anchorCell": {"sheetId": sheet_id, "rowIndex": 1, "columnIndex": 6}, "widthPixels": 560, "heightPixels": 320}},
                }
            }
        })
    service.batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()


def _save_google_row(
    worksheet: str,
    headers: list[str],
    row: list[Any],
    idempotency_key: str,
    submission_id: str,
) -> SaveResult:
    service = _service()
    _ensure_worksheet(service, worksheet, headers)
    _ensure_worksheet(service, "Characters", CHARACTER_HEADERS)
    _ensure_worksheet(service, "Evaluations", EVALUATION_HEADERS)
    _ensure_dashboard(service)

    spreadsheet_id = _sheet_id()
    existing = service.values().get(
        spreadsheetId=spreadsheet_id, range=f"'{worksheet}'!A2:B"
    ).execute().get("values", [])
    for saved in existing:
        if saved and saved[0] == idempotency_key:
            return SaveResult(False, saved[1] if len(saved) > 1 else submission_id)

    service.values().append(
        spreadsheetId=spreadsheet_id,
        range=f"'{worksheet}'!A:{chr(64 + min(len(headers), 26))}",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()
    return SaveResult(True, submission_id)


def _save_csv_row(
    worksheet: str,
    headers: list[str],
    row: list[Any],
    idempotency_key: str,
    submission_id: str,
) -> SaveResult:
    base = Path(os.getenv("LOCAL_CSV_DIR", "local-data"))
    path = base / f"{worksheet.lower()}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[list[str]] = []
    if path.exists():
        with path.open(newline="", encoding="utf-8") as handle:
            existing = list(csv.reader(handle))
        for saved in existing[1:]:
            if saved and saved[0] == idempotency_key:
                return SaveResult(False, saved[1] if len(saved) > 1 else submission_id)

    needs_header = not existing
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if needs_header:
            writer.writerow(headers)
        writer.writerow(row)
    return SaveResult(True, submission_id)


def save_record(
    worksheet: str,
    headers: list[str],
    row: list[Any],
    idempotency_key: str,
    submission_id: str,
) -> SaveResult:
    backend = os.getenv("STORAGE_BACKEND", "google_sheets").strip().lower()
    if backend == "csv":
        return _save_csv_row(
            worksheet, headers, row, idempotency_key, submission_id
        )
    if backend == "google_sheets":
        return _save_google_row(
            worksheet, headers, row, idempotency_key, submission_id
        )
    raise SheetConfigurationError(
        "STORAGE_BACKEND must be either 'csv' or 'google_sheets'."
    )
