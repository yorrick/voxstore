# VoxStore - Self-Healing Voice-Powered Product Catalog

## Overview

A vanilla JS e-commerce storefront with voice search, backed by a FastAPI server. When errors occur in production, Sentry captures them, triggers a webhook to our **autopilot** service, which uses the Claude Agent SDK (Python) to autonomously create a fix PR, review it, run a security check, and auto-merge it.

## Architecture

```
┌────────────────────────────┐     ┌─────────────────────────────┐
│  app/client (Vanilla JS)   │────▶│  app/server (FastAPI)       │
│  - Product grid            │     │  - /api/products            │
│  - Voice search            │     │  - /api/search              │
│  - Cart                    │     │  - /api/cart                │
│  - Sentry Browser SDK      │     │  - /api/health              │
│  - No build step           │     │  - Sentry Python SDK        │
└────────────────────────────┘     │  - SQLite                   │
                                   └─────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  autopilot/ (Self-Healing Service - separate from the app)       │
│                                                                  │
│  webhook_server.py  ◀── Sentry webhook + GitHub webhook          │
│       │                  (exposed via Cloudflare Tunnel)          │
│       ▼                                                          │
│  fix_agent.py       ── Uses Claude Agent SDK to analyze error    │
│       │                 and create a fix branch + PR             │
│       ▼                                                          │
│  review_agent.py    ── Uses Claude Agent SDK to review the PR    │
│       ▼                                                          │
│  security_agent.py  ── Uses Claude Agent SDK for security review │
│       ▼                                                          │
│  merge_ops.py       ── Auto-merges if all checks pass           │
│                                                                  │
│  modules/           ── Shared utilities (git, github, logging)   │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  .github/workflows/                     │
│  ci.yml         ── Lint + tests on PRs  │
└─────────────────────────────────────────┘
```

## Project Structure

```
voxstore/
├── app/
│   ├── client/                     # Vanilla JS frontend (no build step)
│   │   ├── index.html              # Main HTML
│   │   ├── style.css               # Styles
│   │   ├── app.js                  # Main JS (product grid, cart, voice search)
│   │   └── sentry.js               # Sentry browser SDK init
│   │
│   └── server/                     # FastAPI backend
│       ├── server.py               # Main FastAPI app
│       ├── core/
│       │   ├── models.py           # Pydantic models
│       │   ├── db.py               # SQLite setup + seed data
│       │   └── search.py           # Search logic
│       ├── pyproject.toml
│       └── .env.sample
│
├── autopilot/                      # Self-healing service (NOT part of the app)
│   ├── webhook_server.py           # FastAPI server receiving Sentry + GitHub webhooks
│   ├── pipeline.py                 # Orchestrates the full fix→review→security→merge pipeline
│   ├── agents/
│   │   ├── fix_agent.py            # Claude Agent SDK: analyze error, create fix PR
│   │   ├── review_agent.py         # Claude Agent SDK: review the PR
│   │   └── security_agent.py       # Claude Agent SDK: security audit
│   ├── modules/
│   │   ├── git_ops.py              # Git operations (branch, commit, push, merge)
│   │   ├── github_ops.py           # GitHub API via gh CLI (PRs, comments)
│   │   ├── sentry_parser.py        # Parse Sentry webhook payloads
│   │   └── logging.py              # Structured logging
│   ├── pyproject.toml
│   └── .env.sample
│
├── .github/
│   └── workflows/
│       └── ci.yml                  # Lint + test on PRs
│
├── scripts/
│   ├── start.sh                    # Start app (client + server)
│   └── start_autopilot.sh          # Start autopilot webhook server
│
├── render.yaml                     # Render deployment config
├── CLAUDE.md                       # Claude Code context file
└── .gitignore
```

## Implementation Plan

### Phase 1: Application (app/)

#### 1.1 Backend — `app/server/`

**server.py** — FastAPI app:
- `GET /api/products` — list all products (with optional category/price filters)
- `GET /api/products/{id}` — get single product
- `GET /api/search?q=...` — text search across products
- `POST /api/cart` — add to cart
- `GET /api/cart` — get cart contents
- `DELETE /api/cart/{item_id}` — remove from cart
- `GET /api/health` — health check
- CORS configured for frontend
- Sentry SDK init with FastAPI integration
- SQLite database with seed product data (25-30 products across categories: Electronics, Clothing, Home, Books, Sports)

**core/models.py** — Pydantic models:
- `Product(id, name, description, price, category, image_url, in_stock, rating)`
- `CartItem(id, product_id, quantity)`
- `SearchResult(products, total, query)`

**core/db.py** — Database:
- SQLite setup with products table
- Seed data function with 25-30 realistic products
- Use placeholder image URLs (picsum.photos or similar)

**core/search.py** — Search:
- SQLite LIKE-based search across name + description + category

**pyproject.toml** — Dependencies:
- fastapi, uvicorn, python-dotenv, sentry-sdk[fastapi]

#### 1.2 Frontend — `app/client/`

**No build step** — plain HTML/CSS/JS served by FastAPI's StaticFiles.

**index.html** — Single page with:
- Header with search bar + voice search button + cart icon
- Product grid section
- Cart sidebar/modal
- Filter controls (category dropdown, price range)

**style.css** — Clean, modern e-commerce look:
- CSS Grid for product cards
- Responsive design
- Cart slide-in panel
- Voice search button with pulse animation when recording

