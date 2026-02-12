# VoxStore

A voice-powered product catalog with an autonomous self-healing pipeline. The app itself is intentionally simple — a FastAPI backend and vanilla JavaScript frontend. The interesting part is what happens when it breaks: a separate service catches production errors from Sentry and spins up Claude Code agents to fix them, review the fix, audit it for security issues, and merge the PR. No human in the loop.

## The App

A straightforward e-commerce catalog. FastAPI serves a REST API backed by SQLite, and a plain HTML/CSS/JS frontend talks to it. No React, no build step — the backend serves the static files directly.

**Backend** (`app/server/`): Product CRUD, semantic search (BGE embeddings via OpenRouter), shopping cart, and voice search support. The voice pipeline transcribes audio with ElevenLabs, then uses an LLM (Gemini Flash) to extract structured search intent from the transcript — things like category, minimum rating, and sort order.

**Frontend** (`app/client/`): Product grid with filters, a shopping cart, and a voice search button that uses the Web Speech API (with a WebSocket transcription fallback). Press Alt or click the mic to search by voice.

The app is deployed on [Render](https://render.com) and reports errors to [Sentry](https://sentry.io).

## The Autopilot

This is the self-healing service. It runs separately from the app (different process, different port, different deployment) and does one thing: receives Sentry webhooks and orchestrates a pipeline of Claude Code agents to fix the error autonomously.

### How It Works

```
Production error
      |
      v
Sentry captures it, fires a webhook
      |
      v
Autopilot receives the webhook (POST /webhook/sentry)
      |
      v
Creates an isolated git worktree on a new branch
      |
      v
Code Fix Agent (Claude Opus, up to 50 turns)
  - Queries Sentry via MCP server for full error details + stacktrace
  - Reads the relevant source files
  - Applies a minimal fix
  - Runs the full test suite (ruff, pyright, pytest, Playwright)
  - Commits, pushes, opens a PR
      |
      v
Waits for CI (polls GitHub Actions for up to 5 minutes)
      |
      v
Code Review Agent (Claude Opus, up to 20 turns)
  - Reads the PR diff
  - Checks for bugs, security issues, CLAUDE.md compliance
  - Scores each finding 0-100, filters below 75 to avoid noise
  - Comments on the PR
      |
      v
Security Agent (Claude Opus, up to 10 turns)
  - Audits the diff for SQL injection, XSS, path traversal, etc.
  - Posts a security assessment on the PR
      |
      v
If CI passes + review approves + security passes:
  Auto-merge via squash
Otherwise:
  Leave the PR open for manual review
```

### The Agents

All three agents use the [Claude Agent SDK](https://docs.anthropic.com/en/docs/claude-code/sdk) (`claude-agent-sdk` Python package). They run Claude Opus in `bypassPermissions` mode — fully autonomous, no human prompts.

The agent prompts are inspired by Anthropic's official [feature development](https://github.com/anthropics/claude-code/tree/main/.claude/plugins/feature-dev) and [code review](https://github.com/anthropics/claude-code/tree/main/.claude/plugins/code-review) plugin prompts for Claude Code:

- **Code Fix Agent** (`autopilot/agents/code_fix_agent.py`): Has a phased workflow — investigate via Sentry MCP, explore the codebase, apply a minimal fix, verify with the full test suite, create a PR. Gets access to the Sentry MCP server so it can pull error details and stacktraces directly.

- **Code Review Agent** (`autopilot/agents/code_review_agent.py`): Reviews the PR diff using `gh` CLI. Looks for bugs, security issues, and CLAUDE.md compliance. Uses a confidence scoring system (0-100) and only reports findings above 75 to filter out false positives.

- **Security Agent** (`autopilot/agents/security_agent.py`): Audits the diff for OWASP-style vulnerabilities. Read-only — can only use `Read`, `Glob`, and `Grep`. Returns PASS/FAIL with risk level and findings.

### Pipeline Details

The pipeline (`autopilot/pipeline.py`) manages the full lifecycle:

1. Creates a git worktree at `trees/autopilot/fix-{issue_id}` for isolation
2. Runs the fix agent, which creates the PR
3. Cleans up the worktree
4. Polls CI via `gh pr checks`
5. Runs review and security agents in sequence
6. Auto-merges if everything passes, or leaves a comment explaining why not

Webhooks are deduplicated by issue title — if a pipeline is already running for an issue, duplicate webhooks are ignored.

## Project Structure

```
voxstore/
  app/
    client/          Vanilla JS frontend (HTML, CSS, JS — no build step)
    server/          FastAPI backend (SQLite, Sentry SDK, embeddings)
  autopilot/
    agents/          Claude Agent SDK agent definitions
    modules/         Git, GitHub, Sentry, and logging helpers
    models/          Pydantic models (SentryIssue, etc.)
    webhook_server.py  FastAPI server that receives Sentry webhooks
    pipeline.py      Orchestrates fix -> review -> security -> merge
  tests/e2e/         Playwright tests (Chromium + Firefox)
  scripts/           start.sh, start_autopilot.sh
  .github/workflows/ CI pipeline (lint, typecheck, test, E2E)
```

## Running It

```bash
# Start the app (backend + frontend on :8000)
./scripts/start.sh

# Start the autopilot webhook server (on :8002)
./scripts/start_autopilot.sh
```

The autopilot needs a way to receive webhooks from Sentry — in development, you can use a Cloudflare Tunnel or ngrok to expose port 8002.

### Environment Variables

**App** (`app/server/.env`):
- `OPENROUTER_API_KEY` — for embeddings and LLM extraction
- `SENTRY_DSN` — Sentry error tracking (only active on Render)

**Autopilot** (`autopilot/.env`):
- `ANTHROPIC_API_KEY` — powers the Claude agents
- `SENTRY_AUTH_TOKEN` — Sentry API access (used by the MCP server)
- `SENTRY_WEBHOOK_SECRET` — HMAC-SHA256 verification of incoming webhooks
- `GITHUB_PAT` — GitHub token for creating PRs and merging
- `RENDER_APP_URL` — the deployed app URL
- `REPO_PATH` — path to the git repo root

## Tech Stack

- **Backend:** Python, FastAPI, SQLite, Sentry SDK
- **Frontend:** HTML, CSS, vanilla JavaScript
- **Autopilot:** Python, Claude Agent SDK, Sentry MCP Server
- **Search:** BGE Large v1.5 embeddings via OpenRouter
- **Voice:** ElevenLabs transcription, Gemini Flash for intent extraction
- **CI:** GitHub Actions (ruff, pyright, pytest, Playwright)
- **Deployment:** Render
