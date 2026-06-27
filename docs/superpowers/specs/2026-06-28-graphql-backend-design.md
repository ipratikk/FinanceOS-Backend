# FinanceOS GraphQL Backend — Design Spec

**Date:** 2026-06-28
**Status:** Approved
**Branch:** feat/graphql-backend

---

## Problem

FinanceOS is currently a native macOS SwiftUI app with all logic embedded in-process: GRDB/SQLite for persistence, Swift packages for parsing (FinanceParsers), and analytics (FinanceIntelligence). This architecture limits:

- Reuse of parsing/analytics logic across clients
- AI/ML integration (Python ecosystem)
- Future web or mobile clients
- Separation of concerns between UI and data intelligence

## Goal

Refactor FinanceOS into a thin SwiftUI client backed by a GraphQL API. The backend owns persistence, parsing, analytics, and AI. The SwiftUI app uploads files and queries/mutates data via GraphQL.

---

## Architecture

```
SwiftUI App (thin client)
    │
    │  GraphQL over HTTP (queries + mutations)
    │  File upload via multipart mutation
    ▼
┌─────────────────────────────────────┐
│  Node.js — Apollo Server 4          │  port 4000
│  ├── GraphQL schema (SDL-first)     │
│  ├── Resolvers                      │
│  ├── graphql-upload (multipart)     │
│  ├── Prisma ORM → PostgreSQL        │
│  └── HTTP client → Python service  │
└──────────────┬──────────────────────┘
               │  Internal REST
               ▼
┌─────────────────────────────────────┐
│  Python — FastAPI                   │  port 8000
│  ├── POST /parse                    │
│  ├── POST /import                   │
│  ├── GET  /analytics                │
│  └── POST /categorize (AI)         │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
   PostgreSQL       Redis
   port 5432        port 6379
   (source of       (analytics cache,
    truth)           TTL 5 min)
```

### File Import Data Flow

1. SwiftUI sends `uploadStatement(ledgerId, file)` GraphQL mutation
2. Apollo Server receives multipart file, forwards binary + metadata to `POST /parse`
3. Python detects bank format, parses CSV/TXT → `ParsedTransaction[]`
4. Python deduplicates via `(ledgerId, sourceFingerprint)` unique constraint
5. Python writes new transactions to Postgres
6. Node resolves updated `ImportResult` (counts + ledger) back to SwiftUI

---

## GraphQL Schema

SDL-first. Defined in `node_api/src/schema/typedefs.graphql`.

```graphql
scalar Upload

type Bank {
  id: ID!
  name: String!
  code: String!
  ledgers: [Ledger!]!
}

type Ledger {
  id: ID!
  displayName: String!
  kind: LedgerKind!
  last4: String
  bank: Bank!
  transactions(filter: TransactionFilter): [Transaction!]!
  balance: Float!
}

enum LedgerKind {
  BANK_ACCOUNT
  CREDIT_CARD
  LOAN
  WALLET
  CRYPTO
  INVESTMENT
}

type Transaction {
  id: ID!
  date: String!
  narration: String!
  amount: Float!
  ledger: Ledger!
  category: String
  merchant: String
  sourceFingerprint: String!
}

type SpendingSummary {
  totalSpend: Float!
  totalIncome: Float!
  netFlow: Float!
  byCategory: [CategoryBreakdown!]!
  byMonth: [MonthlyBreakdown!]!
}

type CategoryBreakdown {
  category: String!
  amount: Float!
  count: Int!
}

type MonthlyBreakdown {
  month: String!
  spend: Float!
  income: Float!
}

type ImportResult {
  imported: Int!
  duplicates: Int!
  errors: [String!]!
  ledger: Ledger!
}

input TransactionFilter {
  from: String
  to: String
  category: String
  minAmount: Float
  maxAmount: Float
}

input CreateLedgerInput {
  displayName: String!
  kind: LedgerKind!
  last4: String
  bankId: ID!
}

input UpdateLedgerInput {
  displayName: String
  kind: LedgerKind
  last4: String
}

type Query {
  banks: [Bank!]!
  ledger(id: ID!): Ledger
  ledgers: [Ledger!]!
  transactions(ledgerId: ID, filter: TransactionFilter): [Transaction!]!
  analytics(ledgerId: ID, from: String, to: String): SpendingSummary!
}

type Mutation {
  uploadStatement(ledgerId: ID!, file: Upload!): ImportResult!
  createLedger(input: CreateLedgerInput!): Ledger!
  updateLedger(id: ID!, input: UpdateLedgerInput!): Ledger!
  deleteLedger(id: ID!): Boolean!
  recategorize(transactionId: ID!, category: String!): Transaction!
}
```

Schema is versioned and can be extended. No breaking changes without migration.

---

## Node.js Service

**Stack:** TypeScript, Apollo Server 4, Express, Prisma, `graphql-upload`

