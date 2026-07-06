## Tracking

<!-- REQUIRED: Fill in the JIRA field below. PRs missing this will be blocked. -->

- **JIRA Issue:** [REPLACE-WITH-KEY](https://ipratikgoel.atlassian.net/browse/REPLACE-WITH-KEY) <!-- e.g. [FINOS-5](https://ipratikgoel.atlassian.net/browse/FINOS-5) — must match pattern [A-Z]+-[0-9]+ -->

## Summary

Please provide a brief summary of the changes in this PR.

- What changed?
- Why did it change?
- What problem does it solve?

## Type of Change

Please select the type of change:

- [ ] **Feature** — New functionality added
- [ ] **Bug Fix** — Issue fixed
- [ ] **Refactoring** — Code reorganized without changing behavior
- [ ] **Performance** — Speed or efficiency improvement
- [ ] **Documentation** — Docs added or updated
- [ ] **Dependencies** — Package updates or dependency changes
- [ ] **Test** — Test coverage added or improved

## Changes Made

Describe the specific changes:

- [ ] Changed file A (reason)
- [ ] Added file B (reason)
- [ ] Modified service X (reason)

## Test Plan

How was this tested?

- [ ] Local CI passed (`/create-pr`)
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated (against real Postgres, not mocked — this repo's convention)
- [ ] Manual smoke test completed (describe)
- [ ] Parser tests passed (if applicable)
- [ ] No regressions observed

### Screenshots/Logs

If applicable, add logs demonstrating the changes:

```
Paste logs or test output here
```

## Architecture & Design

If this change affects architecture, explain the approach:

- [ ] No architecture impact
- [ ] Extension of existing pattern
- [ ] New pattern introduced (explain why)
- [ ] Breaking change (explain migration)
- [ ] Touches `docker-compose.yml`/`Dockerfile`/env vars — confirm both `node-api` and `python-parser` still boot cleanly (see `/create-pr`'s Phase 4)

## Checklist

- [ ] TypeScript type-check passes (`npx tsc --noEmit` in `node_api`)
- [ ] All tests pass (`npm test`, `pytest tests/`)
- [ ] Node build succeeds (`npm run build`)
- [ ] Commit message follows Conventional Commits
- [ ] PR title is descriptive
- [ ] Documentation updated (if needed)
- [ ] No unnecessary refactoring mixed with feature
- [ ] No credentials, real key material, or `.env` files committed

## Notes

Any additional notes for reviewers?

- Migration steps needed?
- Breaking changes to document?
- Follow-up work?
- Design decisions to discuss?

---

**Reviewers:** Please verify:
- [ ] Changes align with architecture
- [ ] Code quality standards met
- [ ] Test coverage adequate (real integration tests where the change touches Postgres or cross-service contracts)
- [ ] No scope creep
- [ ] No unnecessary coupling introduced
