# Founder Email — production checklist

## Umami analytics

**Website ID** (goes in `web/.env` as `VITE_UMAMI_WEBSITE_ID`):

`cc680feb-6e25-4286-8b17-3d1a614a81f1`

**Script URL:** `https://cloud.umami.is/script.js`

**API key** (`api_PmB49jCk1IjLc6GLxwcoeSKlIFwNxf4L`) is **not** used by the app. It is only for the [Umami HTTP API](https://umami.is/docs/api) (pulling stats from a script or backend). Do **not** put it in `VITE_*` env vars or commit it. If this key was shared publicly, rotate it in Umami → Settings → API keys.

### Umami dashboard

1. **Settings → Websites → foundersmail → Edit**
2. Set **Domain** to your live Founder Email URL (e.g. `founderemail.linkitapp.in` or whatever you deploy), not `localhost`.
3. After deploy, open the live site → Umami **Realtime** should show a visit within ~30s.

### Build with analytics

```powershell
cd web
npm run build
```

Rebuild whenever you change `web/.env` (Vite embeds env at build time).

---

## Founder Email API (this repo)

| Variable | Production example |
|----------|-------------------|
| `APP_SECRET` | Long random string |
| `REQUIRE_AUTH` | `true` |
| `LINKIT_APP_URL` | `https://linkitapp.in` (main app for SSO, **not** `api.linkitapp.in`) |
| `LINKIT_V5_BACKEND` or `LINKIT_SERVICE_ACCOUNT_PATH` | Path to `serviceAccountKey.json` (same Firebase project as Linkit) |
| `CORS_ORIGINS` | Your Founder Email frontend origin(s), comma-separated |
| `COOKIE_SECURE` | `true` when using HTTPS |

`api.linkitapp.in` is the **Linkit** backend. Founder Email runs its **own** FastAPI server (this repo) and only **verifies Firebase ID tokens** with the shared service account.

---

## Linkit (`linkit_v5`) — required for SSO

Deploy the main app to **https://linkitapp.in** with the **founder-email** sign-in flow (already in `src/pages/SignIn.tsx`):

- `source=founder-email` + `redirect=<your Founder Email URL>` → authorize screen → redirect back with `#authToken`.

### Linkit — nothing required on `api.linkitapp.in` specifically

Founder Email does **not** call Linkit’s REST API for login. Flow:

1. User clicks **Continue with Linkit** on Founder Email.
2. Browser opens `https://linkitapp.in/signin?redirect=...&source=founder-email`.
3. User signs in (Firebase on Linkit).
4. Linkit calls `POST https://api.linkitapp.in/auth/authorize-app` (existing endpoint).
5. Linkit redirects to Founder Email with Firebase ID token in the hash.
6. Founder Email API verifies the token and sets `founder_session` cookie.

### Linkit backend env (already typical)

- Firebase Admin / `serviceAccountKey.json` (same project Founder Email uses).
- No new env var for Founder Email unless you want to restrict redirects (currently any `https://` redirect is allowed).

### Linkit frontend deploy checklist

- [ ] `SignIn.tsx` with `founder-email` authorize UI is deployed to production.
- [ ] Test:  
  `https://linkitapp.in/signin?redirect=https%3A%2F%2FYOUR-FOUNDER-APP%2F&source=founder-email`

### Optional: SignUp parity

`SignUp.tsx` does not yet mirror Studio/founder-email external redirect. Prefer **sign in** from Founder Email; add SignUp handling later if you link “Sign up on Linkit” for new users.

---

## Linkit Studio (`linkit-studio`) — no changes needed

Studio uses `source=studio` and `https://linkitapp.in` (see `linkit-studio/src/lib/mainAppUrl.ts`). Founder Email is a separate app (`source=founder-email`). You do **not** need Studio code or env changes for Founder Email or Umami.

---

## Architecture (quick)

```
Founder Email UI  ──►  Founder Email API (your host)
       │                      │
       │                      └── Firebase Admin verify token
       └── SSO redirect ──►  linkitapp.in/signin
                                    │
                                    └── api.linkitapp.in (authorize-app only)
```

---

## Smoke test after deploy

1. Open Founder Email → Umami Realtime shows visitor.
2. **Continue with Linkit** → sign in → land back logged in.
3. Connect network → run one lookup → Umami events: `lookup_start`, `lookup_complete`.