```
node_api/
├── src/
│   ├── schema/
│   │   └── typedefs.graphql
│   ├── resolvers/
│   │   ├── bank.ts
│   │   ├── ledger.ts
│   │   ├── transaction.ts
│   │   ├── analytics.ts
│   │   └── upload.ts
│   ├── services/
│   │   └── python.ts          # Axios client for FastAPI
│   ├── prisma/
│   │   └── schema.prisma
│   └── index.ts
├── package.json
└── tsconfig.json
```

**Responsibilities:**
- Own GraphQL schema and resolvers
- Forward file uploads to Python parser
- Own Postgres reads for queries (transactions, ledgers, banks)
- Delegate all writes and analytics computation to Python

**Node does NOT:**
- Parse files
- Run analytics computations
- Contain business logic beyond GraphQL resolution

---

## Python Service

**Stack:** Python 3.12, FastAPI, SQLAlchemy (async), asyncpg, redis-py, pandas

```
python_service/
├── parsers/
│   ├── base.py                # BaseBankParser ABC
│   ├── detector.py            # Format auto-detection by content/filename
│   ├── hdfc_bank_txt.py       # Port of HDFCBankTXTNormalizer.swift
│   ├── hdfc_card_csv.py       # Port of HDFCCardCSVNormalizer.swift
│   ├── icici_bank_csv.py      # Port of ICICIBankCSVNormalizer.swift
│   ├── icici_card_csv.py      # Port of ICICICardCSVNormalizer.swift
│   ├── amex_card_csv.py       # Port of AmexCardCSVNormalizer.swift
│   ├── axis_bank_csv.py       # Port of AxisBankCSVNormalizer.swift
│   ├── axis_card_csv.py       # Port of AxisCardCSVNormalizer.swift
│   ├── sbi_bank_csv.py        # Port of SBIBankCSVNormalizer.swift
│   └── sbi_card_csv.py        # Port of SBICardCSVNormalizer.swift
├── pipeline/
│   ├── mapper.py              # ParsedTransaction → DB model
│   └── deduplicator.py        # sourceFingerprint check before insert
├── analytics/
│   └── spending.py            # Port of GRDBSpendingService.swift
├── ai/
│   └── categorizer.py         # Rule-based now, ML-ready interface
├── models/
│   └── schemas.py             # Pydantic request/response models
├── cache.py                   # Redis cache helpers
├── database.py                # asyncpg connection pool (no ORM)
└── main.py                    # FastAPI app + route registration
```

**Endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/parse` | Multipart file → `ParsedTransaction[]`. Detects bank, applies parser. |
| POST | `/import` | `ParsedTransaction[]` → dedup + Postgres insert. Returns counts. |
| GET | `/analytics` | Spending summary. Cached in Redis (TTL 5 min). |
| POST | `/categorize` | Batch categorization. Rule-based now, AI pipeline later. |
| GET | `/health` | Liveness check. |

**Deduplication:** `(ledger_id, source_fingerprint)` unique constraint at Postgres level. Python pre-checks with `SELECT` before bulk insert to return accurate `duplicates` count rather than catching constraint errors.

**sourceFingerprint:** Plain pipe-delimited string, no hashing. Format varies slightly by bank but follows the pattern established in the Swift normalizers:
- Credit/debit split parsers: `"{date}|{description}|{creditMinorUnits}|{debitMinorUnits}"`
- Single amount parsers: `"{date}|{description}|{amountMinorUnits}"`
Each Python parser mirrors its Swift counterpart's exact fingerprint format to ensure cross-platform dedup consistency.

---

## Database Schema (Prisma / PostgreSQL)

```prisma
model Bank {
  id      String   @id @default(uuid())
  name    String
  code    String   @unique
  ledgers Ledger[]
}

model Ledger {
  id           String        @id @default(uuid())
  displayName  String
  kind         LedgerKind
  last4        String?
  bankId       String
  bank         Bank          @relation(fields: [bankId], references: [id])
  transactions Transaction[]
  createdAt    DateTime      @default(now())
  updatedAt    DateTime      @updatedAt
}

model Transaction {
  id                String   @id @default(uuid())
  date              DateTime
  narration         String
  amount            Float
  ledgerId          String
  ledger            Ledger   @relation(fields: [ledgerId], references: [id])
  category          String?
  merchant          String?
  sourceFingerprint String
  createdAt         DateTime @default(now())

  @@unique([ledgerId, sourceFingerprint])
  @@index([ledgerId, date])
  @@index([category])
}

enum LedgerKind {
  BANK_ACCOUNT
  CREDIT_CARD
  LOAN
  WALLET
  CRYPTO
  INVESTMENT
}
```

**Migrations:** Prisma owns all schema migrations. Python uses `asyncpg` directly with raw SQL — no ORM, no Alembic. Single migration authority prevents schema drift between services.

---

## Redis Usage

| Key Pattern | Value | TTL |
|-------------|-------|-----|
| `analytics:{ledger_id}:{from}:{to}` | JSON SpendingSummary | 5 min |
| `analytics:all:{from}:{to}` | JSON SpendingSummary | 5 min |

Cache invalidated on any successful import to the relevant ledger.

---

## Docker Compose

```yaml
version: "3.9"
services:
  node-api:
    build: ./node_api
    ports: ["4000:4000"]
    environment:
      DATABASE_URL: postgresql://financeOS:financeOS@postgres:5432/financeOS
      PYTHON_SERVICE_URL: http://python-parser:8000
      NODE_ENV: development
    depends_on: [postgres, redis]
    volumes:
      - ./node_api/src:/app/src   # hot reload in dev

  python-parser:
    build: ./python_service
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql+asyncpg://financeOS:financeOS@postgres:5432/financeOS
      REDIS_URL: redis://redis:6379
    depends_on: [postgres, redis]
    volumes:
      - ./python_service:/app     # hot reload via uvicorn --reload

  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    environment:
      POSTGRES_USER: financeOS
      POSTGRES_PASSWORD: financeOS
      POSTGRES_DB: financeOS
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