**app.js** — Main application logic:
- Fetch and render product grid
- Search (text input with debounce)
- Voice search using Web Speech API (SpeechRecognition)
- Add to cart / remove from cart
- Category filtering
- Price sorting
- Cart total calculation

**sentry.js** — Sentry Browser SDK initialization:
- Init with DSN from a config
- Configure traces, replays

#### 1.3 Deployment

**render.yaml**:
- Web service for FastAPI backend (serves both API and static frontend files)

### Phase 2: Self-Healing Autopilot (autopilot/)

#### 2.1 Webhook Server — `autopilot/webhook_server.py`

A FastAPI server (separate from the app) that:
- `POST /sentry-webhook` — receives Sentry issue alerts
- `POST /gh-webhook` — receives GitHub PR/check events (for merge decisions)
- `GET /health` — health check
- Runs on a configurable port (default 8002)
- Exposed via Cloudflare Tunnel so Sentry/GitHub can reach it

When a Sentry webhook arrives:
1. Parse the error details (sentry_parser.py)
2. Kick off the pipeline (pipeline.py) in the background
3. Return 200 immediately

#### 2.2 Pipeline — `autopilot/pipeline.py`

Orchestrates the full self-healing flow:

```
1. Parse Sentry error → extract stacktrace, error message, file/line
2. Run fix_agent → creates branch, applies fix, commits, pushes, creates PR
3. Wait for CI to pass (poll GitHub checks)
4. Run review_agent → reviews the PR diff
5. Run security_agent → security audit of the changes
6. If all pass → auto-merge the PR
7. Post status updates as GitHub issue/PR comments
```

#### 2.3 Agents (using Claude Agent SDK)

**fix_agent.py** — Analyze error + create fix:
```python
from claude_agent_sdk import query, ClaudeAgentOptions

options = ClaudeAgentOptions(
    system_prompt="You are a senior developer fixing a production bug...",
    allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
    cwd=repo_path,
    max_turns=20,
)
async for msg in query(prompt=f"Fix this error: {error_details}", options=options):
    # collect results
```

**review_agent.py** — PR code review:
```python
options = ClaudeAgentOptions(
    system_prompt="You are a code reviewer. Review this PR diff...",
    allowed_tools=["Read", "Bash", "Glob", "Grep"],
    cwd=repo_path,
    max_turns=10,
)
```

**security_agent.py** — Security review:
```python
options = ClaudeAgentOptions(
    system_prompt="You are a security engineer. Audit these changes for vulnerabilities...",
    allowed_tools=["Read", "Bash", "Glob", "Grep"],
    cwd=repo_path,
    max_turns=10,
)
```

#### 2.4 Modules

**modules/git_ops.py** — Git operations:
- `create_branch()`, `commit_changes()`, `push_branch()`
- `get_current_branch()`, `checkout_branch()`

**modules/github_ops.py** — GitHub operations:
- `create_pr()`, `check_pr_status()`, `merge_pr()`
- `add_pr_comment()`, `get_pr_diff()`
- Uses `gh` CLI

**modules/sentry_parser.py** — Parse Sentry webhook payload:
- Extract error type, message, stacktrace
- Extract affected file(s) and line numbers
- Format into a prompt for the fix agent

**modules/logging.py** — Structured logging:
- JSON logs per pipeline run
- Stored in `runs/{run_id}/`

#### 2.5 Dependencies — `autopilot/pyproject.toml`:
- fastapi, uvicorn, python-dotenv
- claude-agent-sdk
- pydantic

### Phase 3: CI/CD

#### .github/workflows/ci.yml
- Trigger: on PR to main
- Steps: checkout → setup Python → install deps → run ruff lint → run pytest
- Keep it simple — just enough for the demo

### Phase 4: Scripts & Config

**scripts/start.sh** — Start the app (backend + serve static files)
**scripts/start_autopilot.sh** — Start the autopilot webhook server
**CLAUDE.md** — Project context for Claude Code
**render.yaml** — Render deployment
**.gitignore** — Standard Python + Node ignores

## Naming Decision

- **ADW** (tac-7) → **autopilot** (voxstore)
- The self-healing service is called "autopilot" — clear, memorable, and distinct from the app

## Key Difference from tac-7

| Aspect | tac-7 (ADW) | voxstore (autopilot) |
|--------|-------------|----------------------|
| Agent invocation | `subprocess.run(["claude", ...])` | `claude_agent_sdk.query()` |
| Trigger | GitHub issues/comments | Sentry webhooks |
| Workflow types | Many (plan, build, test, review, ship) | Single pipeline (fix→review→security→merge) |
| Complexity | High (worktrees, state machine) | Focused (one pipeline, one purpose) |
| Frontend | Vite + TypeScript | Plain HTML/CSS/JS (no build) |

## Build Order

1. `app/server/` — backend with seed data, API, Sentry
2. `app/client/` — frontend with product grid, voice search, Sentry
3. `scripts/start.sh` — run the app locally
4. `autopilot/modules/` — shared utilities
5. `autopilot/webhook_server.py` — webhook receiver
6. `autopilot/agents/` — fix, review, security agents
7. `autopilot/pipeline.py` — orchestrator
8. `.github/workflows/ci.yml` — CI
9. `render.yaml` — deployment config
10. `CLAUDE.md` — project context
