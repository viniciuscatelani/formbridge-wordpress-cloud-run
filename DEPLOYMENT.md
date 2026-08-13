# Deployment guide

This runbook deploys the FastAPI backend to Google Cloud Run and connects either
a local or hosted WordPress installation to it.

Replace every uppercase placeholder with your own value. Never commit `.env`,
`credentials.json`, or integration secrets.

## 1. Select a Google Cloud project

```powershell
gcloud auth login
gcloud projects list
gcloud config set project YOUR_PROJECT_ID
gcloud config get-value project
```

Cloud Run requires billing to be linked, even for workloads inside the free
tier:

```powershell
gcloud billing projects describe YOUR_PROJECT_ID
```

Confirm that it reports `billingEnabled: true`.

## 2. Enable APIs

```powershell
gcloud services enable `
  run.googleapis.com `
  cloudbuild.googleapis.com `
  artifactregistry.googleapis.com `
  sheets.googleapis.com `
  secretmanager.googleapis.com
```

## 3. Create the runtime service account

```powershell
gcloud iam service-accounts create dnd-api `
  --display-name="DnD API"
```

The address has this format:

```text
dnd-api@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

Share the target Google Sheet with that address as an editor. No JSON key is
created for Cloud Run.

## 4. Create the WordPress integration secret

The following works with older Windows PowerShell versions and does not print
the generated value:

```powershell
$bytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$rng.Dispose()
$secret = [Convert]::ToBase64String($bytes)

$tempSecretFile = Join-Path $env:TEMP "dnd-secret-$([Guid]::NewGuid()).txt"
[System.IO.File]::WriteAllText(
  $tempSecretFile,
  $secret,
  (New-Object System.Text.UTF8Encoding($false))
)

gcloud secrets create wordpress-integration-secret `
  --data-file=$tempSecretFile

Remove-Item -LiteralPath $tempSecretFile -Force
```

Writing without a trailing newline matters because the backend compares the
secret exactly.

Allow only the runtime identity to access this secret:

```powershell
gcloud secrets add-iam-policy-binding wordpress-integration-secret `
  --member="serviceAccount:dnd-api@YOUR_PROJECT_ID.iam.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"
```

## 5. Deploy Cloud Run

Load the spreadsheet configuration from the local `.env` file:

```powershell
$sheetId = (
  Get-Content .env |
  Where-Object { $_ -match '^GOOGLE_SHEET_ID=' }
) -replace '^GOOGLE_SHEET_ID=', ''

$sheetName = (
  Get-Content .env |
  Where-Object { $_ -match '^GOOGLE_SHEET_NAME=' }
) -replace '^GOOGLE_SHEET_NAME=', ''
```

Deploy from the repository root:

```powershell
gcloud run deploy dnd-registry-api `
  --source . `
  --region southamerica-east1 `
  --service-account dnd-api@YOUR_PROJECT_ID.iam.gserviceaccount.com `
  --allow-unauthenticated `
  --port 8000 `
  --min 0 `
  --max 1 `
  --memory 512Mi `
  --cpu 1 `
  --set-env-vars "STORAGE_BACKEND=google_sheets,GOOGLE_SHEET_ID=$sheetId,GOOGLE_SHEET_NAME=$sheetName" `
  --set-secrets "WORDPRESS_INTEGRATION_SECRET=wordpress-integration-secret:latest"
```

The first source deployment creates an Artifact Registry repository and uses
Cloud Build. Record the HTTPS service URL returned by the command.

Older Google Cloud CLI releases use `--min-instances` and `--max-instances`.
Updating the CLI is recommended:

```powershell
gcloud components update
```

## 6. Test Cloud Run safely

Health check:

```powershell
Invoke-RestMethod -Uri "YOUR_CLOUD_RUN_URL/api/health"
```

A direct POST without the integration secret should return HTTP 401. Do not send
a real secret from browser JavaScript.

Cloud Run logs:

```powershell
gcloud logging read `
  'resource.type="cloud_run_revision" AND resource.labels.service_name="dnd-registry-api"' `
  --limit=20 `
  --order=desc
```

## 7. Connect local WordPress to Cloud Run

Retrieve the secret into the current PowerShell process without displaying it:

```powershell
$env:DND_CLOUD_RUN_URL = "YOUR_CLOUD_RUN_URL"
$env:DND_INTEGRATION_SECRET = (
  gcloud secrets versions access latest `
    --secret=wordpress-integration-secret
).Trim()
```

Recreate WordPress so Compose passes these variables into its container:

```powershell
docker compose up -d --force-recreate wordpress
```

The plugin prefers server environment variables and does not expose them to its
JavaScript. Submit at <http://localhost:8080/guild-registry/>, then confirm HTTP
201 in Cloud Run logs and verify the row in Google Sheets.

## 8. Connect hosted WordPress

Docker is not required on the hosted WordPress server. Install a ZIP containing
the plugin directory, activate it, and place this shortcode on a page:

```text
[dnd_character_registry]
```

Provide these two values server-side using the host's environment/secrets
configuration when possible:

```text
DND_CLOUD_RUN_URL
DND_INTEGRATION_SECRET
```

If environment variables are unavailable, constants may be defined once in
`wp-config.php`. Never put the integration secret in HTML or JavaScript.

The hosting provider must permit custom plugins and outbound HTTPS requests.

## 9. Rotate the integration secret

Generate a new `$secret` and temporary file as described in step 4, then add a
new version:

```powershell
gcloud secrets versions add wordpress-integration-secret `
  --data-file=$tempSecretFile
```

Deploy the selected version to Cloud Run:

```powershell
gcloud run services update dnd-registry-api `
  --region southamerica-east1 `
  --set-secrets "WORDPRESS_INTEGRATION_SECRET=wordpress-integration-secret:VERSION"
```

Update WordPress with the matching value. Do not print it in terminal output or
screenshots. Disable the compromised/old secret version after validation.

## 10. Stop or remove resources

Local Docker services are independent of Cloud Run:

```powershell
docker compose down
```

Cloud Run remains deployed and scales to zero. To delete the service:

```powershell
gcloud run services delete dnd-registry-api `
  --region southamerica-east1
```

Deleting Cloud Run does not automatically delete Artifact Registry images or
Secret Manager secrets.

