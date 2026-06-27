# FinanceOS Backend — Plan 3: Node.js GraphQL

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the stub `health`-only GraphQL schema with the full SDL, wire all resolvers (banks, ledgers, transactions, upload), and connect `uploadStatement` to the Python `/parse` + `/import` pipeline.

**Architecture:** Apollo Server 4 with SDL-first schema. Resolvers are split by domain into separate files. The `uploadStatement` mutation streams the file to Python `/parse`, receives `ParsedTransaction[]`, then calls `/import`. Prisma client handles all Postgres reads for queries.

**Tech Stack:** Apollo Server 4 + Express + Prisma 5 + graphql-upload-ts + Axios + TypeScript

---

## Prerequisite

Plans 1 and 2 complete. Python `/parse` and `/import` endpoints return correct results.

---

## File Map

```
node_api/src/
├── schema/
│   └── typedefs.graphql        # REPLACE: stub → full SDL
├── resolvers/
│   ├── index.ts                # merge all resolvers
│   ├── bank.ts                 # Query.banks
│   ├── ledger.ts               # Query.ledger, Query.ledgers, Ledger.transactions, Ledger.balance
│   ├── transaction.ts          # Query.transactions
│   ├── analytics.ts            # Query.analytics (calls Python /analytics)
│   └── upload.ts               # Mutation.uploadStatement
├── services/
│   └── python.ts               # Axios client → FastAPI
├── prisma/
│   └── client.ts               # singleton PrismaClient
└── index.ts                    # MODIFY: add graphql-upload, wire all resolvers
```

---

### Task 1: Full SDL schema

**Files:**
- Modify: `node_api/src/schema/typedefs.graphql`

- [ ] **Step 1: Replace stub typedefs with full schema**

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
  health: String!
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

- [ ] **Step 2: Verify dev server still starts after schema change**

```bash
cd node_api && npm run dev
```

Expected: Apollo Server starts (resolvers will be missing but server loads schema).

- [ ] **Step 3: Commit**

```bash
git add node_api/src/schema/typedefs.graphql
git commit -m "feat: replace stub SDL with full FinanceOS GraphQL schema"
```

---

### Task 2: Prisma client singleton + Python service client

**Files:**
- Create: `node_api/src/prisma/client.ts`
- Create: `node_api/src/services/python.ts`
- Run: `npm install axios`

- [ ] **Step 1: Create `node_api/src/prisma/client.ts`**

```typescript
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();
export default prisma;
```

- [ ] **Step 2: Install axios**

```bash
cd node_api && npm install axios
```

- [ ] **Step 3: Create `node_api/src/services/python.ts`**

```typescript
import axios from 'axios';
import FormData from 'form-data';

const PYTHON_URL = process.env.PYTHON_SERVICE_URL ?? 'http://localhost:8000';

export interface ParsedTransaction {
  postedAt: string;
  description: string;
  amountMinorUnits: number;
  currencyCode: string;
  sourceFingerprint: string;
  rewardPoints?: number;
  closingBalanceMinorUnits?: number;
  statementRowIndex?: number;
}

export interface ParseResponse {
  bank_code: string;
  count: number;
  transactions: ParsedTransaction[];
}

export interface ImportResponse {
  imported: number;
  duplicates: number;
  errors: string[];
}

export async function parseFile(
  fileBuffer: Buffer,
  filename: string,
  bankCode?: string,
): Promise<ParseResponse> {
  const form = new FormData();
  form.append('file', fileBuffer, { filename });
  if (bankCode) form.append('bank_code', bankCode);

  const res = await axios.post<ParseResponse>(`${PYTHON_URL}/parse`, form, {
    headers: form.getHeaders(),
  });
  return res.data;
}

export async function importTransactions(
  ledgerId: string,
  transactions: ParsedTransaction[],
): Promise<ImportResponse> {
  const res = await axios.post<ImportResponse>(`${PYTHON_URL}/import`, {
    ledger_id: ledgerId,
    transactions,
  });
  return res.data;
}

export async function getAnalytics(
  ledgerId?: string,
  from?: string,
  to?: string,
): Promise<unknown> {
  const params: Record<string, string> = {};
  if (ledgerId) params.ledger_id = ledgerId;
  if (from) params.from = from;
  if (to) params.to = to;

  const res = await axios.get(`${PYTHON_URL}/analytics`, { params });
  return res.data;
}
```

