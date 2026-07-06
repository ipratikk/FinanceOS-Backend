---
name: review
description: Code review with surgical one-line findings (diff/file/arch/design) or comprehensive PR review via code-review:code-review. Lightweight for diffs, multi-agent for PRs.
---

# /review

Surgical review. No praise. No scope creep.

## Variants

- `/review` → current branch diff vs main (lightweight, haiku)
- `/review file <path>` → single file audit (lightweight, haiku)
- `/review pr <num>` → **Delegates to code-review:code-review** (comprehensive, 5 parallel agents)
- `/review arch` → cross-service architectural pass (sonnet) — checks the `node_api` ↔ `python_service` ↔ Postgres contract specifically
- `/review design <doc>` → design doc critique (opus)

## Output format (non-PR reviews)

One line per finding:
```
path:line: <emoji> <severity>: <problem>. <fix>.
```

Severities:
- 🔴 BLOCKER — correctness, security, data loss
- 🟠 HIGH — perf regression, missing error handling, API contract break
- 🟡 MED — design smell, missing test
- ⚪ LOW — style only (suppress unless asked)

Forbidden:
- multi-paragraph commentary
- "looks good!" / praise
- restating what the code does
- formatting nits unless they change meaning

Token rules:
- read only the diff, not surrounding context unless a finding requires it
- never paste code blocks > 5 lines in findings
- group findings by file, sort by severity desc
- skip LOW unless `--strict` requested

## PR review (delegates to code-review:code-review)

For `/review pr <num>`: invokes code-review:code-review, which runs:
- 5 parallel agents (CLAUDE.md compliance, bug detection, git history, prior PR context, code comments)
- confidence scoring (filters out scores <80)
- GitHub comment with findings

See code-review documentation for details.
