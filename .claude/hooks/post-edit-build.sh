#!/usr/bin/env bash
# Triggered after Edit/Write on .ts files.
# Whole-project type-check via tsc --noEmit (no per-file incremental option exists
# for TypeScript the way swiftlint/swift build could scope to one package).
# Debounced with a lockfile since this is a full-project check, not per-file.

set -e

INPUT="$(cat)"
FILE=$(printf '%s' "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',d).get('file_path',''))" 2>/dev/null || true)

[ -z "$FILE" ] && exit 0
[[ ! "$FILE" =~ \.ts$ ]] && exit 0
[[ ! "$FILE" =~ /node_api/ ]] && exit 0

cd "$(git rev-parse --show-toplevel)" || exit 0

LOCK="/tmp/financeos_backend_tsc.lock"
if [ -f "$LOCK" ]; then
  if [ "$(($(date +%s) - $(stat -f %m "$LOCK" 2>/dev/null || echo 0)))" -gt 60 ]; then
    rm -f "$LOCK"
  else
    exit 0
  fi
fi
touch "$LOCK"
trap 'rm -f "$LOCK"' EXIT

OUTPUT=$(cd node_api && npx tsc --noEmit 2>&1 | grep -E "error TS" | head -10)

if [ -n "$OUTPUT" ]; then
  printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"TYPE CHECK FAIL after edit to %s:\\n%s\\n→ delegate to haiku-agent to fix, escalate to sonnet if cross-file."}}\n' \
    "$FILE" "$(echo "$OUTPUT" | sed 's/"/\\"/g' | tr '\n' '|')"
fi

exit 0
