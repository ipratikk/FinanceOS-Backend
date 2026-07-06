# Create PR

Orchestrates pull request creation with inline CI validation. Claude runs each step directly,
waits for the result, and fixes any failures before proceeding. Does not delegate to a script.

## Usage

- `/create-pr` — Full workflow
- `/create-pr --skipValidation` — Skip CI steps (only when already validated)
- `/create-pr --base=<branch>` — Stacked PR against a non-main branch

---

## Execution Flow

### Phase 0: Branch check (always runs)

Run:
```bash
git branch --show-current
```

Create a new branch from latest origin/main if not already on a feature branch.
Block if branch does not follow `<type>/<description>(<jira>)` convention.
Find the JIRA ticket for the current task and add it to the branch name.

---

### Phase 1: Identify changed files

Run:
```bash
git diff --name-only origin/main...HEAD
```

Use this list to determine:
- Whether `node_api/` has changes (needs type-check + `npm test`)
- Whether `python_service/` has changes (needs `pytest`)
- Whether `docker-compose.yml`, any `Dockerfile`, or `.env.example` changed (needs a real container rebuild+restart check, not just unit tests — see Phase 4)

---

### Phase 2: Type-check (skip if `--skipValidation`)

**Note:** this repo has no configured linter (no `.eslintrc`, no `flake8`/`ruff` config) as of this writing. The closest available correctness gate for Node is TypeScript's own type-checker; Python has no equivalent step beyond its test suite.

If `node_api/` changed, run:
```bash
cd node_api && npx tsc --noEmit
```

**Rules:**
- Any `error TS...` line → fix the violation, then re-run until output is empty
- Only proceed to Phase 3 when `npx tsc --noEmit` produces zero output

---

### Phase 3: Tests (skip if `--skipValidation`)

If `node_api/` changed, run:
```bash
cd node_api && npm test
```

If `python_service/` changed, run (ensure the local Postgres is up first — `docker compose ps` from the repo root, `docker compose up -d` if not, since several test files are real integration tests against Postgres, not mocks):
```bash
cd python_service && source .venv/bin/activate && python -m pytest tests/ -q
```

**Rules:**
- Any test failure → read the failure output, fix the failing code, re-run tests for that service
- Before assuming a failure is caused by your change, check whether it's pre-existing on `main` (`git stash` your changes, re-run, compare) — this repo has at least one known pre-existing, unrelated `test_analytics.py` failure cluster from an earlier migration; don't spend a fix cycle on a regression you didn't introduce, but don't silently ignore a failure either — confirm first
- Only proceed to Phase 4 when all affected services' tests pass

---

### Phase 4: Build / deploy-readiness check (skip if `--skipValidation`)

If `node_api/` changed, run:
```bash
cd node_api && npm run build
```
Expected: exits 0, no `error TS` output.

**If `docker-compose.yml`, any `Dockerfile`, or `.env.example` changed** — these changes have previously caused real deploy-blocking regressions in this repo (both `node-api` and `python-parser` crash on boot if either encryption key env var is missing) that no unit test caught. Do an actual container verification, not just a file review:
```bash
docker compose up -d --build node-api python-parser
docker compose ps   # confirm both show "Up", not restarting/exited
docker compose logs node-api --tail 20
docker compose logs python-parser --tail 20
```
Expected: both containers `Up`, no crash traceback in the logs, `Apollo Server ready at http://localhost:4000/graphql` present in `node-api`'s log.

**Rules:**
- Any build failure or crash-on-boot → fix the error, re-run until clean
- Only proceed to Phase 5 after a clean result

---

### Phase 5: Branch sync

Run:
```bash
git fetch origin main
git rev-list --count HEAD..origin/main
```

If behind → run `git pull --rebase origin main`, then push.

Run:
```bash
git push -u origin HEAD
```

---

### Phase 6: PR creation

Inspect commits on this branch vs `origin/main`:
```bash
git log origin/main..HEAD --oneline
```

Extract JIRA key and GitHub issue # from commits/branch.

Create PR with title format `<type>(<scope>): <description> (<jira>)`:
```bash
gh pr create \
  --title "<type>(<scope>): <description> (<jira>)" \
  --body "$(cat .github/PULL_REQUEST_TEMPLATE.md)" \
  --base <base-branch>
```

**Body must follow** [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md):
- Fill all Tracking fields (JIRA Issue, GitHub Issue)
- Select Type of Change
- List Changes Made with reasons
- Complete Test Plan checklist
- Document Architecture & Design impact
- Verify Checklist items
- Add Notes for reviewers

Return the PR URL.

---

## Rules

- **Never create the PR if Phase 2, 3, or 4 produced any error or failure.**
- Fix failures inline. Do not ask "should I proceed anyway?" — fix, then proceed.
- `--skipValidation` is the only bypass. If the user did not pass it, run all phases.
