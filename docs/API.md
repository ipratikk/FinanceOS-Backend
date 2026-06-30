# FinanceOS API Reference

> Auto-generated 2026-06-30 12:45 UTC from `node_api/src/schema/typedefs.graphql`. Do not edit manually.

## Endpoint

| Protocol | URL |
|----------|-----|
| GraphQL | `POST http://localhost:4000/graphql` |
| Health check | `GET http://localhost:4000/health` |

> All GraphQL operations go to `POST /graphql`. Send JSON body `{"query": "..."}` or use a GraphQL client.

## Money

All monetary values use the `Money` type: `{ value: Int!, currencyCode: CurrencyCode! }`. `value` is in **minor units** (paise for INR, cents for USD/EUR/GBP). Divide by 100 for display.

---

## Queries

### `health`
_Returns server status string._

**Returns:** `String!`

### `banks`
_List all banks._

**Returns:** `[Bank!]!`

### `ledger`
_Fetch single ledger by ID._

**Arguments:**

- `id: ID!`

**Returns:** `Ledger`

### `ledgers`
_List all ledgers across all banks._

**Returns:** `[Ledger!]!`

### `transactions`
_List transactions, optionally filtered by ledger and/or criteria._

**Arguments:**

- `ledgerId: ID`
- `filter: TransactionFilter`
- `limit: Int`

**Returns:** `[Transaction!]!`

### `analytics`
_Spending summary for a date range, optionally scoped to a ledger._

**Arguments:**

- `ledgerId: ID`
- `from: String`
- `to: String`

**Returns:** `SpendingSummary!`

---

## Mutations

### `uploadStatement`
_Upload a bank statement file (PDF or CSV) to import transactions. Uses `multipart/form-data`._

**Arguments:**

- `ledgerId: ID!`
- `file: Upload!`

**Returns:** `ImportResult!`

### `createLedger`
_Create a new ledger under an existing bank._

**Arguments:**

- `input: CreateLedgerInput!`

**Returns:** `Ledger!`

### `updateLedger`
_Update ledger display name, kind, or last4._

**Arguments:**

- `id: ID!`
- `input: UpdateLedgerInput!`

**Returns:** `Ledger!`

### `deleteLedger`
_Delete a ledger and all its transactions._

**Arguments:**

- `id: ID!`

**Returns:** `Boolean!`

### `recategorize`
_Override the category on a transaction._

**Arguments:**

- `transactionId: ID!`
- `category: String!`

**Returns:** `Transaction!`

### `deleteTransaction`
_Delete a single transaction by ID._

**Arguments:**

- `id: ID!`

**Returns:** `Boolean!`

### `createBank`
_Register a new bank._

**Arguments:**

- `input: CreateBankInput!`

**Returns:** `Bank!`

### `clearAllData`
_Wipe all banks, ledgers, and transactions. Irreversible._

**Returns:** `Boolean!`

---

## Types

### `Money`

| Field | Type |
|-------|------|
| `value` | `Int!` |
| `currencyCode` | `CurrencyCode!` |

### `Bank`

| Field | Type |
|-------|------|
| `id` | `ID!` |
| `name` | `String!` |
| `code` | `String!` |
| `ledgers` | `[Ledger!]!` |

### `Ledger`

| Field | Type |
|-------|------|
| `id` | `ID!` |
| `displayName` | `String!` |
| `kind` | `LedgerKind!` |
| `last4` | `String` |
| `bank` | `Bank!` |
| `transactions` | `[Transaction!]!` |
| `balance` | `Money!` |

### `Transaction`

| Field | Type |
|-------|------|
| `id` | `ID!` |
| `date` | `String!` |
| `narration` | `String!` |
| `amount` | `Money!` |
| `ledger` | `Ledger!` |
| `category` | `String` |
| `merchant` | `String` |
| `sourceFingerprint` | `String!` |

### `SpendingSummary`

| Field | Type |
|-------|------|
| `totalSpend` | `Money!` |
| `totalIncome` | `Money!` |
| `netFlow` | `Money!` |
| `byCategory` | `[CategoryBreakdown!]!` |
| `byMonth` | `[MonthlyBreakdown!]!` |

### `CategoryBreakdown`

| Field | Type |
|-------|------|
| `category` | `String!` |
| `amount` | `Money!` |
| `count` | `Int!` |

### `MonthlyBreakdown`

| Field | Type |
|-------|------|
| `month` | `String!` |
| `spend` | `Money!` |
| `income` | `Money!` |

### `ImportResult`

| Field | Type |
|-------|------|
| `imported` | `Int!` |
| `duplicates` | `Int!` |
| `errors` | `[String!]!` |
| `ledger` | `Ledger!` |

---

## Input Types

### `TransactionFilter`

| Field | Type |
|-------|------|
| `from` | `String` |
| `to` | `String` |
| `category` | `String` |
| `minAmount` | `Int` |
| `maxAmount` | `Int` |

### `CreateLedgerInput`

| Field | Type |
|-------|------|
| `displayName` | `String!` |
| `kind` | `LedgerKind!` |
| `last4` | `String` |
| `bankId` | `ID!` |

### `UpdateLedgerInput`

| Field | Type |
|-------|------|
| `displayName` | `String` |
| `kind` | `LedgerKind` |
| `last4` | `String` |

### `CreateBankInput`

| Field | Type |
|-------|------|
| `name` | `String!` |
| `code` | `String!` |

---

## Enums

### `CurrencyCode`

- `INR`
- `USD`
- `EUR`
- `GBP`

### `LedgerKind`

- `BANK_ACCOUNT`
- `CREDIT_CARD`
- `LOAN`
- `WALLET`
- `CRYPTO`
- `INVESTMENT`

---

## Scalars

- `Upload` — file upload via multipart/form-data (used in `uploadStatement`)

