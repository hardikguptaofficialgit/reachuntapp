# Reachunt

Reachunt is a local-first founder/contact enrichment tool. It can run as a web app for single or bulk lookups, and it also includes a batch Excel pipeline for finding founder LinkedIn profiles and emails.

The project uses:

- Python + FastAPI for the API
- React + Vite for the web UI
- Playwright for browser automation
- DuckDuckGo/DDGS for public profile discovery
- Mailmeteor's public LinkedIn email finder flow for email lookup

## Prerequisites

Install these before starting:

- Python 3.10 or newer
- Node.js 20 or newer
- npm
- Git
- Brave or Chrome

## Clone And Install

```powershell
git clone <your-repo-url>
cd yc-founder-enrichment

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
playwright install chromium

cd web
npm install
cd ..
```

On macOS/Linux, activate the environment with:

```bash
source .venv/bin/activate
```

## Configure Environment

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

For simple local testing without Linkit/Firebase auth, set:

```env
REQUIRE_AUTH=false
APP_SECRET=local-dev-secret
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DDG_SEARCH_ENABLED=true
WEB_BROWSER=brave
```

Use `WEB_BROWSER=chrome` if you do not have Brave installed.

For authenticated production-like usage, keep `REQUIRE_AUTH=true` and configure the Linkit/Firebase values in `.env`. Do not commit `.env`.

## Public Deployment Shape

The frontend can stay on Cloudflare Pages:

```text
https://reachunt.arclabs.page
```

Run the backend on your droplet behind an API domain, for example:

```text
https://apimail.arclabs.page
```

Set these backend env values on the droplet:

```env
REQUIRE_AUTH=true
APP_SECRET=<strong-random-secret>
LINKIT_APP_URL=https://linkitapp.in
CORS_ORIGINS=https://reachunt.arclabs.page
COOKIE_DOMAIN=.arclabs.page
COOKIE_SECURE=true
COOKIE_SAMESITE=none
DATABASE_PATH=/var/lib/reachunt/webapp.db
WEB_LINKEDIN_CLIENT_MODE=true
DDG_SEARCH_ENABLED=true
WEB_BROWSER=chrome
LOOKUP_DAILY_LIMIT=3
RATE_LIMIT_LOOKUPS_PER_MIN=20
```

Set the frontend build env on Cloudflare Pages:

```env
VITE_API_BASE=https://apimail.arclabs.page
VITE_LINKIT_APP_URL=https://linkitapp.in
```

`LOOKUP_DAILY_LIMIT=3` gives each authenticated user three lookup jobs per UTC day. Set it to `0` only if you want unlimited lookups.

## Run The Web App Locally

Start the API in one terminal:

```powershell
python -m api.server --host 127.0.0.1 --port 8000
```

Start the web UI in a second terminal:

```powershell
cd web
npm run dev
```

Open:

```text
http://localhost:5173
```

The Vite dev server proxies `/api` requests to `http://127.0.0.1:8000`.

## Production-Style Local Run

To build the frontend and serve it from the FastAPI app:

```powershell
cd web
npm run build
cd ..
python -m api.server --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

## Batch Excel Pipeline

The batch pipeline reads an Excel file, searches LinkedIn for founders, and writes a CSV output.

Your Excel file should contain a startup/company column. By default the code looks for:

```text
Startup Name
```

Run a small LinkedIn-only test first:

```powershell
python run_startups.py --input "C:\path\to\startups.xlsx" --output "output\results.csv" --linkedin-only --limit 10
```

If your column has a different name:

```powershell
python run_startups.py --input "C:\path\to\startups.xlsx" --column "Company" --output "output\results.csv" --linkedin-only --limit 10
```

To save a local LinkedIn browser session:

```powershell
python run_startups.py --login-only
```

To run LinkedIn discovery:

```powershell
python run_startups.py --input "C:\path\to\startups.xlsx" --output "output\results.csv" --linkedin-only
```

To run email lookup for rows that already have LinkedIn URLs:

```powershell
python run_startups.py --output "output\results.csv" --emails-only
```

To run both phases:

```powershell
python run_startups.py --input "C:\path\to\startups.xlsx" --output "output\results.csv"
```

The CSV output columns are:

```text
startup_name, founder_name, linkedin_url, email, email_status, notes
```

Generated files under `output/` and local progress files under `data/` are ignored by git.

## Useful Commands

Run API directly:

```powershell
python -m api.server --host 127.0.0.1 --port 8000
```

Build frontend:

```powershell
cd web
npm run build
```

Run tests:

```powershell
pytest
```

## Ports

| Service | Default Port |
| --- | --- |
| API | 8000 |
| Web dev server | 5173 |
| Web Mailmeteor browser | 9224 |
| Batch Mailmeteor browser | 9222 |
| Batch LinkedIn browser | 9223 |

## Local Files Not Committed

The repo intentionally ignores local/private artifacts:

- `.env` and other local env files
- `.cursor/` editor/chat state
- Excel/CSV exports
- `output/`
- generated `data/*.json`
- local databases
- browser/session profiles
- network/debug captures

This keeps the public repo usable without leaking personal runs, browser sessions, or generated contact data.

## Troubleshooting

If the API cannot launch a browser, install Playwright again:

```powershell
playwright install chromium
```

If the web app cannot reach the API, confirm the API is running on port `8000` and the frontend is running on port `5173`.

If batch lookup cannot find your spreadsheet column, pass the correct column name with `--column`.

If LinkedIn or Mailmeteor rate-limits you, slow the batch run down:

```powershell
python run_startups.py --input "C:\path\to\startups.xlsx" --output "output\results.csv" --linkedin-delay 8 --delay 6 --jitter 4
```

## License

MIT License. See [LICENSE](LICENSE).
