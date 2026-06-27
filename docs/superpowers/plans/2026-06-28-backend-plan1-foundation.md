# FinanceOS Backend — Plan 1: Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the `financeos-backend` repo with Docker Compose (Postgres 16 + Redis 7), a Node.js Apollo Server skeleton, Prisma schema with initial migration, and a Python FastAPI skeleton — all four services healthy at `docker compose up`.

**Architecture:** Two services (Node.js port 4000, Python port 8000) share one Postgres instance and Redis. Node owns schema migrations via Prisma; Python uses asyncpg with raw SQL against the same schema. Docker Compose orchestrates local deployment with healthchecks before dependent services start.

**Tech Stack:** Node.js 20 + TypeScript 5 + Apollo Server 4 + Prisma 5 + Express 4; Python 3.12 + FastAPI 0.111 + asyncpg 0.29 + uvicorn; PostgreSQL 16-alpine; Redis 7-alpine; Docker Compose v3.9

---

## Part of a 5-Plan Series

1. **Foundation** (this plan)
2. Python parsers + import pipeline
3. Node.js GraphQL (full SDL + resolvers + upload mutation)
4. Analytics + Redis cache
5. iOS thin client (Apollo SDK, replace GRDB)

---

## File Map

**New repo location:** `financeos-backend/` — sibling to `FinanceOS/` on disk, separate git repo.

```
financeos-backend/
├── .gitignore
├── .env.example
├── docker-compose.yml
├── node_api/
│   ├── .env                    # local dev only — gitignored
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── prisma/
│   │   └── schema.prisma       # source of truth for all DB migrations
│   └── src/
│       ├── index.ts            # Apollo Server + Express entrypoint
│       └── schema/
│           └── typedefs.graphql  # SDL (health query only for now)
└── python_service/
    ├── Dockerfile
    ├── requirements.txt
    ├── database.py             # asyncpg connection pool
    └── main.py                 # FastAPI app + /health endpoint
```

---

### Task 1: Initialize `financeos-backend` repo

**Files:** `.gitignore`

- [ ] **Step 1: Create the repo**

```bash
cd ~/Documents/GitHub
mkdir financeos-backend
cd financeos-backend
git init
```

- [ ] **Step 2: Create `.gitignore`**

```
# Node
node_modules/
dist/
*.js.map
.env

# Python
__pycache__/
*.pyc
.venv/
*.egg-info/

# Docker
*.log

# macOS
.DS_Store
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: init financeos-backend repo"
```

---

### Task 2: Docker Compose — Postgres + Redis

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`

- [ ] **Step 1: Create `docker-compose.yml`**

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: financeOS
      POSTGRES_PASSWORD: financeOS
      POSTGRES_DB: financeOS
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U financeOS"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  node-api:
    build: ./node_api
    ports:
      - "4000:4000"
    environment:
      DATABASE_URL: postgresql://financeOS:financeOS@postgres:5432/financeOS
      PYTHON_SERVICE_URL: http://python-parser:8000
      NODE_ENV: development
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  python-parser:
    build: ./python_service
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://financeOS:financeOS@postgres:5432/financeOS
      REDIS_URL: redis://redis:6379
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  pgdata:
```

- [ ] **Step 2: Create `.env.example`**

```
DATABASE_URL=postgresql://financeOS:financeOS@localhost:5432/financeOS
PYTHON_SERVICE_URL=http://localhost:8000
REDIS_URL=redis://localhost:6379
NODE_ENV=development
```

- [ ] **Step 3: Start Postgres + Redis only**

```bash
docker compose up postgres redis -d
```

Wait ~15 seconds then verify both show `healthy`:

```bash
docker compose ps
```

Expected: Both `postgres` and `redis` show status `healthy`.

- [ ] **Step 4: Verify Postgres connection**

```bash
docker compose exec postgres psql -U financeOS -c "\l"
```

Expected: Lists `financeOS` database in the output.

- [ ] **Step 5: Verify Redis**

```bash
docker compose exec redis redis-cli ping
```

Expected: `PONG`

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "chore: add Docker Compose with Postgres 16 + Redis 7"
```

---

### Task 3: Node.js Apollo skeleton

**Files:**
- Create: `node_api/package.json`
- Create: `node_api/tsconfig.json`
- Create: `node_api/src/schema/typedefs.graphql`
- Create: `node_api/src/index.ts`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p node_api/src/schema
```

