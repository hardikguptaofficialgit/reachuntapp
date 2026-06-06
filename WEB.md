# Web app

Premium lookup UI with accounts and per-user professional network connection.

**Your batch pipeline is unchanged:** ports **9222** (Mailmeteor) and **9223** (LinkedIn) stay dedicated to `run_startups.py` / `enrich_emails.py`.

The web app uses:

| Service | Port | Profile |
|---------|------|---------|
| Web email resolver | **9224** | `data/web-mailmeteor-cdp-profile/` |
| Per-user network | **9300–9380** | `data/web-linkedin-{hash}/` |

---

## Deployed product flow

1. User **signs in with Linkit**
2. User clicks **Connect network** → Brave opens → they sign in to their professional account
3. User enters `Full Name — company.com` → discovery + email verification
4. UI never mentions internal tools; only user-friendly steps

---

## Local dev (with auth)

Sign-in uses **Linkit SSO** (same Firebase project as Linkit Studio). You need the main Linkit app running for login redirects.

```powershell
pip install -r requirements.txt
# Point Firebase at linkit_v5 (see .env.example)
$env:LINKIT_V5_BACKEND = "C:\Disk E\Startups\Linkit\linkit_v5\backend"
$env:LINKIT_APP_URL = "http://localhost:8080"
.\run-api.ps1
.\run-web-dev.ps1
```

In another terminal, run the Linkit main app on port **8080** (your usual `linkit_v5` dev command).

Flow: **Continue with Linkit** → sign in on Linkit → authorize Founder Email → return with `#authToken` → API exchanges for a session cookie.

`run-api.ps1` uses `python -m api.server` (Windows-safe Playwright). Auto-reload is off on Windows so LinkedIn connect works.

### Speed (on by default)

| Trick | Effect |
|--------|--------|
| **Repeat lookups** | Instant from history (same query) |
| **Profile cache** | Skips LinkedIn if profile was found before |
| **`FAST_LOOKUP=true`** | Shorter waits (default) |
| **`ANYMAIL_API_KEY`** | Email via API first (~seconds vs browser) |
| **Keep API running** | Mailmeteor tab stays warm between lookups |

Optional env:

```powershell
$env:FAST_LOOKUP = "true"          # default
$env:LOOKUP_TIMEOUT_SEC = "12"
$env:LINKEDIN_SEARCH_TIMEOUT_MS = "10000"
$env:ANYMAIL_API_KEY = "your-key" # fastest email phase
$env:EMAIL_API_FIRST = "true"
```

Open http://localhost:5173 → **Continue with Linkit** → Connect network → Discover.

Set `APP_SECRET` in production.

## Local dev (skip auth, uses batch LinkedIn 9223)

While your batch email run is going, use this only for UI testing:

```powershell
.\run-api-dev.ps1
```

## Production

```powershell
$env:APP_SECRET = "long-random-secret"
$env:REQUIRE_AUTH = "true"
$env:COOKIE_SECURE = "true"
.\run-web-prod.ps1
```

On a Droplet you need a display or virtual framebuffer so Brave can open for each user's network connect.

---

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_SECRET` | (required in prod) | JWT signing |
| `REQUIRE_AUTH` | `true` | `false` = dev bypass |
| `WEB_MAILMETEOR_PORT` | `9224` | Isolated from batch 9222 |
| `WEB_LINKEDIN_PORT_BASE` | `9300` | Per-user network ports |
| `CORS_ORIGINS` | localhost:5173 | Comma-separated |
| `LINKIT_APP_URL` | `http://localhost:8080` | Main Linkit app for SSO redirect |
| `LINKIT_V5_BACKEND` | — | Folder with `serviceAccountKey.json` |
| `LINKIT_SERVICE_ACCOUNT_PATH` | — | Direct path to Firebase service account JSON |

### Scale / bulk queue

| Variable | Default | Purpose |
|----------|---------|---------|
| `BULK_MAX_QUERIES` | `100` | Max lines per bulk submit |
| `QUEUE_MAX_PER_USER` | `200` | Max queued + running jobs per user |
| `JOB_WORKER_COUNT` | `2` | Async workers (cache hits run in parallel) |
| `JOB_STATUS_BATCH_MAX` | `100` | Jobs per status poll request |
| `JOB_MEMORY_MAX` | `8000` | In-memory job cap before eviction |

Bulk queues all jobs on the server; the UI polls status in parallel batches. Single Discover lookups jump ahead of bulk (priority queue). Browser lookups still run one-at-a-time (shared Mailmeteor/LinkedIn lock); cached repeats skip the browser instantly.

---

## Web analytics (optional)

The React app can send **privacy-safe** usage events (no emails, names, or lookup text). Enable one provider via `web/.env` (see `web/.env.example`).

### Option A — Umami (recommended)

1. Create an account at [umami.is](https://umami.is) or use your self-hosted instance.
2. **Settings → Websites → Add website** — enter your production URL/domain.
3. Open the site → copy **Website ID** (UUID).
4. Copy the **tracking script** host (e.g. `https://cloud.umami.is/script.js` or your self-hosted `/script.js`).
5. Create `web/.env`:

```env
VITE_UMAMI_WEBSITE_ID=your-website-id-uuid
VITE_UMAMI_SCRIPT_URL=https://cloud.umami.is/script.js
```

6. Rebuild before deploy: `cd web && npm run build` (Vite bakes env at build time).
7. In Umami dashboard you’ll see pageviews and custom events: `sign_in`, `lookup_start`, `lookup_complete`, `screen_view`.

**Local dev:** leave vars empty or set `VITE_ANALYTICS_DISABLED=true`.

### Option B — Plausible

Lightweight, GDPR-friendly, no cookie banner in most cases.

1. Create a site at [plausible.io](https://plausible.io) (or self-host).
2. Add your production domain in Plausible.
3. In `web/.env`:

```env
VITE_PLAUSIBLE_DOMAIN=yourdomain.com
# For custom events (lookup_start, sign_in, etc.):
VITE_PLAUSIBLE_SCRIPT_URL=https://plausible.io/js/script.tagged-events.js
```

4. In Plausible → **Goal conversions**, add custom events (exact names):

| Event | Meaning |
|-------|---------|
| `screen_view` | Tab or auth screen (`props.screen`) |
| `sign_in` | Linkit SSO success |
| `lookup_start` | User ran a lookup (`props.mode`: quick/split) |
| `lookup_complete` | Lookup finished (`props.hit`: true/false) |

5. Rebuild: `npm run build` (Vite bakes env at build time).

### Option C — Google Analytics 4

1. Create a GA4 property → **Data streams** → Web → copy **Measurement ID** (`G-…`).
2. In `web/.env`:

```env
VITE_GA_MEASUREMENT_ID=G-XXXXXXXXXX
```

3. Rebuild and deploy. Events appear under **Reports → Engagement → Events**.

### Local dev

Leave analytics unset, or disable explicitly:

```env
VITE_ANALYTICS_DISABLED=true
```

### What is tracked

- Page load + screen changes (`discover`, `bulk`, `library`, `build`, `auth`, `loading`)
- Sign-in success
- Lookup started / completed (hit or miss only — no query content)

To add more events, call `trackEvent('your_event', { key: 'value' })` from `web/src/lib/analytics.ts` (avoid PII in props).
