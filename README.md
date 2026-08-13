# FormBridge

A portfolio-ready integration project that embeds a custom form in WordPress, relays
submissions through server-side PHP to a FastAPI service on Google Cloud Run,
and stores validated records in Google Sheets.

The included demo is a D&D Guild Registry, but its architecture is
designed for real form-to-spreadsheet workflows such as applications, contest
rubrics, internal evaluations, surveys, and lead capture.

> **Demo:** D&D character registration  
> **Reusable core:** WordPress → secure Python API → Google Sheets

## What this project demonstrates

- Custom WordPress plugin development with a shortcode-based form
- Browser-to-WordPress submission through the WordPress REST API
- Secure server-to-server communication between WordPress and FastAPI
- Pydantic validation and structured API errors
- Google Sheets writes through a dedicated service account
- Keyless Google authentication on Cloud Run
- Secret Manager integration
- Docker Compose development with WordPress and MariaDB
- Automated API tests
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

Google Sheets receives:

```text
Submitted at | Name | Class | Level | Alignment | Notes
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
- FastAPI documentation: <http://localhost:8000/docs>

The local administrator credentials above are intentionally disposable and must
never be reused in a hosted environment.

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

The successful submission path is mocked in the automated suite, so tests do
not write rows to Google Sheets.

## Cloud deployment

The tested cloud path is:

```text
Local WordPress -> Cloud Run -> Google Sheets
```

The deployment runbook, including all `gcloud` commands, secret rotation, WordPress
configuration, verification, and cleanup, is in [DEPLOYMENT.md](DEPLOYMENT.md).

## Adapting this project

The current character form is intentionally simple. A stronger portfolio
version could add ability scores, race/species, background, proficiencies,
equipment, or calculated modifiers. A more business-oriented evolution would
replace the D&D model with a weighted judging rubric and calculate a final score
in FastAPI before saving both raw ratings and results.

The architecture is already the most valuable part of the project. Expanding
the domain model is worthwhile when it demonstrates additional engineering,
such as conditional validation, derived values, duplicate prevention, tests,
or a useful spreadsheet dashboard—not merely a larger number of text fields.

## Status

- Local WordPress-to-FastAPI integration: verified
- FastAPI-to-Google-Sheets integration: verified
- WordPress-to-Cloud-Run-to-Google-Sheets integration: verified
- Cloud Run secret rejection: verified with HTTP 401
- Automated tests: passing
