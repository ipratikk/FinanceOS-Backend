#!/usr/bin/env python3
"""Generate docs/API.md from node_api/src/schema/typedefs.graphql."""

import re
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / "node_api" / "src" / "schema" / "typedefs.graphql"
OUTPUT_PATH = REPO_ROOT / "docs" / "API.md"

DESCRIPTIONS = {
    "health": "Returns server status string.",
    "banks": "List all banks.",
    "ledger": "Fetch single ledger by ID.",
    "ledgers": "List all ledgers across all banks.",
    "transactions": "List transactions, optionally filtered by ledger and/or criteria.",
    "analytics": "Spending summary for a date range, optionally scoped to a ledger.",
    "uploadStatement": "Upload a bank statement file (PDF or CSV) to import transactions. Uses `multipart/form-data`.",
    "createLedger": "Create a new ledger under an existing bank.",
    "updateLedger": "Update ledger display name, kind, or last4.",
    "deleteLedger": "Delete a ledger and all its transactions.",
    "recategorize": "Override the category on a transaction.",
    "deleteTransaction": "Delete a single transaction by ID.",
    "createBank": "Register a new bank.",
    "clearAllData": "Wipe all banks, ledgers, and transactions. Irreversible.",
}


def parse_schema(text: str) -> dict:
    text = re.sub(r'""".*?"""', '', text, flags=re.DOTALL)
    text = re.sub(r'#.*', '', text)

    result: dict = {
        "scalars": [],
        "enums": {},
        "types": {},
        "inputs": {},
        "queries": [],
        "mutations": [],
    }

    block_re = re.compile(
        r'(enum|type|input)\s+(\w+)(?:\s+[^{]*)?\s*\{([^}]*)\}',
        re.DOTALL,
    )

    for m in block_re.finditer(text):
        kind, name, body = m.group(1), m.group(2), m.group(3)
        lines = [l.strip() for l in body.strip().splitlines() if l.strip()]

        if kind == "enum":
            result["enums"][name] = lines
        elif kind == "type" and name == "Query":
            result["queries"] = [_parse_field(l) for l in lines]
        elif kind == "type" and name == "Mutation":
            result["mutations"] = [_parse_field(l) for l in lines]
        elif kind == "type":
            result["types"][name] = [_parse_field(l) for l in lines]
        elif kind == "input":
            result["inputs"][name] = [_parse_simple_field(l) for l in lines]

    # scalars have no braces
    for m in re.finditer(r'^scalar\s+(\w+)\s*$', text, re.MULTILINE):
        if m.group(1) not in result["scalars"]:
            result["scalars"].append(m.group(1))

    return result


def _parse_field(line: str) -> dict:
    m = re.match(r'(\w+)(\([^)]*\))?\s*:\s*(.+)', line)
    if not m:
        return {"name": line, "args": [], "type": ""}
    args = []
    if m.group(2):
        for a in re.findall(r'(\w+)\s*:\s*([^\s,)]+)', m.group(2)):
            args.append({"name": a[0], "type": a[1]})
    return {"name": m.group(1), "args": args, "type": m.group(3).strip()}


def _parse_simple_field(line: str) -> dict:
    m = re.match(r'(\w+)\s*:\s*(.+)', line)
    if not m:
        return {"name": line, "type": ""}
    return {"name": m.group(1), "type": m.group(2).strip()}


def generate_md(schema: dict) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out: list[str] = [
        "# FinanceOS API Reference",
        "",
        f"> Auto-generated {now} from `node_api/src/schema/typedefs.graphql`. Do not edit manually.",
        "",
        "## Endpoint",
        "",
        "| Protocol | URL |",
        "|----------|-----|",
        "| GraphQL | `POST http://localhost:4000/graphql` |",
        "| Health check | `GET http://localhost:4000/health` |",
        "",
        "> All GraphQL operations go to `POST /graphql`. Send JSON body `{\"query\": \"...\"}` or use a GraphQL client.",
        "",
        "## Money",
        "",
        "All monetary values use the `Money` type: `{ value: Int!, currencyCode: CurrencyCode! }`. "
        "`value` is in **minor units** (paise for INR, cents for USD/EUR/GBP). Divide by 100 for display.",
        "",
        "---",
        "",
        "## Queries",
        "",
    ]

    for f in schema["queries"]:
        out.append(f"### `{f['name']}`")
        if f["name"] in DESCRIPTIONS:
            out.append(f"_{DESCRIPTIONS[f['name']]}_")
        out.append("")
        if f["args"]:
            out.append("**Arguments:**")
            out.append("")
            for a in f["args"]:
                out.append(f"- `{a['name']}: {a['type']}`")
            out.append("")
        out.append(f"**Returns:** `{f['type']}`")
        out.append("")

    out += ["---", "", "## Mutations", ""]

    for f in schema["mutations"]:
        out.append(f"### `{f['name']}`")
        if f["name"] in DESCRIPTIONS:
            out.append(f"_{DESCRIPTIONS[f['name']]}_")
        out.append("")
        if f["args"]:
            out.append("**Arguments:**")
            out.append("")
            for a in f["args"]:
                out.append(f"- `{a['name']}: {a['type']}`")
            out.append("")
        out.append(f"**Returns:** `{f['type']}`")
        out.append("")

    out += ["---", "", "## Types", ""]

    for tname, fields in schema["types"].items():
        out.append(f"### `{tname}`")
        out.append("")
        out.append("| Field | Type |")
        out.append("|-------|------|")
        for f in fields:
            out.append(f"| `{f['name']}` | `{f['type']}` |")
        out.append("")

    out += ["---", "", "## Input Types", ""]

    for iname, fields in schema["inputs"].items():
        out.append(f"### `{iname}`")
        out.append("")
        out.append("| Field | Type |")
        out.append("|-------|------|")
        for f in fields:
            out.append(f"| `{f['name']}` | `{f['type']}` |")
        out.append("")

    out += ["---", "", "## Enums", ""]

    for ename, values in schema["enums"].items():
        out.append(f"### `{ename}`")
        out.append("")
        for v in values:
            out.append(f"- `{v}`")
        out.append("")

    if schema["scalars"]:
        out += ["---", "", "## Scalars", ""]
        for s in schema["scalars"]:
            if s == "Upload":
                out.append(f"- `{s}` — file upload via multipart/form-data (used in `uploadStatement`)")
            else:
                out.append(f"- `{s}`")
        out.append("")

    return "\n".join(out) + "\n"


if __name__ == "__main__":
    schema_text = SCHEMA_PATH.read_text()
    schema = parse_schema(schema_text)
    md = generate_md(schema)
    OUTPUT_PATH.write_text(md)
    print(f"Generated {OUTPUT_PATH.relative_to(REPO_ROOT)}")