- [ ] **Step 2: Create `node_api/package.json`**

```json
{
  "name": "financeos-api",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "ts-node-dev --respawn --transpile-only src/index.ts",
    "build": "tsc && cp -r src/schema dist/schema",
    "start": "node dist/index.js",
    "migrate:dev": "prisma migrate dev",
    "migrate:deploy": "prisma migrate deploy",
    "generate": "prisma generate"
  },
  "dependencies": {
    "@apollo/server": "^4.10.4",
    "@prisma/client": "^5.13.0",
    "axios": "^1.7.2",
    "cors": "^2.8.5",
    "express": "^4.19.2",
    "graphql": "^16.8.2",
    "prisma": "^5.13.0"
  },
  "devDependencies": {
    "@types/cors": "^2.8.17",
    "@types/express": "^4.17.21",
    "@types/node": "^20.14.0",
    "ts-node-dev": "^2.0.0",
    "typescript": "^5.4.5"
  }
}
```

Note: `prisma` is in `dependencies` (not devDependencies) so the CLI is available inside Docker at runtime for `migrate deploy`.

- [ ] **Step 3: Create `node_api/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

- [ ] **Step 4: Create `node_api/src/schema/typedefs.graphql`**

```graphql
type Query {
  health: String!
}
```

- [ ] **Step 5: Create `node_api/src/index.ts`**

```typescript
import { ApolloServer } from '@apollo/server';
import { expressMiddleware } from '@apollo/server/express4';
import { ApolloServerPluginDrainHttpServer } from '@apollo/server/plugin/drainHttpServer';
import express from 'express';
import http from 'http';
import cors from 'cors';
import { readFileSync } from 'fs';
import { join } from 'path';

const typeDefs = readFileSync(join(__dirname, 'schema/typedefs.graphql'), 'utf-8');

const resolvers = {
  Query: {
    health: () => 'ok',
  },
};

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

Path note: `__dirname` is `src/` when running via `ts-node-dev`, so `join(__dirname, 'schema/typedefs.graphql')` resolves correctly. The build script (`tsc && cp -r src/schema dist/schema`) copies the SDL so it resolves the same way in the compiled `dist/` output.

- [ ] **Step 6: Install dependencies + start dev server**

```bash
cd node_api
npm install
npm run dev
```

Expected: `Apollo Server ready at http://localhost:4000/graphql`

- [ ] **Step 7: Smoke test (in a new terminal)**

```bash
curl http://localhost:4000/health
```
Expected: `{"status":"ok"}`

```bash
curl -X POST http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ health }"}'
```
Expected: `{"data":{"health":"ok"}}`

- [ ] **Step 8: Stop dev server (Ctrl+C), commit**

```bash
cd ..
git add node_api/package.json node_api/tsconfig.json node_api/src/
git commit -m "feat: add Node.js Apollo Server skeleton with health query"
```

---

### Task 4: Prisma schema + initial migration

**Files:**
- Create: `node_api/prisma/schema.prisma`
- Create: `node_api/.env` (local only, not committed)

Prerequisite: Postgres must be running from Task 2.

- [ ] **Step 1: Create `node_api/.env` (not committed — already gitignored)**

```
DATABASE_URL=postgresql://financeOS:financeOS@localhost:5432/financeOS
```

- [ ] **Step 2: Create `node_api/prisma/schema.prisma`**

```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

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

- [ ] **Step 3: Run initial migration**

```bash
cd node_api
npx prisma migrate dev --name init
```

Expected output:
```
Applying migration `20260628000000_init`
Database changes applied.
✔  Generated Prisma Client
```

- [ ] **Step 4: Verify tables in Postgres**

```bash
docker compose exec postgres psql -U financeOS -c "\dt"
```

Expected: Lists `Bank`, `Ledger`, `Transaction`, `_prisma_migrations`.

- [ ] **Step 5: Commit (migrations folder is intentionally committed)**

```bash
cd ..
git add node_api/prisma/
git commit -m "feat: add Prisma schema with Bank/Ledger/Transaction + initial migration"
```

---

### Task 5: Node.js Dockerfile

**Files:**
- Create: `node_api/Dockerfile`

- [ ] **Step 1: Create `node_api/Dockerfile`**

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npx prisma generate
RUN npm run build
EXPOSE 4000
CMD ["sh", "-c", "npx prisma migrate deploy && node dist/index.js"]
```

