# FormBridge

A portfolio-ready integration project that embeds a custom form in WordPress, relays
submissions through server-side PHP to a FastAPI service on Google Cloud Run,
and stores validated records in Google Sheets.

The included demo is a D&D Guild Registry, but its architecture is
designed for real form-to-spreadsheet workflows such as applications, contest
rubrics, internal evaluations, surveys, and lead capture.

> **Demo:** D&D character registration  
> **Reusable core:** WordPress -> secure Python API -> Google Sheets

## Current release

- WordPress plugin: `2.0.1`
- FastAPI: `2.0.0`
- Automated tests: `10 passing`
- GitHub Actions: passing on `main`
- Cloud Run v2: deployed and verified against Google Sheets

## What this project demonstrates

- Custom WordPress plugin development with a shortcode-based form
- Browser-to-WordPress submission through the WordPress REST API
- Secure server-to-server communication between WordPress and FastAPI
- Pydantic validation and structured API errors
- Server-calculated D&D ability modifiers and ability totals
- Stable submission IDs and idempotent retry protection
- A reusable weighted-rubric API for evaluations and contests
- Google Sheets writes through a dedicated service account
- Automatic `Characters`, `Evaluations`, and `Dashboard` sheet setup
- Formula-driven KPIs and a class-distribution chart
- Keyless Google authentication on Cloud Run
- Secret Manager integration
- Docker Compose development with WordPress and MariaDB
- Automated API tests
- GitHub Actions continuous integration
- A swappable local CSV storage backend

## Architecture

```text
Browser
   |
   | form data only
   v
WordPress plugin (PHP)
   |
   | HTTPS + private integration secret
   v
FastAPI on Cloud Run
   |
   | Cloud Run service identity
   v
Google Sheets
```

The Google service-account credentials and WordPress integration secret never
appear in browser JavaScript. Cloud Run uses Application Default Credentials,
so no downloadable Google key is deployed to the cloud service.

## Current D&D example

The example collects:

- Character name
- Class
- Level from 1 to 20
- Alignment
- Optional notes
- Player name
- Six ability scores from 1 to 20

FastAPI calculates each D&D modifier with `floor((score - 10) / 2)`, totals the
ability scores, and returns a stable `FB-...` submission ID. Retrying a request
with the same `X-Idempotency-Key` does not append a second row.

The WordPress form previews every modifier while the character is being built,
using explicit badges such as `Modifier +4` or `Modifier -1`. FastAPI repeats
the calculation server-side so browser values are never trusted as results.

Google Sheets receives:

```text
Idempotency Key | Submission ID | Submitted At | Character | Player | Class
Level | Alignment | STR/DEX/CON/INT/WIS/CHA and modifiers | Ability Total | Notes
```

## Technology

- Python 3.12 and FastAPI
- Google Sheets API
- Google Cloud Run, Secret Manager, Cloud Build, and Artifact Registry
- WordPress plugin using PHP, HTML, CSS, and JavaScript
- MariaDB and Docker Compose for local WordPress development
- Pytest and FastAPI TestClient

## Repository structure

```text
app/                         FastAPI application and storage adapters
static/                      Standalone FastAPI demo form
tests/                       Automated backend tests
.github/workflows/ci.yml     CI pipeline for every push and pull request
wordpress-plugin/
  dnd-character-registry/    Installable WordPress plugin source
Dockerfile                   Cloud Run/API container
compose.yaml                 Local WordPress development stack
DEPLOYMENT.md                Google Sheets and Cloud Run runbook
SECURITY.md                  Security model and production checklist
```

## Quick start: full local WordPress stack

Prerequisites:

- Docker Desktop
- A Google Sheet with a `Characters` tab
- A Google service-account JSON key for local development only

Copy the environment template:

```powershell
Copy-Item .env.example .env
```

Set the spreadsheet ID in `.env`, save the local key as `credentials.json`, and
share the spreadsheet with the key's `client_email` as an editor. Then start:

```powershell
docker compose up -d
```

On a new Docker volume, initialize WordPress once:

```powershell
docker compose run --rm wpcli wp core install --path=/var/www/html --url=http://localhost:8080 --title="Local D&D Guild" --admin_user=localadmin --admin_password="local-dnd-test-only" --admin_email=admin@example.test --skip-email
docker compose run --rm wpcli wp plugin activate dnd-character-registry --path=/var/www/html
docker compose run --rm wpcli wp post create --path=/var/www/html --post_type=page --post_title="Guild Registry" --post_name=guild-registry --post_status=publish --post_content="[dnd_character_registry]"
docker compose run --rm wpcli wp rewrite structure '/%postname%/' --path=/var/www/html
```

Open:

- WordPress form: <http://localhost:8080/guild-registry/>
- WordPress administration: <http://localhost:8080/wp-admin/>
- Local FastAPI documentation: <http://localhost:8000/docs>

The local administrator credentials above are intentionally disposable and must
never be reused in a hosted environment.

Use the WordPress page on port `8080` for submissions. The standalone page on
port `8000` calls the protected API directly and therefore receives HTTP 401;
browser JavaScript intentionally does not contain the integration secret.

Stop the stack while preserving its volumes:

```powershell
docker compose down
```

## Run FastAPI without Docker

Do not use this at the same time as the Docker API because both bind port 8000.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload
```

## Tests

```powershell
python -m pytest -q
```

The suite currently contains 10 tests covering authorization, validation,
ability modifiers, ability totals, weighted scoring, idempotent duplicate
responses, and real CSV duplicate prevention. External Google Sheets writes are
mocked, so tests do not modify the configured spreadsheet.

## Cloud deployment

The tested cloud path is:

```text
Local WordPress -> Cloud Run -> Google Sheets
```

The deployment runbook, including all `gcloud` commands, secret rotation, WordPress
configuration, verification, and cleanup, is in [DEPLOYMENT.md](DEPLOYMENT.md).

## Adapting this project

The API now includes a business-oriented weighted judging route at
`POST /api/evaluations`. Each criterion supplies a score, maximum score, and
weight; weights must total `1.0`. FastAPI normalizes mixed scoring scales and
saves both the final score and auditable criterion JSON.

This is currently an API-only second workflow. Character submissions populate
`Characters`; they do not populate `Evaluations`. The `Evaluations` tab receives
only requests to `POST /api/evaluations`. A dedicated WordPress evaluation form
is a documented future extension.

The `Dashboard` tab summarizes both workflows and currently includes KPI
formulas plus a native characters-by-class chart.

Possible future extensions include race/species, background, proficiencies,
equipment, judge authentication, contest deadlines, or a dedicated rubric UI.

The architecture is already the most valuable part of the project. Expanding
the domain model is worthwhile when it demonstrates additional engineering,
such as conditional validation, derived values, duplicate prevention, tests,
or a useful spreadsheet dashboard—not merely a larger number of text fields.

## Status

- Local WordPress-to-FastAPI integration: verified
- FastAPI-to-Google-Sheets integration: verified
- WordPress-to-Cloud-Run-to-Google-Sheets integration: verified
- Cloud Run secret rejection: verified with HTTP 401
- Automated tests: 10 passing locally and in GitHub Actions
- Idempotent duplicate protection: verified
- Weighted-rubric calculation: verified
- GitHub Actions CI: configured and verified
- WordPress live modifier preview: implemented in plugin `2.0.1`
- Evaluation frontend: not implemented; API and storage are complete
