---
name: commit
description: Create clean, service-grouped git commits using caveman:caveman-commit for deterministic message generation. Layer: node-api, python-service, infra, claude-config, docs, tests, misc.
---

# /commit

Groups unstaged changes by service/layer. For each group, invokes `caveman:caveman-commit` for ultra-compressed Conventional Commits messages.

**Default agent:** haiku (mechanical grouping) / sonnet (mixed-layer calls)

## Workflow

1. Collect modified files (unstaged + staged)
2. Group by layer (see below)
3. For each group:
   - Stage files
   - **Invoke caveman:caveman-commit** to generate message
   - Create commit

## Usage

- `/commit` → auto-group by layer, commit each group (requires caveman:caveman-commit)
- `/commit --dry-run` → show groups without committing

## Grouping layers (in order)

1. `node_api/` — node-api
2. `python_service/` — python-service
3. `docker-compose.yml`, `Dockerfile`, `.env.example` — infra
4. `.claude/` — claude-config
5. `docs/` — docs
6. `*.test.ts`, `tests/` — tests
7. catch-all — misc

## Safety rules

- confirm before committing if changes appear destructive
- never commit `.env`, generated files, debug prints, or real key material
- call out suspicious changes before staging (especially anything under `node_api/.env`, `python_service/.env`, or files matching `*_PRIVATE_KEY`/`*_ENCRYPTION_KEY` patterns)

## After commits

Return: list of created commits only. No essays.
