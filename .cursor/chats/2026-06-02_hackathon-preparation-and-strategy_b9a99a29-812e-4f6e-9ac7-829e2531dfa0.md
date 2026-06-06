---
title: "Hackathon preparation and strategy"
model: "default"
updated: "2026-06-02T23:01:16.421Z"
---

## User

see i have to win this https://hackathon.x-arc.ai/ like through that i wil lgot hired so anaylze this all and tel me what to do

## Assistant

Analyzing the hackathon site and your project so we can map requirements to a winning strategy.


## Assistant

This is not a typical hackathon where a polished demo wins. [X-ARC’s hiring hackathon](https://hackathon.x-arc.ai/) is a **5-day take-home for one full-time remote role** building production agentic systems. They evaluate **how you engineer an autonomous agent**, not a flashy UI.

---

## What you’re actually competing for

| Dimension | What they care about |
|-----------|---------------------|
| **Outcome** | One hire — strongest submission gets a 30-min review call, then possibly an offer |
| **Artifact** | A production-shaped autonomous agent you build **from scratch** in a domain you pick |
| **Timeline** | 5 days from the assignment email (not from registration) |
| **Evaluation depth** | Code, **commit history**, **unedited AI session traces**, video, and `MEMO.md` |

They are hiring someone who can ship **real agent infrastructure**, not someone who glued a chat UI onto an API.

---

## The 5 non‑negotiable requirements

Every submission must satisfy **all five**. Missing one likely disqualifies you.

### 1. 50+ tools across 4+ namespaces
- Tools must be **model-selected** (LLM picks from a registry), not hard-coded `if/else` routing.
- Registry must stay **coherent at scale** — not 50 separate `if tool == "x"` branches.
- Example namespaces: `research.*`, `web.*`, `data.*`, `github.*`, `report.*`

### 2. Real subagent orchestration
- At least one tool **spawns a subagent** with:
  - **Isolated context** (separate message history / window)
  - **Scoped tool subset**
  - **Structured result** returned to parent
- A function renamed “subagent” does **not** count.

### 3. Long-horizon execution (20+ tool calls)
- One session completes a task with **≥20 tool calls** without losing the plan.
- **Context management must be explicit in code** (summarization, plan tracker, scratchpad, compaction — not magic).

### 4. Production scaffolding
Must include all of:
- Observability (structured logs, traces, metrics)
- Retries with exponential backoff
- Rate limiting on external calls
- Typed error handling
- Evaluation harness
- Unit + integration tests
- Repo structured for **deployment**, not a notebook

### 5. Composable tool I/O
- At least one tool **consumes structured output** from another (tool chains, not isolated one-offs).

---

## How your current project maps

Your `yc-founder-enrichment` repo is a **browser automation pipeline** (YC lookup → LinkedIn → Mailmeteor email). It’s solid engineering, but it is **not** what they’re asking for:

| Requirement | Your repo today |
|-------------|-----------------|
| 50+ model-routed tools | ❌ No agent / tool registry |
| Subagents | ❌ |
| 20+ tool-call sessions | ❌ Deterministic scripts, not LLM loops |
| Production scaffolding | ⚠️ Partial (API, retries in places) — missing eval harness, observability, typed agent errors |
| Composable tool chains | ❌ Linear pipeline, not LLM tool composition |
| `MEMO.md` | ❌ |

**Do not submit this repo as-is.** You can **reuse domain knowledge** (founder research, web scraping, email resolution) as **tools inside a new agent**, but the core must be a new agent architecture.

---

## Best domain for you (given your background)

Pick a domain where you can go **deep in 5 days**:

| Domain | Fit for you | Risk |
|--------|-------------|------|
| **Deep research / founder intelligence** | ⭐ Best — you already know YC, LinkedIn, email workflows | Don’t let scraping eat all 5 days |
| Repository automation | Good if strong with GitHub API | Crowded, harder to differentiate |
| DevOps / SRE agent | Only if you already live in that world | Easy to over-scope |
| Coding agent | High bar, lots of competition | Hard to stand out in 5 days |
| Personal-ops agent | Easier scope | May feel shallow unless execution is excellent |

**Recommended:** a **Founder / Company Research Agent** — e.g. “Given a startup name or domain, produce a structured dossier with founders, emails, web presence, news, and a brief.” That gives you natural 20+ tool-call runs and composable pipelines.

---

## Architecture that clears the bar (5-day blueprint)

```
┌─────────────────────────────────────────────────────────┐
│  CLI / API entrypoint                                   │
│  AgentLoop (plan → act → observe → compact context)     │
└──────────────────────────┬──────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   ToolRegistry      SubagentSpawner     ContextManager
   (50+ tools,        (isolated ctx,       (summarize,
    4 namespaces)     scoped tools)        plan store)
        │
   ┌────┴────┬─────────┬─────────┐
   research.* web.*  data.*  report.*
```

**Suggested stack (fast to ship):**
- **Python** + Pydantic (typed tool I/O and errors)
- **OpenAI / Anthropic** function calling for tool routing
- **tenacity** — retries with backoff
- **slowapi** or token bucket — rate limits
- **structlog** + JSON logs (or OpenTelemetry)
- **pytest** — unit tests for tools; integration test for full 20+ call run
- **eval/** — golden tasks + scoring (did it find founders? valid JSON?)

**Tool count strategy (don’t hand-write 50 unrelated tools):**
- Use **parameterized tool families** with clear schemas, e.g.:
  - `research.search_news(query, source, limit)`
  - `research.search_crunchbase(...)`, `research.search_yc(...)`, etc.
- Group into namespaces; aim for **~12–15 distinct tools × variants** or explicit per-source tools until you hit 50+.
- Registry stays one module with metadata (description, namespace, input/output schema) — that’s what “coherent at 50 tools” means.

**Subagent pattern:**
- Parent tool: `research.deep_dive(topic)` → spawns subagent with only `web.fetch`, `research.extract`, `research.summarize` → returns `{ findings: [...], sources: [...], confidence }`.

**Context management (must be visible in code):**
- `PlanStore` — current step, completed steps
- `ContextCompactor` — after N tokens or M tool calls, summarize history
- Log compaction events in observability

---

## 5-day execution plan

| Day | Focus |
|-----|--------|
| **Day 1** | Skeleton: agent loop, tool registry (aim 20 tools), one namespace, logging, typed errors. **Commit often.** |
| **Day 2** | Hit 50+ tools / 4 namespaces. Subagent spawner working. One end-to-end task (even if short). |
| **Day 3** | Context management + 20+ tool-call demo task. Retries, rate limits, integration tests. |
| **Day 4** | Eval harness (3–5 golden cases). Harden edge cases. Polish composable chains. |
| **Day 5** | `MEMO.md`, video (3–5 min), export **unedited** Cursor/Claude traces, final README, clean commit history. |

**Cut ruthlessly:** fancy React UI, auth, multi-user — none of that is scored. A **CLI + good logs + eval results** beats a pretty dashboard.

---

## What separates winners from rejections

### They will reward
- Clean registry design at 50 tools
- Real subagent isolation you can **show in the video**
- A recorded run with **20+ tool calls** and coherent plan
- Explicit context strategy in code
- Eval harness with pass/fail on real tasks
- **Commit history** that shows iterative engineering (not one giant dump)
- **Traces** showing good judgment with AI (when you pushed back, refactored, fixed architecture)
- `MEMO.md` with a **defensible design tradeoff** (e.g. “summarize every 8 tool calls vs sliding window — I chose X because…”)

### They will reject
- 50 tools that are copy-paste wrappers with no registry discipline
- “Subagent” that’s just a nested function call in the same context
- Demo that only runs 5 tool calls
- Notebook-style repo with no tests or observability
- Heavily edited AI traces
- Generic “ChatGPT wrapper” with 3 tools

---

## Submission checklist (reply to assignment email)

1. **Public GitHub repo** — code + meaningful commits  
2. **3–5 min video** — working demo, deepest code walkthrough, **one moment you disagreed with the model**  
3. **Prompts + unedited session traces** (Cursor JSONL from `~/.cursor/projects/...` or Claude Code export)  
4. **`MEMO.md` at repo root** — what you built, what you cut, what you’d do with more time, **one design decision you’d defend**

---

## Video script (rough)

1. **0:00–0:45** — Problem + domain choice  
2. **0:45–2:00** — Live run: 20+ tool calls, show logs/plan tracker  
3. **2:00–3:30** — Code: registry, subagent spawner, context compactor  
4. **3:30–4:30** — Eval harness results  
5. **4:30–5:00** — “The model wanted X; I chose Y because…”

---

## Immediate next steps

1. **Apply** on [hackathon.x-arc.ai](https://hackathon.x-arc.ai/) if you haven’t — clock starts on assignment email.  
2. **Start a new repo** (e.g. `founder-research-agent`) — don’t retrofit the enrichment UI.  
3. **Day 1 goal:** agent loop + registry + 1 subagent + structured logging — before adding more tools.  
4. **Keep Cursor sessions from day one** — traces are part of the submission.  
5. **Pick one golden task** early: e.g. “Research `Stripe` → JSON dossier with founders, emails, sources” and build toward a passing eval.

---

## Bottom line

To win this, you need to look like someone X-ARC would trust to run **production agents at scale**: rigorous tool registry, real subagents, long-horizon runs with explicit context control, and evals/tests/observability — plus honest traces and a sharp `MEMO.md`.

Your founder-enrichment work is **domain advantage**, not the submission itself. Wrap that knowledge as tools inside a **new agent codebase** built to their five requirements.

If you want, I can next sketch a **concrete repo layout + tool namespace list + golden eval cases** tailored to a Founder Research Agent you can start building today.
