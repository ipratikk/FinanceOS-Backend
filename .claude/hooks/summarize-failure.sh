#!/usr/bin/env bash
# PostToolUse hook for Bash. Detects failed builds/tests and surfaces ONE-LINE summary.
# Prevents the main thread from re-reading huge npm/pytest/docker logs.

set -e

INPUT="$(cat)"
EXIT_CODE=$(printf '%s' "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_response',d).get('exit_code',0))" 2>/dev/null || echo 0)
CMD=$(printf '%s' "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',d).get('command',''))" 2>/dev/null || true)
OUTPUT=$(printf '%s' "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_response',d).get('output','')[:8000])" 2>/dev/null || true)

[ "$EXIT_CODE" = "0" ] && exit 0
[ -z "$CMD" ] && exit 0

# Only summarize for known commands
case "$CMD" in
  *npm\ test*|*npm\ run\ build*|*npx\ tsc*)
    ERR=$(echo "$OUTPUT" | grep -E "error TS|✖|FAIL" | head -3 | tr '\n' '|')
    [ -n "$ERR" ] && printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"NODE BUILD/TEST FAIL: %s"}}\n' "$(echo "$ERR" | sed 's/"/\\"/g')"
    ;;
  *pytest*)
    ERR=$(echo "$OUTPUT" | grep -E "^FAILED|^ERROR" | head -5 | tr '\n' '|')
    [ -n "$ERR" ] && printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"PYTEST FAIL: %s"}}\n' "$(echo "$ERR" | sed 's/"/\\"/g')"
    ;;
  *docker\ compose*)
    ERR=$(echo "$OUTPUT" | grep -iE "error|exited with code" | head -3 | tr '\n' '|')
    [ -n "$ERR" ] && printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"DOCKER COMPOSE FAIL: %s"}}\n' "$(echo "$ERR" | sed 's/"/\\"/g')"
    ;;
esac

exit 0
