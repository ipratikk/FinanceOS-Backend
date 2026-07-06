# `.claude/` — FinanceOS-Backend Agent Workflow

Ported from the `FinanceOS` (client) repo's `.claude/` setup and adapted for this
repo's stack (Node/TypeScript `node_api` + Python `python_service`, no Swift/Xcode).

```
.claude/
├── agents/           ← haiku / sonnet / opus model definitions
├── commands/         ← user-facing /slash workflows (create-pr)
├── skills/           ← reusable skill blueprints (commit, review)
├── hooks/            ← auto-routing + summarizers
├── settings.json     ← hook + permission wiring
└── README.md
```

## Quick start

| If you want to... | Run |
|---|---|
| Review the current diff | `/review` (haiku) |
| Commit grouped by service | `/commit` (haiku) |
| Create a PR with full validation | `/create-pr` (see the command file for phases) |

## Hard cost discipline

Bottom line: **opus only plans, haiku executes**. See each agent's `.md` file
for its exact use/forbidden lists and escalation rules.

## Known gaps vs. the FinanceOS setup this was ported from

- **No configured linter.** Neither `node_api` (no `.eslintrc`/`eslint.config.*`)
  nor `python_service` (no `flake8`/`ruff` config) has a linter set up. The
  `post-edit-lint.sh` hook and `/create-pr`'s Phase 2 are scoped accordingly —
  Python gets a fast per-file syntax check (`py_compile`, not a linter);
  TypeScript gets `tsc --noEmit` as the closest available correctness gate.
  If a real linter is added later, wire it into both.
- **No macOS/Xcode build step** (this repo has none) — replaced with
  `npm run build` (Node) and a real `docker compose up -d --build` +
  log-inspection check specifically when `docker-compose.yml`/`Dockerfile`/env
  vars change, since that exact class of change has caused real deploy-blocking
  container crash-on-boot regressions in this repo before, undetected by unit
  tests alone.
- **No `graphify`-equivalent tooling** — the FinanceOS agents reference
  `graphify-out/wiki` for token-efficient cross-module lookups; this repo has
  no equivalent, so those references were dropped rather than ported as dead
  weight.

## Adding a new agent / skill / command

- Agents: `.claude/agents/<name>.md` with frontmatter `name`, `description`, `model`, `tools`
- Skills: `.claude/skills/<name>/SKILL.md` with frontmatter `name`, `description`
- Commands: `.claude/commands/<name>.md` with frontmatter `description`, `allowed-tools`, `argument-hint`
- Hooks: `.claude/hooks/<name>.sh` (executable) + wired in `settings.json`

## Hooks active

- **UserPromptSubmit** → `escalation-detector.sh`: annotates each prompt with a routing hint
- **PostToolUse(Edit|Write)** → `post-edit-lint.sh` (Python syntax check) + `post-edit-build.sh` (TypeScript type-check, `node_api/` only)
- **PostToolUse(Bash)** → `summarize-failure.sh`: collapses verbose `npm`/`pytest`/`docker compose` failures
