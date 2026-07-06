#!/usr/bin/env bash
# UserPromptSubmit hook. Routes the user's prompt and adds context for the agent.
# Uses shared routing-lib.sh.

set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/routing-lib.sh"

INPUT="$(cat)"
PROMPT=$(printf '%s' "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('prompt',''))" 2>/dev/null || true)
[ -z "$PROMPT" ] && exit 0

RESULT=$(route_prompt "$PROMPT")
AGENT=$(echo "$RESULT" | grep "^AGENT=" | cut -d= -f2)
REASON=$(echo "$RESULT" | grep "^REASON=" | cut -d= -f2-)

[ -z "$AGENT" ] && exit 0

printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"ROUTING HINT: %s-agent — %s. Avoid opus unless reasoning genuinely required (.claude/agents/opus-agent.md)."}}\n' \
  "$AGENT" "$REASON"

exit 0
