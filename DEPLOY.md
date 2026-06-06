# Reachunt Production Checklist

Reachunt is split into two deploys:

- Frontend: Cloudflare Pages (`web/dist`)
- API: droplet FastAPI service behind Caddy (`apimail.arclabs.page`)

## Cloudflare Pages

Set these build-time environment variables:

```env
VITE_API_BASE=https://apimail.arclabs.page
VITE_LINKIT_APP_URL=https://linkitapp.in
```

Redeploy Pages after changing any `VITE_*` value.

## Droplet API

Important production variables:

```env
APP_TITLE=Reachunt
REQUIRE_AUTH=true
LINKIT_APP_URL=https://linkitapp.in
LINKIT_SOURCE=founder-email
LINKIT_SERVICE_ACCOUNT_PATH=/home/deploy/secrets/serviceAccountKey.json
CORS_ORIGINS=https://reachunt.arclabs.page
COOKIE_SECURE=true
COOKIE_SAMESITE=none
COOKIE_DOMAIN=.arclabs.page
WEB_LINKEDIN_CLIENT_MODE=true
DDG_SEARCH_ENABLED=true
EMAIL_API_FIRST=false
DATABASE_PATH=/home/deploy/anyone-email/data/webapp.db
```

Keep `LINKIT_SOURCE=founder-email`; it is the Linkit compatibility slug, not the public product name.

Restart after env or code changes:

```bash
cd /home/deploy/anyone-email
git pull
source .venv/bin/activate
pip install -r requirements.txt -q
sudo systemctl restart anyone-email
```

Health checks:

```bash
curl -s https://apimail.arclabs.page/api/v1/health
curl -s https://apimail.arclabs.page/api/v1/ready
```

## Linkit SSO

Reachunt uses Linkit for login:

```text
https://linkitapp.in/signin?redirect=https%3A%2F%2Freachunt.arclabs.page%2F&source=founder-email
```

Flow:

1. User clicks **Continue with Linkit** on Reachunt.
2. Linkit signs in or signs up the user.
3. Linkit authorizes `source=founder-email`.
4. Linkit redirects back to Reachunt with `#authToken`.
5. Reachunt API verifies the Firebase token and creates the app session.

## Discovery Flow

For production, `WEB_LINKEDIN_CLIENT_MODE=true` means Reachunt does not require a LinkedIn login step. The droplet does not launch a per-user LinkedIn browser.

Lookups use DuckDuckGo (`ddgs`) to find public LinkedIn profile URLs and Mailmeteor on the server to resolve emails.

## Umami

Set the Umami website domain to your live Reachunt URL, not localhost. The frontend can use:

```env
VITE_UMAMI_WEBSITE_ID=<your-website-id>
VITE_UMAMI_SCRIPT_URL=https://cloud.umami.is/script.js
```