- [ ] **Step 4: Install form-data types**

```bash
cd node_api && npm install form-data && npm install --save-dev @types/form-data
```

- [ ] **Step 5: Commit**

```bash
git add node_api/src/prisma/ node_api/src/services/ node_api/package.json node_api/package-lock.json
git commit -m "feat: add Prisma client singleton and Python service Axios client"
```

---

### Task 3: Bank + Ledger resolvers

**Files:**
- Create: `node_api/src/resolvers/bank.ts`
- Create: `node_api/src/resolvers/ledger.ts`
- Create: `node_api/src/resolvers/index.ts`
- Modify: `node_api/src/index.ts`

- [ ] **Step 1: Create `node_api/src/resolvers/bank.ts`**

```typescript
import prisma from '../prisma/client.js';

export const bankResolvers = {
  Query: {
    banks: () => prisma.bank.findMany({ include: { ledgers: false } }),
  },
  Bank: {
    ledgers: (parent: { id: string }) =>
      prisma.ledger.findMany({ where: { bankId: parent.id } }),
  },
};
```

- [ ] **Step 2: Create `node_api/src/resolvers/ledger.ts`**

```typescript
import prisma from '../prisma/client.js';

export const ledgerResolvers = {
  Query: {
    ledgers: () => prisma.ledger.findMany({ include: { bank: true } }),
    ledger: (_: unknown, { id }: { id: string }) =>
      prisma.ledger.findUnique({ where: { id }, include: { bank: true } }),
  },
  Mutation: {
    createLedger: (_: unknown, { input }: { input: { displayName: string; kind: string; last4?: string; bankId: string } }) =>
      prisma.ledger.create({ data: input as any, include: { bank: true } }),
    updateLedger: (_: unknown, { id, input }: { id: string; input: Partial<{ displayName: string; kind: string; last4: string }> }) =>
      prisma.ledger.update({ where: { id }, data: input as any, include: { bank: true } }),
    deleteLedger: async (_: unknown, { id }: { id: string }) => {
      await prisma.ledger.delete({ where: { id } });
      return true;
    },
  },
  Ledger: {
    bank: (parent: { bankId: string }) =>
      prisma.bank.findUnique({ where: { id: parent.bankId } }),
    transactions: (
      parent: { id: string },
      { filter }: { filter?: { from?: string; to?: string; category?: string; minAmount?: number; maxAmount?: number } },
    ) => {
      const where: Record<string, unknown> = { ledgerId: parent.id };
      if (filter?.from) where.date = { gte: new Date(filter.from) };
      if (filter?.to) where.date = { ...(where.date as object ?? {}), lte: new Date(filter.to) };
      if (filter?.category) where.category = filter.category;
      if (filter?.minAmount != null) where.amount = { gte: filter.minAmount / 100 };
      if (filter?.maxAmount != null) where.amount = { ...(where.amount as object ?? {}), lte: filter.maxAmount / 100 };
      return prisma.transaction.findMany({ where, orderBy: { date: 'desc' } });
    },
    balance: async (parent: { id: string }) => {
      const result = await prisma.transaction.aggregate({
        where: { ledgerId: parent.id },
        _sum: { amount: true },
      });
      return result._sum.amount ?? 0;
    },
  },
};
```

- [ ] **Step 3: Create `node_api/src/resolvers/transaction.ts`**

```typescript
import prisma from '../prisma/client.js';

export const transactionResolvers = {
  Query: {
    transactions: (
      _: unknown,
      { ledgerId, filter }: { ledgerId?: string; filter?: { from?: string; to?: string; category?: string } },
    ) => {
      const where: Record<string, unknown> = {};
      if (ledgerId) where.ledgerId = ledgerId;
      if (filter?.from) where.date = { gte: new Date(filter.from) };
      if (filter?.to) where.date = { ...(where.date as object ?? {}), lte: new Date(filter.to) };
      if (filter?.category) where.category = filter.category;
      return prisma.transaction.findMany({ where, orderBy: { date: 'desc' } });
    },
  },
  Mutation: {
    recategorize: (_: unknown, { transactionId, category }: { transactionId: string; category: string }) =>
      prisma.transaction.update({
        where: { id: transactionId },
        data: { category },
        include: { ledger: true },
      }),
  },
  Transaction: {
    ledger: (parent: { ledgerId: string }) =>
      prisma.ledger.findUnique({ where: { id: parent.ledgerId }, include: { bank: true } }),
  },
};
```

