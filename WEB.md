# Reachunt Web App

The web app has two parts:

- FastAPI backend in `api/`
- React/Vite frontend in `web/`

## Local Dev

Install dependencies from the repo root:

```powershell
pip install -r requirements.txt
playwright install chromium

cd web
npm install
cd ..
```

Copy the example env:

```powershell
Copy-Item .env.example .env
```

For local unauthenticated testing, keep:

```env
REQUIRE_AUTH=false
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
WEB_BROWSER=brave
```

Start the API:

```powershell
python -m api.server --host 127.0.0.1 --port 8000
```

Start the frontend:

```powershell
cd web
npm run dev
```

Open:

```text
http://localhost:5173
```

## Production-Style Local Run

```powershell
cd web
npm run build
cd ..
python -m api.server --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Important Env

```env
APP_TITLE=Reachunt
REQUIRE_AUTH=false
APP_SECRET=change-me
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
WEB_LINKEDIN_CLIENT_MODE=true
DDG_SEARCH_ENABLED=true
WEB_BROWSER=brave
WEB_MAILMETEOR_PORT=9224
LOOKUP_DAILY_LIMIT=3
```

For authenticated deployments, set `REQUIRE_AUTH=true` and configure Linkit/Firebase values in `.env`.

For the current public frontend at `https://reachunt.arclabs.page`, use a droplet API domain such as `https://apimail.arclabs.page` and set:

```env
REQUIRE_AUTH=true
APP_SECRET=<strong-random-secret>
CORS_ORIGINS=https://reachunt.arclabs.page
COOKIE_DOMAIN=.arclabs.page
COOKIE_SECURE=true
COOKIE_SAMESITE=none
DATABASE_PATH=/var/lib/reachunt/webapp.db
LOOKUP_DAILY_LIMIT=3
```

On Cloudflare Pages, set:

```env
VITE_API_BASE=https://apimail.arclabs.page
VITE_LINKIT_APP_URL=https://linkitapp.in
```

## Ports

| Service | Port |
| --- | --- |
| Web API | 8000 |
| Vite dev server | 5173 |
| Web Mailmeteor browser | 9224 |
| Batch Mailmeteor browser | 9222 |
| Batch LinkedIn browser | 9223 |