Note: Single-stage build — simpler for local dev. `prisma migrate deploy` runs on every container start using the `DATABASE_URL` env var injected by Docker Compose.

- [ ] **Step 2: Build and start in Docker**

```bash
docker compose build node-api
docker compose up node-api -d
```

- [ ] **Step 3: Check logs**

```bash
docker compose logs node-api
```

Expected log lines:
```
Applying migration `20260628000000_init`
Database changes applied.
Apollo Server ready at http://localhost:4000/graphql
```

- [ ] **Step 4: Smoke test from host**

```bash
curl http://localhost:4000/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 5: Commit**

```bash
git add node_api/Dockerfile
git commit -m "feat: add Node.js Dockerfile with Prisma migrate on startup"
```

---

### Task 6: Python FastAPI skeleton

**Files:**
- Create: `python_service/requirements.txt`
- Create: `python_service/database.py`
- Create: `python_service/main.py`
- Create: `python_service/Dockerfile`

- [ ] **Step 1: Create `python_service/requirements.txt`**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
asyncpg==0.29.0
redis[hiredis]==5.0.4
python-multipart==0.0.9
pydantic==2.7.1
httpx==0.27.0
```

- [ ] **Step 2: Create `python_service/database.py`**

```python
import asyncpg
import os

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(os.environ["DATABASE_URL"])
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
```

- [ ] **Step 3: Create `python_service/main.py`**

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import close_pool, get_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="FinanceOS Parser Service", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    pool = await get_pool()
    await pool.fetchval("SELECT 1")
    return {"status": "ok", "db": "connected"}
```

- [ ] **Step 4: Test locally (optional, requires Python 3.12)**

```bash
cd python_service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=postgresql://financeOS:financeOS@localhost:5432/financeOS uvicorn main:app --reload
```

Expected: `Uvicorn running on http://127.0.0.1:8000`

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok","db":"connected"}`

Stop with Ctrl+C.

- [ ] **Step 5: Create `python_service/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 6: Commit**

```bash
cd ..
git add python_service/
git commit -m "feat: add Python FastAPI skeleton with /health + asyncpg db check"
```

---

### Task 7: Full Docker Compose smoke test

**Files:** No new files.

- [ ] **Step 1: Bring down all containers (clean slate)**

```bash
docker compose down
```

- [ ] **Step 2: Start all four services**

```bash
docker compose up --build
```

Wait for all services to stabilize (~30-60 seconds). Expected log lines (order may vary):

```
financeos-backend-postgres-1       | database system is ready to accept connections
financeos-backend-redis-1          | Ready to accept connections tcp 0.0.0.0:6379
financeos-backend-node-api-1       | Apollo Server ready at http://localhost:4000/graphql
financeos-backend-python-parser-1  | Application startup complete.
```

- [ ] **Step 3: In a second terminal, verify all endpoints**

```bash
# Node health
curl http://localhost:4000/health
# Expected: {"status":"ok"}

# GraphQL health query
curl -X POST http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ health }"}'
# Expected: {"data":{"health":"ok"}}

# Python health (includes DB check)
curl http://localhost:8000/health
# Expected: {"status":"ok","db":"connected"}

# FastAPI auto-generated docs
curl -s http://localhost:8000/docs | head -5
# Expected: HTML starting with <!DOCTYPE html>
```

- [ ] **Step 4: Verify schema in Postgres**

```bash
docker compose exec postgres psql -U financeOS -c "\dt"
```

Expected:
```
         List of relations
 Schema |        Name        | Type  |  Owner
--------+--------------------+-------+----------
 public | Bank               | table | financeOS
 public | Ledger             | table | financeOS
 public | Transaction        | table | financeOS
 public | _prisma_migrations | table | financeOS
```

- [ ] **Step 5: Tag and push**

```bash
git tag v0.1.0-foundation
```

**Plan 1 complete.** Proceed to Plan 2 (Python parsers + import pipeline) when ready.