- [ ] **Step 4: Create `node_api/src/resolvers/index.ts`**

```typescript
import { bankResolvers } from './bank.js';
import { ledgerResolvers } from './ledger.js';
import { transactionResolvers } from './transaction.js';
import { uploadResolvers } from './upload.js';
import { analyticsResolvers } from './analytics.js';

export const resolvers = {
  Query: {
    health: () => 'ok',
    ...bankResolvers.Query,
    ...ledgerResolvers.Query,
    ...transactionResolvers.Query,
    ...analyticsResolvers.Query,
  },
  Mutation: {
    ...ledgerResolvers.Mutation,
    ...transactionResolvers.Mutation,
    ...uploadResolvers.Mutation,
  },
  Bank: bankResolvers.Bank,
  Ledger: ledgerResolvers.Ledger,
  Transaction: transactionResolvers.Transaction,
};
```

- [ ] **Step 5: Commit**

```bash
git add node_api/src/resolvers/
git commit -m "feat: add bank, ledger, transaction resolvers"
```

---

### Task 4: Upload mutation + analytics stub

**Files:**
- Create: `node_api/src/resolvers/upload.ts`
- Create: `node_api/src/resolvers/analytics.ts`

- [ ] **Step 1: Create `node_api/src/resolvers/upload.ts`**

```typescript
import { parseFile, importTransactions } from '../services/python.js';
import prisma from '../prisma/client.js';

interface FileUpload {
  filename: string;
  mimetype: string;
  encoding: string;
  createReadStream: () => NodeJS.ReadableStream;
}

export const uploadResolvers = {
  Mutation: {
    uploadStatement: async (
      _: unknown,
      { ledgerId, file }: { ledgerId: string; file: Promise<FileUpload> },
    ) => {
      const { filename, createReadStream } = await file;

      // Buffer the stream
      const chunks: Buffer[] = [];
      await new Promise<void>((resolve, reject) => {
        const stream = createReadStream();
        stream.on('data', (chunk: Buffer) => chunks.push(chunk));
        stream.on('end', resolve);
        stream.on('error', reject);
      });
      const buffer = Buffer.concat(chunks);

      // Parse via Python
      const parsed = await parseFile(buffer, filename);

      // Import via Python (dedup + write to Postgres)
      const imported = await importTransactions(ledgerId, parsed.transactions);

      // Return updated ledger
      const ledger = await prisma.ledger.findUniqueOrThrow({
        where: { id: ledgerId },
        include: { bank: true },
      });

      return {
        imported: imported.imported,
        duplicates: imported.duplicates,
        errors: imported.errors,
        ledger,
      };
    },
  },
};
```

- [ ] **Step 2: Create `node_api/src/resolvers/analytics.ts`**

```typescript
import { getAnalytics } from '../services/python.js';

export const analyticsResolvers = {
  Query: {
    analytics: async (
      _: unknown,
      { ledgerId, from, to }: { ledgerId?: string; from?: string; to?: string },
    ) => {
      const data = await getAnalytics(ledgerId, from, to) as any;
      return data;
    },
  },
};
```

- [ ] **Step 3: Commit**

```bash
git add node_api/src/resolvers/upload.ts node_api/src/resolvers/analytics.ts
git commit -m "feat: add uploadStatement mutation and analytics resolver stub"
```

---

### Task 5: Wire graphql-upload + resolvers into server

**Files:**
- Modify: `node_api/src/index.ts`
- Modify: `node_api/package.json`

- [ ] **Step 1: Install graphql-upload-ts**

```bash
cd node_api && npm install graphql-upload-ts
```

- [ ] **Step 2: Replace `node_api/src/index.ts` with upload-enabled version**

