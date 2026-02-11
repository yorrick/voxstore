# VoxStore - Self-Healing Voice-Powered Product Catalog

## Project Overview

VoxStore is a demo application showcasing autonomous self-healing capabilities. When errors occur in production, Sentry captures them and triggers an automated pipeline that uses the Claude Agent SDK to fix, review, security-audit, and auto-merge fixes — all without human intervention.

## Architecture

- **app/client/** — Vanilla JS frontend (no build step). Product grid, voice search via Web Speech API, shopping cart. Served as static files by the backend.
- **app/server/** — FastAPI backend with SQLite. Product catalog API, search, cart. Sentry SDK for error tracking.
- **autopilot/** — Self-healing service (separate from the app). Receives Sentry webhooks, runs Claude Agent SDK agents to fix errors, creates PRs, reviews them, runs security audits, and auto-merges.

## Tech Stack

- **Backend:** Python 3.10+, FastAPI, SQLite, Sentry SDK
- **Frontend:** Vanilla HTML/CSS/JS (no framework, no build step)
- **Autopilot:** Python, Claude Agent SDK (`claude-agent-sdk`), FastAPI (webhook server)
- **CI/CD:** GitHub Actions (lint + type check + test + E2E on PRs)
- **Deployment:** Render (web service)
- **Tooling:** ruff (format + lint), pyright (type check), prettier (JS/CSS/HTML format), Playwright (E2E tests)

## Key Commands

```bash
# Start the app
./scripts/start.sh

# Start the autopilot webhook server (hot reload + logs teed to autopilot/logs/autopilot.log)
# IMPORTANT: When working on the autopilot, always start the server via this script
# so both the agent and the user can inspect logs.
./scripts/start_autopilot.sh

# Server: format, lint, type check, test
cd app/server && uv run ruff format . && uv run ruff check . && uv run pyright . && uv run pytest -v

# Autopilot: format, lint, type check, test
cd autopilot && uv run ruff format . && uv run ruff check . && uv run pyright . && uv run pytest -v

# Frontend: format
npx prettier --write "app/client/**/*.{js,css,html}"

# E2E tests (starts server automatically)
npx playwright test

# E2E tests with UI
npx playwright test --ui

# Update visual snapshots
npx playwright test --update-snapshots tests/e2e/visual.spec.js
```

## Verification Rules

For EVERY change to this codebase, the following checks MUST pass before committing:

### Python changes (app/server/ or autopilot/)
1. `uv run ruff format .` — auto-format
2. `uv run ruff check .` — lint (0 errors)
3. `uv run pyright .` — type check (0 errors)
4. `uv run pytest -v` — all tests pass

### Frontend changes (app/client/)
1. `npx prettier --write "app/client/**/*.{js,css,html}"` — auto-format
2. `npx playwright test` — all E2E tests pass (starts server automatically)
3. Check browser console logs in both Chromium and Firefox for errors/warnings (use Playwright's `page.on('console')` or inspect test traces)

### CI/CD pipeline changes (.github/workflows/)
- Push the changes and verify GitHub Actions are green before considering the change complete

### Any change
- Run **all** tests (E2E, unit, etc.) — not just the ones you think are affected
- Check browser console logs in both **Chromium and Firefox** for errors, warnings, or unexpected output
- Start the app (`./scripts/start.sh`), test API endpoints, verify no errors/warnings in logs
- If UI changed, update visual snapshots: `npx playwright test --update-snapshots tests/e2e/visual.spec.js`

## Render Deployment

The app is deployed on Render. The deployment URL is configured via the `RENDER_APP_URL`
environment variable in `autopilot/.env` (e.g. `https://voxstore-xxxx.onrender.com`).

When asked to "hit the endpoint", "trigger an error", or "hit sentry-debug", use the Render
deployment URL (NOT localhost). Read the URL from the `RENDER_APP_URL` var in `autopilot/.env`.

**Important:** Before triggering a test error, the corresponding issue must be deleted in Sentry
first. Otherwise Sentry won't fire a new alert (it deduplicates by issue). Remind the user to
delete the issue in Sentry before hitting the endpoint.

```bash
# Trigger a test error on the Render deployment
curl -s $RENDER_APP_URL/sentry-debug
```

## Important Conventions

- Backend uses `uv` as the package manager
- Frontend has NO build step — plain JS served by FastAPI's StaticFiles
- The autopilot service is completely separate from the app — different port, different process
- Agents use `claude-agent-sdk` (NOT subprocess calls to `claude` CLI)
- All git/GitHub operations go through `autopilot/modules/git_ops.py` and `autopilot/modules/github_ops.py`
- Line length limit: 100 characters (ruff + prettier)
- Python target: 3.10+ (uses `str | None` syntax, not `Optional[str]`)
- All HTML elements used in E2E tests must have `data-testid` attributes

## Product Seed Data

When adding or modifying products in `app/server/core/db.py`:
- **Image URLs MUST visually match the product.** Each product's `image_url` should show the actual product (e.g., a water bottle image for a water bottle, headphones image for headphones). Do NOT use generic/random Unsplash photos.
- Use Unsplash URLs in format: `https://images.unsplash.com/photo-XXXXX?w=400&h=400&fit=crop`
- Ensure price and rating variety within product types to support meaningful search/filter testing
- After changing seed data: delete `app/server/db/voxstore.db` and `app/server/db/embeddings_*.npz` so they regenerate
- Update any hardcoded product count assertions in E2E tests (search for the old count in `tests/e2e/`)
