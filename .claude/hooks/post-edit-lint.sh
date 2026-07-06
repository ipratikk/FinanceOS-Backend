#!/usr/bin/env bash
# Triggered after Edit/Write. Fast per-file syntax check only — this repo has
# no configured linter (no .eslintrc, no flake8/ruff config) as of this writing,
# so this hook is deliberately narrow: it catches syntax errors immediately,
# it does not enforce style. If a linter is added later, wire it in here.

set -e

INPUT="$(cat)"
FILE=$(printf '%s' "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',d).get('file_path',''))" 2>/dev/null || true)

[ -z "$FILE" ] && exit 0
[ ! -f "$FILE" ] && exit 0

case "$FILE" in
  *.py)
    # py_compile is a fast, per-file syntax check — not a linter.
    OUTPUT=$(python3 -m py_compile "$FILE" 2>&1) || {
      printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"python syntax error in %s:\\n%s"}}\n' \
        "$(basename "$FILE")" "$(echo "$OUTPUT" | sed 's/"/\\"/g' | tr '\n' '|')"
    }
    ;;
  *)
    exit 0
    ;;
esac

exit 0