```typescript
import { ApolloServer } from '@apollo/server';
import { expressMiddleware } from '@apollo/server/express4';
import { ApolloServerPluginDrainHttpServer } from '@apollo/server/plugin/drainHttpServer';
import express from 'express';
import http from 'http';
import cors from 'cors';
import { readFileSync } from 'fs';
import { join } from 'path';
import { graphqlUploadExpress } from 'graphql-upload-ts';
import { resolvers } from './resolvers/index.js';

const typeDefs = readFileSync(join(__dirname, 'schema/typedefs.graphql'), 'utf-8');

async function main() {
  const app = express();
  const httpServer = http.createServer(app);

  const server = new ApolloServer({
    typeDefs,
    resolvers,
    plugins: [ApolloServerPluginDrainHttpServer({ httpServer })],
  });

  await server.start();

  app.use(
    '/graphql',
    cors<cors.CorsRequest>(),
    graphqlUploadExpress({ maxFileSize: 50 * 1024 * 1024, maxFiles: 1 }),
    express.json(),
    expressMiddleware(server),
  );

  app.get('/health', (_req, res) => {
    res.json({ status: 'ok' });
  });

  await new Promise<void>(resolve => httpServer.listen({ port: 4000 }, resolve));
  console.log('Apollo Server ready at http://localhost:4000/graphql');
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
```

- [ ] **Step 3: Start dev server, verify it compiles**

```bash
cd node_api && npm run dev
```

Expected: `Apollo Server ready at http://localhost:4000/graphql`

- [ ] **Step 4: Smoke test — banks query (empty result, but no error)**

```bash
curl -X POST http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ banks { id name code } }"}'
```

Expected: `{"data":{"banks":[]}}`

- [ ] **Step 5: Seed one bank to verify DB reads work**

```bash
docker compose exec postgres psql -U financeOS -c \
  "INSERT INTO \"Bank\" (id, name, code) VALUES (gen_random_uuid(), 'HDFC Bank', 'HDFC') ON CONFLICT DO NOTHING;"
```

Re-run banks query — expected: 1 bank returned.

- [ ] **Step 6: Test uploadStatement via curl**

Requires a ledger to exist. Create one:

```bash
curl -X POST http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { createLedger(input: { displayName: \"HDFC Card\", kind: CREDIT_CARD, bankId: \"<BANK_ID_FROM_STEP_5>\" }) { id displayName } }"}'
```

Then upload:

```bash
curl -X POST http://localhost:4000/graphql \
  -F 'operations={"query":"mutation($file:Upload!,$ledgerId:ID!){uploadStatement(ledgerId:$ledgerId,file:$file){imported duplicates errors ledger{id}}}","variables":{"file":null,"ledgerId":"<LEDGER_ID>"}}' \
  -F 'map={"0":["variables.file"]}' \
  -F '0=@../FinanceOS/Packages/FinanceParsers/Tests/Fixtures/hdfc_card.csv'
```

Expected: `{"data":{"uploadStatement":{"imported":4,"duplicates":0,"errors":[],"ledger":{"id":"..."}}}}`

- [ ] **Step 7: Commit**

```bash
git add node_api/src/index.ts node_api/package.json node_api/package-lock.json
git commit -m "feat: wire graphql-upload, full resolver set, and uploadStatement mutation end-to-end"
```

---

### Task 6: Rebuild Docker image + integration smoke test

**Files:** No new files.

- [ ] **Step 1: Rebuild and restart all services**

```bash
docker compose down
docker compose up --build
```

- [ ] **Step 2: Verify all queries work via Docker**

```bash
# Health
curl http://localhost:4000/health
# Expected: {"status":"ok"}

# Banks query
curl -X POST http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ banks { id name } }"}'
# Expected: {"data":{"banks":[...]}}

# Ledgers query
curl -X POST http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ ledgers { id displayName kind } }"}'
# Expected: {"data":{"ledgers":[...]}}
```

- [ ] **Step 3: Export SDL for iOS codegen**

```bash
cd node_api
npx apollo-codegen introspect-schema http://localhost:4000/graphql --output ../docs/schema.graphql 2>/dev/null || \
npx get-graphql-schema http://localhost:4000/graphql > ../docs/schema.graphql
```

Or simpler — just copy the SDL:

```bash
cp node_api/src/schema/typedefs.graphql docs/schema.graphql
```

- [ ] **Step 4: Commit**

```bash
git add docs/schema.graphql
git commit -m "docs: export GraphQL SDL for iOS Apollo codegen"
```
