# Startups pipeline (LinkedIn + Mailmeteor)

New workflow for **`startupsnew.xlsx`** — not YC.

## Input / output

| | Path |
|---|------|
| Excel | `C:\Users\hardi\Downloads\startupsnew.xlsx` |
| CSV | `output\startupsnew_results.csv` |

Columns: `startup_name`, `founder_name`, `linkedin_url`, `email`, `email_status`, `notes`

## Setup (once)

```powershell
cd C:\Users\hardi\yc-founder-enrichment
pip install -r requirements.txt
playwright install chromium
```

## Steps

### 1) Log into LinkedIn (once)

```powershell
.\run-linkedin-setup.ps1
```

Brave opens → log into LinkedIn → press **Enter** in PowerShell.

Uses profile `data\brave-linkedin-profile` (port **9223**).

### 2) Get founder LinkedIn URLs (530 startups)

```powershell
.\run-linkedin.ps1
```

Searches LinkedIn while logged in, saves to CSV. Resumes if stopped.

Pilot:

```powershell
python run_startups.py --linkedin-only --limit 10
```

### 3) Get emails via Mailmeteor

Close CSV in Excel. Uses Mailmeteor on port **9222** (same as before):

```powershell
.\run-startups-emails.ps1
```

Or both steps:

```powershell
.\run-startups-full.ps1
```

## Web app (single lookup)

Accounts + **Connect network** (user signs into their professional profile). Input: `Hard Name — company.com`.

See **[WEB.md](WEB.md)**. **Batch ports 9222/9223 are not used by the web app** (web uses 9224 + 9300+).

```powershell
.\run-api.ps1          # terminal 1 (auth on)
.\run-web-dev.ps1      # terminal 2 → http://localhost:5173
# Or while batch emails run: .\run-api-dev.ps1 (no auth, read-only UI test)
```

## Notes

- **Two Brave profiles:** LinkedIn (9223) and Mailmeteor (9222) — can run your normal Brave separately.
- LinkedIn may rate-limit — use `--linkedin-delay 8` if needed.
- Old YC pipeline still in `run.py` / `enrich_emails.py` if needed.
