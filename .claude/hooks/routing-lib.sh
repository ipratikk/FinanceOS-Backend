#!/usr/bin/env bash
# Shared routing logic. Sourced by escalation-detector.
# Reads a prompt on stdin or $1, prints two lines:
#   AGENT=<haiku|sonnet|opus>
#   REASON=<text>
# Order matters: most specific (opus) → feature (sonnet) → mechanical (haiku) → default sonnet.

route_prompt() {
  local prompt="$1"
  local lp
  lp=$(echo "$prompt" | tr '[:upper:]' '[:lower:]')
  local agent=""
  local reason=""

  # ════════════════════════════════════════════════════════════
  # TIER 1: OPUS (architecture + cross-cutting reasoning)
  # ════════════════════════════════════════════════════════════
  if echo "$lp" | grep -qE "(design|redesign|architect) (the |a )?(parser pipeline|ingestion|dedup engine|concurrency|async|migration|schema|database|architecture)"; then
    agent="opus"; reason="architectural design keyword"
  elif echo "$lp" | grep -qE "(database (schema|migration)|db schema|prisma (schema|migration) (design|architecture))"; then
    agent="opus"; reason="db schema design"
  elif echo "$lp" | grep -qE "(redesign|restructure) (concurrency|the pipeline|ingestion)"; then
    agent="opus"; reason="pipeline/concurrency redesign"
  elif echo "$lp" | grep -qE "(concurrency|asyncio|event loop|race condition|data race|connection pool(ing)?)"; then
    agent="opus"; reason="concurrency reasoning"
  elif echo "$lp" | grep -qE "(cross-service|across (node_api|python_service)|pipeline restructure)"; then
    agent="opus"; reason="cross-service scope"
  elif echo "$lp" | grep -qE "(performance bottleneck|optimize.*algorithm|profile.*hot path|algorithmic complexity)"; then
    agent="opus"; reason="perf algorithmic"
  elif echo "$lp" | grep -qE "parser .*(broken|wrong|missing|fails|garbled|corrupt|misparses|gives wrong)"; then
    agent="opus"; reason="parser failure (root cause unknown)"
  elif echo "$lp" | grep -qE "(architecture decision|design (doc|review)|tradeoff analysis)"; then
    agent="opus"; reason="architecture decision"

  # ════════════════════════════════════════════════════════════
  # TIER 2: SONNET (feature work — must come BEFORE generic build/run verbs)
  # ════════════════════════════════════════════════════════════
  elif echo "$lp" | grep -qE "(add|build|implement|create|make) (a |an |the |new )*(resolver|mutation|query|endpoint|feature|service|parser (for|class)|graphql)"; then
    agent="sonnet"; reason="feature implementation"
  elif echo "$lp" | grep -qE "(resolver|mutation|service) (work|logic|component)"; then
    agent="sonnet"; reason="resolver/service work"
  elif echo "$lp" | grep -qE "implement (a |the |new )?[a-z]+(parser|importer|extractor|migrator|resolver|service)"; then
    agent="sonnet"; reason="implement new type"
  elif echo "$lp" | grep -qE "(write|add) (unit |integration )?tests"; then
    agent="sonnet"; reason="test writing"
  elif echo "$lp" | grep -qE "(refactor|extract|inline) (a |the )?(function|method|class|resolver|module)"; then
    agent="sonnet"; reason="medium refactor"
  elif echo "$lp" | grep -qE "(wire up|integrate|hook up|connect (the )?)"; then
    agent="sonnet"; reason="integration"

  # ════════════════════════════════════════════════════════════
  # TIER 3: HAIKU (mechanical execution)
  # ════════════════════════════════════════════════════════════
  elif echo "$lp" | grep -qE "(npm test|npm run build|npx tsc|pytest|prisma migrate)"; then
    agent="haiku"; reason="build/test command"
  elif echo "$lp" | grep -qE "^(rebuild|recompile)( |$)"; then
    agent="haiku"; reason="rebuild verb"
  elif echo "$lp" | grep -qE "^build( the )?(project|node_api|python_service|all)( |$)"; then
    agent="haiku"; reason="build verb (no feature target)"
  elif echo "$lp" | grep -qE "^run (.*test|.*parser|.*build|the cli)"; then
    agent="haiku"; reason="run command"
  elif echo "$lp" | grep -qE "(format|reformat|prettify) (this|the|file|code|all)"; then
    agent="haiku"; reason="format request"
  elif echo "$lp" | grep -qE "(fix typo|fix the typo|typo in|misspell)"; then
    agent="haiku"; reason="typo fix"
  elif echo "$lp" | grep -qE "^(commit|push|stage|git add|git status|git diff)"; then
    agent="haiku"; reason="git op"
  elif echo "$lp" | grep -qE "^(rename|move|delete|copy)( |$)"; then
    agent="haiku"; reason="file/symbol op"
  elif echo "$lp" | grep -qE "^(grep|search|find|fd|rg) "; then
    agent="haiku"; reason="search"
  elif echo "$lp" | grep -qE "(regenerate|update|refresh).*?(fixture|baseline)"; then
    agent="haiku"; reason="regen task"
  elif echo "$lp" | grep -qE "(parse the|run the parser|invoke parser|parser cli|test the parser on)"; then
    agent="haiku"; reason="parser invocation"

  # ════════════════════════════════════════════════════════════
  # DEFAULT — sonnet (NEVER opus)
  # ════════════════════════════════════════════════════════════
  else
    agent="sonnet"
    reason="default (ambiguous → sonnet, never opus)"
  fi

  echo "AGENT=$agent"
  echo "REASON=$reason"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  route_prompt "$1"
fi