volumes:
  pgdata:
```

**Start:** `docker compose up --build`
**GraphQL playground:** `http://localhost:4000/graphql`
**Python docs:** `http://localhost:8000/docs`

---

## SwiftUI Thin-Client Changes

The SwiftUI app (`Apps/FinanceOSMac`) changes minimally:

1. **Remove:** All GRDB/SQLite dependencies, `FinanceParsers` import, `FinanceIntelligence` import
2. **Add:** `Apollo` iOS SDK (Swift Package) or lightweight `URLSession`-based GraphQL client
3. **`AppContainer`:** Vends `GraphQLClient` instead of repositories. ViewModels receive `GraphQLClient` via `init`.
4. **ViewModels:** Replace `repository.fetch()` calls with `graphqlClient.query(...)`. Presentation models (`TransactionRow`, etc.) unchanged.
5. **Import flow:** `ImportViewModel` sends `uploadStatement` mutation with file data instead of calling local parser pipeline.

ViewModel interfaces stay the same. Only the data source changes.

---

## Repo Structure After Refactor

Two separate repositories. iOS and backend have independent toolchains, CI, and release cycles. Node + Python stay together — they share schema, fixtures, and deploy as one Docker Compose unit.

### `financeos-ios` (renamed from current `FinanceOS` repo)

```
financeos-ios/
├── Apps/
│   └── FinanceOSMac/          # SwiftUI thin client (Apollo iOS SDK)
├── Packages/
│   ├── FinanceCore/           # Keep: Swift models for UI presentation layer
│   ├── FinanceUI/             # Keep: Design system / FDS tokens
│   └── FinanceTesting/        # Keep: UI test helpers, mock GraphQL responses
│   # FinanceParsers — DELETED (logic moved to financeos-backend)
│   # FinanceIntelligence — DELETED (logic moved to financeos-backend)
├── FinanceOS.xcworkspace
├── CLAUDE.md
└── docs/
```

### `financeos-backend` (new repo)

```
financeos-backend/
├── node_api/                  # Apollo Server 4 + Prisma + TypeScript
│   ├── src/
│   │   ├── schema/
│   │   │   └── typedefs.graphql
│   │   ├── resolvers/
│   │   │   ├── bank.ts
│   │   │   ├── ledger.ts
│   │   │   ├── transaction.ts
│   │   │   ├── analytics.ts
│   │   │   └── upload.ts
│   │   ├── services/
│   │   │   └── python.ts      # HTTP client → FastAPI
│   │   └── index.ts
│   ├── prisma/
│   │   └── schema.prisma      # Source of truth for DB schema + migrations
│   ├── package.json
│   └── tsconfig.json
├── python_service/            # FastAPI + parsers + analytics
│   ├── parsers/
│   ├── pipeline/
│   ├── analytics/
│   ├── ai/
│   ├── models/
│   ├── cache.py
│   ├── database.py
│   └── main.py
├── shared/
│   └── fixtures/              # Golden JSON test fixtures (copied from FinanceTesting)
├── docker-compose.yml
├── docker-compose.dev.yml     # Dev overrides: hot reload, exposed ports
├── .env.example
└── docs/
    └── schema.graphql         # Exported SDL for iOS codegen
```

**Schema contract:** `financeos-backend/docs/schema.graphql` is exported on every Node build. `financeos-ios` pins to a specific schema version for Apollo codegen. Schema changes require coordinated version bump.

---

## Implementation Order

1. **Backend scaffold** — Docker Compose up, Postgres schema, health checks green
2. **Python parsers** — Port HDFC CSV/TXT, ICICI, Amex. Unit test against existing fixtures in `FinanceTesting`.
3. **Python import pipeline** — `/parse` + `/import` endpoints with dedup
4. **Node.js GraphQL** — Schema, resolvers for ledgers + transactions, `uploadStatement` mutation wired to Python
5. **Python analytics** — `/analytics` + Redis cache
6. **SwiftUI thin client** — Replace GRDB layer with Apollo SDK, wire to `localhost:4000`
7. **End-to-end test** — Upload real bank statement from SwiftUI, verify transactions appear via GraphQL

---

## Out of Scope (This Spec)

- Authentication / authorization
- Cloud deployment
- Web frontend
- Real-time subscriptions
- ML model training
- Sync between clients
