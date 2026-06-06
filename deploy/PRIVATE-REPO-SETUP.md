# Private repo + auto-deploy (reachunt + apimail)

- **Web:** Cloudflare Pages → `https://reachunt.arclabs.page` (auto-deploy on push via Pages Git)
- **API:** Droplet → `https://apimail.arclabs.page` (auto-deploy via GitHub Actions)

---

## Part A — One-time: clone private repo on droplet

SSH in:

```bash
ssh deploy@165.22.216.118
```

### 1) Deploy key (droplet ↔ GitHub, read-only)

```bash
ssh-keygen -t ed25519 -C "droplet-anyone-email-read" -f ~/.ssh/github_anyone_email -N ""
cat ~/.ssh/github_anyone_email.pub
```

Copy the **public** key.

On GitHub: **repo → Settings → Deploy keys → Add deploy key**

- Title: `droplet-read`
- Key: paste public key
- **Allow read access only** (do not enable write unless you need it)

### 2) SSH config for GitHub (multi-repo droplet)

You already use per-repo hosts (`github-linkitbackend`, etc.). Add a **third** block:

```bash
nano ~/.ssh/config
```

Append:

```
Host github-anyone-email
  HostName github.com
  User git
  IdentityFile ~/.ssh/anyone_email_deploy
  IdentitiesOnly yes
```

```bash
chmod 600 ~/.ssh/config ~/.ssh/anyone_email_deploy
ssh -T git@github-anyone-email
```

You should see: `Hi hardikguptaofficialgit/yc-founder-enrichment! ...`

### 3) Clone (use the Host alias, not github.com)

```bash
cd /home/deploy
git clone git@github-anyone-email:hardikguptaofficialgit/yc-founder-enrichment.git anyone-email
cd anyone-email
```

Then continue with `.env`, **Caddy** (or nginx if no Caddy), systemd from the main deploy guide.

### Caddy (recommended if Caddy already runs on the droplet)

Do **not** install nginx. Add `deploy/caddy-apimail.caddy` to your existing Caddyfile, then `sudo systemctl reload caddy`.

---

## Part B — Auto-deploy on push (GitHub Actions → droplet)

Uses workflow: `.github/workflows/deploy-api-droplet.yml`

Triggers on push to `main` when `api/`, `src/`, `deploy/`, or `requirements.txt` change.
(`web/` changes only redeploy Pages, not the droplet.)

### 1) Deploy SSH key (GitHub Actions ↔ droplet)

On **your PC** (not the droplet):

```powershell
ssh-keygen -t ed25519 -C "github-actions-deploy" -f $env:USERPROFILE\.ssh\github_actions_deploy -N '""'
```

- **Public** key → add to droplet:

```bash
# On droplet as deploy user:
mkdir -p ~/.ssh
nano ~/.ssh/authorized_keys
# Paste the public key line, save
chmod 600 ~/.ssh/authorized_keys
```

- **Private** key → GitHub repo secrets (see below).

Test from PC:

```powershell
ssh -i $env:USERPROFILE\.ssh\github_actions_deploy deploy@165.22.216.118 "echo ok"
```

### 2) GitHub repository secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|--------|--------|
| `DEPLOY_HOST` | `165.22.216.118` |
| `DEPLOY_USER` | `deploy` |
| `DEPLOY_SSH_KEY` | Full private key (`github_actions_deploy`, include `-----BEGIN...` lines) |
| `DEPLOY_APP_DIR` | `/home/deploy/anyone-email` (optional) |

### 3) Passwordless restart for deploy user

`post-deploy.sh` restarts systemd. Allow without password:

```bash
sudo visudo
```

Add at end:

```
deploy ALL=(ALL) NOPASSWD: /bin/systemctl restart anyone-email, /bin/systemctl status anyone-email
```

### 4) Push to `main`

```bash
git push origin main
```

GitHub → **Actions** → **Deploy API to Droplet** should run green.

Manual run: **Actions → Deploy API to Droplet → Run workflow**.

---

## Part C — Cloudflare Pages (web) auto-deploy

Already set up if Pages is connected to the same private repo:

- Pages → project → **Settings → Builds** — build command: `cd web && npm ci && npm run build`
- Output: `web/dist`
- Env: `VITE_API_BASE=https://apimail.arclabs.page`

Every push to `main` that touches `web/` rebuilds the UI on Pages automatically.

---

## Summary

| What | Auto-deploy |
|------|-------------|
| `web/` → reachunt.arclabs.page | Cloudflare Pages (Git) |
| `api/` + `src/` → apimail.arclabs.page | GitHub Actions SSH workflow |

Two keys:

1. **Deploy key** on droplet — `git pull` from private repo  
2. **Actions SSH key** — GitHub runner SSHs in and runs `post-deploy.sh`
