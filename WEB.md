# Reachunt Web App

Reachunt has two paths:

- Web app: Linkit auth, DuckDuckGo profile discovery, Mailmeteor email lookup.
- Batch pipeline: unchanged; still uses the startup scripts and their own browser ports.

## Product Flow

1. User signs in with Linkit.
2. User enters `Full Name - company.com` or a company/domain.
3. API uses DuckDuckGo (`ddgs`) to find public LinkedIn profile URLs.
4. API sends the LinkedIn profile URL to Mailmeteor on the droplet.
5. UI shows the email result.

There is no production LinkedIn login step for users, and the droplet does not launch per-user LinkedIn browsers.

## Local Dev

```powershell
cd C:\Users\hardi\yc-founder-enrichment
pip install -r requirements.txt
playwright install chromium
.\run-api.ps1
.\run-web-dev.ps1
```

Open:

```text
http://localhost:5173
```

For auth, Linkit must be reachable at `LINKIT_APP_URL`.

## Important Env

```env
APP_TITLE=Reachunt
REQUIRE_AUTH=true
LINKIT_APP_URL=https://linkitapp.in
LINKIT_SOURCE=founder-email
CORS_ORIGINS=https://reachunt.arclabs.page
WEB_LINKEDIN_CLIENT_MODE=true
DDG_SEARCH_ENABLED=true
EMAIL_API_FIRST=false
WEB_BROWSER=chrome
WEB_MAILMETEOR_PORT=9224
DATABASE_PATH=/home/deploy/anyone-email/data/webapp.db
```

Keep `LINKIT_SOURCE=founder-email`; Linkit uses this compatibility slug for authorization.

## Ports

| Service | Port |
|---------|------|
| Web API | 8000 |
| Web Mailmeteor Chrome | 9224 |
| Batch Mailmeteor | 9222 |
| Batch LinkedIn | 9223 |

Production no longer needs `WEB_LINKEDIN_PORT_BASE` for per-user LinkedIn browsers when `WEB_LINKEDIN_CLIENT_MODE=true`.

## Deploy Refresh

On the droplet:

```bash
cd /home/deploy/anyone-email
git pull
source .venv/bin/activate
pip install -r requirements.txt -q
sudo systemctl restart anyone-email
```

Health:

```bash
curl -s https://apimail.arclabs.page/api/v1/health
curl -s https://apimail.arclabs.page/api/v1/ready
```

Cloudflare Pages rebuilds the frontend from `web/`.
