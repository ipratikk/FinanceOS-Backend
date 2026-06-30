# FinanceOS Backend

Personal finance backend — import bank/card statements, query transactions, and analyze spending.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Client (frontend / GraphQL playground)             │
└───────────────────┬─────────────────────────────────┘
                    │  GraphQL  (port 4000)
┌───────────────────▼─────────────────────────────────┐
│  Node.js API  (Apollo Server + Express)             │
│  • GraphQL queries & mutations                      │
│  • Prisma ORM → PostgreSQL                          │
└──────────┬──────────────────────┬───────────────────┘
           │  REST (internal)     │
           │  port 8000           │  SQL
┌──────────▼──────────┐  ┌───────▼────────┐  ┌───────┐
│  Python Parser      │  │  PostgreSQL 16 │  │ Redis │
│  (FastAPI)          │  └────────────────┘  └───────┘
│  • PDF/CSV parsing  │
│  • Analytics        │
│  • Redis caching    │
└─────────────────────┘
```

## Supported Statement Formats

| Institution | Type        | CSV | PDF |
|-------------|-------------|-----|-----|
| HDFC Bank   | Bank account | ✓  | ✓   |
| HDFC        | Credit card  | ✓  | ✓   |
| ICICI Bank  | Bank account | ✓  | ✓   |
| ICICI       | Credit card  | ✓  | —   |
| Amex        | Credit card  | ✓  | —   |
| Scapia      | Credit card  | —  | ✓   |

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose v2

### Setup

```bash
git clone https://github.com/ipratikk/FinanceOS-Backend.git
cd FinanceOS-Backend
./bootstrap.sh
```

All four services start in Docker. Takes ~60 s on first run (image builds).

**GraphQL API:** `http://localhost:4000/graphql`

### Local dev (node/python on host)

```bash
./bootstrap.sh --local
```

Runs postgres + redis in Docker; node and python run locally so you get hot reload.

```bash
# Terminal 1
cd node_api && npm run dev

# Terminal 2
cd python_service && source .venv/bin/activate && uvicorn main:app --reload --port 8000
```

## API Reference

Full reference at [`docs/API.md`](docs/API.md) — auto-generated from the GraphQL schema on every commit.

**Endpoint:** `POST http://localhost:4000/graphql`

Key operations:

| Operation | Type | Description |
|-----------|------|-------------|
| `banks` | Query | List all banks |
| `ledgers` | Query | List all ledgers |
| `transactions` | Query | List transactions with optional filter |
| `analytics` | Query | Spending summary by category and month |
| `uploadStatement` | Mutation | Import a PDF or CSV statement |
| `createLedger` | Mutation | Create a ledger under a bank |
| `recategorize` | Mutation | Override transaction category |

All monetary values are in **minor units** (paise for INR). Divide by 100 for display.

## Project Structure

```
FinanceOS-Backend/
├── node_api/                  # GraphQL API (Node.js, TypeScript)
│   ├── src/
│   │   ├── resolvers/         # Query + mutation resolvers
│   │   ├── schema/
│   │   │   └── typedefs.graphql   # Source of truth for the API schema
│   │   └── services/          # Business logic, calls python parser
│   └── prisma/
│       └── schema.prisma      # DB schema + migrations
├── python_service/            # Internal parser service (Python, FastAPI)
│   ├── parsers/               # One parser per bank/format
│   ├── pipeline/              # Import pipeline (dedup, categorize, persist)
│   └── analytics/             # Spending aggregations
├── docs/
│   └── API.md                 # Auto-generated API reference
├── scripts/
│   └── generate_api_docs.py   # Regenerates docs/API.md from typedefs.graphql
├── .githooks/
│   └── pre-commit             # Runs generate_api_docs.py on every commit
├── docker-compose.yml
└── bootstrap.sh               # First-time setup script
```

## Development

### Git hooks

The pre-commit hook auto-updates `docs/API.md` whenever you commit. It is activated by `bootstrap.sh`. On a fresh clone without running bootstrap:

```bash
git config core.hooksPath .githooks
```

### Database migrations

```bash
# Create a new migration (local dev only)
cd node_api && npx prisma migrate dev --name describe_change

# Apply migrations (done automatically in Docker on startup)
cd node_api && npx prisma migrate deploy
```

### Adding a parser

1. Create `python_service/parsers/<bank>_<type>.py` extending `BaseBankParser`
2. Implement `detect(content: bytes) -> bool` and `parse(content: bytes) -> list[ParsedTransaction]`
3. Register in `python_service/parsers/detector.py` (`_PARSERS` list — order matters, specific before generic)

## Services

| Service | Port | Notes |
|---------|------|-------|
| GraphQL API | 4000 | Public — used by frontend |
| Python parser | 8000 | Internal — called by node-api only |
| PostgreSQL | 5432 | |
| Redis | 6379 | Analytics cache |
