# Automation flow (start to finish)

This is the same work you did by hand — automated end to end. **Nothing sends email.**

---

## Visual flow

```mermaid
flowchart TD
    A[Excel: startups.xlsx\n884 startup names] --> B[Read next startup name]
    B --> C{Already done?}
    C -->|yes| B
    C -->|no| D[Match name on YC directory]
    D --> E{Found on YC?}
    E -->|no| F[Write row: notes=yc_not_found\nempty email]
    E -->|yes| G[Open YC company page]
    G --> H[Read Active Founders\nname + LinkedIn URL]
    H --> I{Any founders?}
    I -->|no| J[Write row: no_founders_on_page]
    I -->|yes| K[For each founder]
    K --> L[Mailmeteor: paste LinkedIn\nclick FIND EMAIL]
    L --> M{Email returned?}
    M -->|yes| N[Save row with email\nemail_status=found]
    M -->|no / error| O[Save row empty email\nnotes=no_email]
    O --> P{More founders?}
    N --> P
    P -->|yes| K
    P -->|no| Q{Any email for startup?}
    Q -->|no| R[Mark notes=no_emails_for_startup\ncontinue]
    Q -->|yes| S[Continue]
    R --> T[Save progress.json\nappend results.csv]
    S --> T
    F --> T
    J --> T
    T --> U{More startups?}
    U -->|yes| B
    U -->|no| V[Final CSV ready]
```

---

## Step by step (what the script does)

| Step | Your manual action | Automation |
|------|-------------------|------------|
| 1 | Open Excel, copy startup name | Reads `C:\Users\hardi\Downloads\startups.xlsx` column `Startup` |
| 2 | Search on ycombinator.com/companies | Fuzzy match against YC company list (~5,900 companies) |
| 3 | Open company page | Opens `ycombinator.com/companies/{slug}` |
| 4 | Copy founder LinkedIn from Active Founders | Parses founder name + `linkedin.com/in/...` |
| 5 | Paste LinkedIn in Mailmeteor, FIND EMAIL | Chrome + Mailmeteor tool (same website) |
| 6 | Copy email into your sheet | Writes one CSV row per founder |
| 7 | Next startup | Repeats; **skips** if no email (does not stop) |

---

## When there is no email

| Situation | What happens |
|-----------|----------------|
| Mailmeteor finds no email for one founder | Row saved with empty `email`, `email_status=not_found`, continues |
| Mailmeteor error (e.g. Cloudflare) | Skips **remaining founders** for that startup, goes to **next startup** |
| No email for **any** founder at that startup | Notes set to `no_emails_for_startup`, moves to next startup |
| Startup not on YC | One row, `notes=yc_not_found`, moves on |
| No founders on page | One row, `notes=no_founders_on_page`, moves on |

The run **never waits forever** on a missing email.

---

## Files

| File | Role |
|------|------|
| `startups.xlsx` | Input (your list) |
| `output/results.csv` | **Final output** — all startups in one file |
| `data/progress.json` | Resume checkpoint if you stop the run |
| `data/chrome-mailmeteor-profile/` | Chrome cookies after warmup (Cloudflare) |

---

## Commands (order)

```powershell
cd C:\Users\hardi\yc-founder-enrichment

# 1) Once: pass Cloudflare in Chrome
.\run-warmup.ps1

# 2) Test 5 startups
.\run-pilot.ps1

# 3) All 884 startups (hours; safe to stop and resume)
.\run-full.ps1
```

---

## Example CSV rows

**Success:**

| startup_name | founder_name | linkedin_url | email | email_status |
|--------------|--------------|--------------|-------|--------------|
| Caseflood.ai | Ethan Hilton | https://linkedin.com/in/ethan-hilton/ | ethan@... | found |

**No email (startup skipped forward):**

| startup_name | founder_name | linkedin_url | email | email_status | notes |
|--------------|--------------|--------------|-------|--------------|-------|
| SomeCo | Jane Doe | https://linkedin.com/in/jane/ | | not_found | no_emails_for_startup |

---

## Time

- ~30–60 seconds per founder (Mailmeteor + delay)
- ~884 startups × ~2 founders ≈ **many hours** for full run  
- Use `.\run-full.ps1` and leave PC on; rerun same command if interrupted.
