# FinanceOS Backend — Plan 5: iOS Thin Client

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the SwiftUI macOS app (`Apps/FinanceOSMac`) from GRDB/local-SQLite to Apollo iOS SDK, wiring all existing ViewModels to the GraphQL backend at `http://localhost:4000/graphql`. Remove `FinanceParsers` and `FinanceIntelligence` package dependencies.

**Architecture:** `AppContainer` replaces repository instances with a `GraphQLClient`. ViewModels are unchanged at the interface level — only the injected dependencies change. Apollo codegen generates Swift types from `docs/schema.graphql` exported in Plan 3. The `uploadStatement` mutation replaces the local import pipeline.

**Tech Stack:** Apollo iOS SDK 1.x (via SPM), Apollo CLI for codegen, Swift 6, SwiftUI

---

## Prerequisite

Plans 1-4 complete. Backend running at `localhost:4000`. `docs/schema.graphql` exported from Node.js.

This plan modifies the **`FinanceOS` (iOS) repo**, not `financeos-backend`.

---

## File Map

Changes in `FinanceOS/` (the iOS repo):

```
Apps/FinanceOSMac/
├── GraphQL/
│   ├── Operations/
│   │   ├── Queries.graphql         # query declarations for Apollo codegen
│   │   └── Mutations.graphql       # mutation declarations for Apollo codegen
│   └── apollo-codegen-config.json  # codegen config pointing to schema.graphql
Packages/
├── FinanceCore/
│   ├── Sources/FinanceCore/
│   │   ├── GraphQL/
│   │   │   ├── GraphQLClient.swift          # protocol + URLSession-based impl
│   │   │   └── ApolloGraphQLClient.swift    # Apollo SDK impl (primary)
│   │   ├── AppContainer/AppContainer.swift  # MODIFY: swap repos for GraphQLClient
│   │   ├── Importing/ImportViewModel.swift  # MODIFY: uploadStatement mutation
│   │   └── Repositories/ (keep protocols, delete GRDB impls)
├── FinanceParsers/    # REMOVE from Package.swift deps
└── FinanceIntelligence/  # REMOVE from Package.swift deps
```

---

### Task 1: Add Apollo iOS SDK via SPM

**Files:**
- Modify: `FinanceOS.xcworkspace` / `Package.swift` (root package manifest or Xcode project)

- [ ] **Step 1: Open Xcode project and add Apollo SPM dependency**

In Xcode: File → Add Package Dependencies

URL: `https://github.com/apollographql/apollo-ios`

Version: `1.x.x` (latest 1.x stable)

Add to target: `FinanceOSMac`

Products to add: `Apollo`, `ApolloAPI`

- [ ] **Step 2: Verify build succeeds**

```
Cmd+B in Xcode
```

Expected: Build succeeds. No Apollo errors.

- [ ] **Step 3: Commit**

```bash
git add FinanceOS.xcworkspace/ # or Package.resolved
git commit -m "feat: add Apollo iOS SDK 1.x via SPM"
```

---

### Task 2: Run Apollo codegen

**Files:**
- Create: `Apps/FinanceOSMac/GraphQL/apollo-codegen-config.json`
- Create: `Apps/FinanceOSMac/GraphQL/Operations/Queries.graphql`
- Create: `Apps/FinanceOSMac/GraphQL/Operations/Mutations.graphql`
- Output: `Apps/FinanceOSMac/GraphQL/Generated/` (generated Swift files)

- [ ] **Step 1: Install Apollo CLI**

```bash
npm install -g @apollo/rover
# or via homebrew:
brew install apollo-ios-cli
```

- [ ] **Step 2: Create codegen config**

`Apps/FinanceOSMac/GraphQL/apollo-codegen-config.json`:

```json
{
  "schemaNamespace": "FinanceOSAPI",
  "input": {
    "operationSearchPaths": ["Operations/**/*.graphql"],
    "schemaSearchPaths": ["../../../../financeos-backend/docs/schema.graphql"]
  },
  "output": {
    "schemaTypes": {
      "path": "Generated/SchemaTypes",
      "moduleType": { "swiftPackageManager": {} }
    },
    "operations": {
      "inSchemaModule": {}
    }
  }
}
```

- [ ] **Step 3: Create `Queries.graphql`**

```graphql
query GetBanks {
  banks {
    id
    name
    code
  }
}

query GetLedgers {
  ledgers {
    id
    displayName
    kind
    last4
    bank {
      id
      name
      code
    }
    balance
  }
}

query GetTransactions($ledgerId: ID, $filter: TransactionFilter) {
  transactions(ledgerId: $ledgerId, filter: $filter) {
    id
    date
    narration
    amount
    category
    merchant
    sourceFingerprint
    ledger {
      id
      displayName
    }
  }
}

query GetAnalytics($ledgerId: ID, $from: String, $to: String) {
  analytics(ledgerId: $ledgerId, from: $from, to: $to) {
    totalSpend
    totalIncome
    netFlow
    byCategory {
      category
      amount
      count
    }
    byMonth {
      month
      spend
      income
    }
  }
}
```

- [ ] **Step 4: Create `Mutations.graphql`**

```graphql
mutation UploadStatement($ledgerId: ID!, $file: Upload!) {
  uploadStatement(ledgerId: $ledgerId, file: $file) {
    imported
    duplicates
    errors
    ledger {
      id
      displayName
      balance
    }
  }
}

mutation CreateLedger($input: CreateLedgerInput!) {
  createLedger(input: $input) {
    id
    displayName
    kind
    last4
    bank {
      id
      name
    }
  }
}

mutation UpdateLedger($id: ID!, $input: UpdateLedgerInput!) {
  updateLedger(id: $id, input: $input) {
    id
    displayName
    kind
    last4
  }
}

mutation DeleteLedger($id: ID!) {
  deleteLedger(id: $id)
}

mutation Recategorize($transactionId: ID!, $category: String!) {
  recategorize(transactionId: $transactionId, category: $category) {
    id
    category
  }
}
```

- [ ] **Step 5: Run codegen**

```bash
cd Apps/FinanceOSMac/GraphQL
apollo-ios-cli generate
```

Expected: `Generated/` directory created with Swift files for each query/mutation.

- [ ] **Step 6: Add Generated/ to Xcode target**

In Xcode: right-click `FinanceOSMac` → Add Files → select `Generated/`

Build: `Cmd+B` — expected: success.

- [ ] **Step 7: Commit**

```bash
git add Apps/FinanceOSMac/GraphQL/
git commit -m "feat: add Apollo codegen config, GraphQL operations, and generated Swift types"
```

---

### Task 3: GraphQLClient protocol + Apollo implementation

**Files:**
- Create: `Packages/FinanceCore/Sources/FinanceCore/GraphQL/GraphQLClient.swift`
- Create: `Packages/FinanceCore/Sources/FinanceCore/GraphQL/ApolloGraphQLClient.swift`

- [ ] **Step 1: Create `GraphQLClient.swift`**

```swift
import Foundation

// Minimal protocol for fetching GraphQL operations.
// ViewModels depend on this protocol, never on ApolloClient directly.
public protocol GraphQLClient: Sendable {
    func fetch<Query: GraphQLOperation>(
        query: Query
    ) async throws -> Query.Data where Query: AnyObject

    func perform<Mutation: GraphQLOperation>(
        mutation: Mutation
    ) async throws -> Mutation.Data where Mutation: AnyObject
}
```

Note: `GraphQLOperation` here is a placeholder type alias. The actual Apollo generated types conform to `ApolloAPI.GraphQLQuery` and `ApolloAPI.GraphQLMutation`. Adjust the protocol to match Apollo iOS SDK 1.x generic constraints — the concrete `ApolloGraphQLClient` below shows the pattern.

- [ ] **Step 2: Create `ApolloGraphQLClient.swift`**

```swift
import Apollo
import ApolloAPI
import Foundation

public final class ApolloGraphQLClient: Sendable {
    private let client: ApolloClient

    public init(url: URL = URL(string: "http://localhost:4000/graphql")!) {
        let store = ApolloStore()
        let provider = DefaultInterceptorProvider(store: store)
        let transport = RequestChainNetworkTransport(
            interceptorProvider: provider,
            endpointURL: url
        )
        self.client = ApolloClient(networkTransport: transport, store: store)
    }

    public func fetch<Query: GraphQLQuery>(query: Query) async throws -> Query.Data {
        try await withCheckedThrowingContinuation { continuation in
            client.fetch(query: query) { result in
                switch result {
                case .success(let response):
                    if let data = response.data {
                        continuation.resume(returning: data)
                    } else if let errors = response.errors {
                        continuation.resume(throwing: GraphQLClientError.graphqlErrors(errors.map(\.message ?? "Unknown")))
                    } else {
                        continuation.resume(throwing: GraphQLClientError.noData)
                    }
                case .failure(let error):
                    continuation.resume(throwing: error)
                }
            }
        }
    }

    public func perform<Mutation: GraphQLMutation>(mutation: Mutation) async throws -> Mutation.Data {
        try await withCheckedThrowingContinuation { continuation in
            client.perform(mutation: mutation) { result in
                switch result {
                case .success(let response):
                    if let data = response.data {
                        continuation.resume(returning: data)
                    } else if let errors = response.errors {
                        continuation.resume(throwing: GraphQLClientError.graphqlErrors(errors.map(\.message ?? "Unknown")))
                    } else {
                        continuation.resume(throwing: GraphQLClientError.noData)
                    }
                case .failure(let error):
                    continuation.resume(throwing: error)
                }
            }
        }
    }
}

public enum GraphQLClientError: Error {
    case noData
    case graphqlErrors([String])
}
```

- [ ] **Step 3: Build and verify no compile errors**

```
Cmd+B in Xcode
```

- [ ] **Step 4: Commit**

```bash
git add Packages/FinanceCore/Sources/FinanceCore/GraphQL/
git commit -m "feat: add ApolloGraphQLClient with async fetch/perform wrappers"
```

---

### Task 4: Replace LedgersViewModel data source

**Files:**
- Modify: `Apps/FinanceOSMac/` or `Packages/FinanceCore/` — locate `LedgersViewModel` / `AccountsViewModel` / `CardsViewModel`

- [ ] **Step 1: Find current ViewModel that loads ledgers**

```bash
grep -rn "LedgerRepository\|ledgerRepository\|fetchAll\|LedgersViewModel" Apps/ Packages/FinanceCore/Sources/ --include="*.swift" | grep -v ".build"
```

- [ ] **Step 2: Update ViewModel init to accept `ApolloGraphQLClient`**

In the ViewModel that loads ledgers (e.g., `LedgersViewModel`), replace `LedgerRepository` injection with `ApolloGraphQLClient`:

```swift
// Before:
private let ledgerRepository: any LedgerRepository

// After:
private let graphQLClient: ApolloGraphQLClient
```

- [ ] **Step 3: Replace `repository.fetchAll()` with GraphQL query**

```swift
// Before:
let ledgers = try await ledgerRepository.fetchAll()

// After:
let data = try await graphQLClient.fetch(query: GetLedgersQuery())
let ledgers = data.ledgers.map { item in
    Ledger(
        id: UUID(uuidString: item.id) ?? UUID(),
        displayName: item.displayName,
        kind: LedgerKind(rawValue: item.kind.rawValue) ?? .bankAccount,
        last4: item.last4,
        bankId: UUID(uuidString: item.bank.id) ?? UUID()
    )
}
```

- [ ] **Step 4: Build and verify**

```
Cmd+B
```

Expected: No errors. Fix any type mismatches between Apollo generated types and existing `Ledger` model.

- [ ] **Step 5: Commit**

```bash
git add -p  # stage only ViewModel changes
git commit -m "feat: migrate LedgersViewModel from GRDB to Apollo GraphQL"
```

---

### Task 5: Replace import pipeline with uploadStatement mutation

**Files:**
- Modify: `ImportViewModel` (locate via `grep -rn "ImportViewModel" Apps/ Packages/`)

- [ ] **Step 1: Find ImportViewModel**

```bash
grep -rn "ImportViewModel\|importStatement\|parseFile" Apps/ Packages/ --include="*.swift" | grep -v ".build" | head -20
```

- [ ] **Step 2: Replace local parser call with uploadStatement mutation**

In `ImportViewModel`, replace the local pipeline with:

```swift
// Before (local parser pipeline):
let pipeline = ImportPipeline(parsers: [...])
let result = try await pipeline.import(fileURL: url, ledgerId: ledgerId)

// After (GraphQL mutation):
let fileData = try Data(contentsOf: url)
let upload = GraphQLFile(
    fieldName: "file",
    originalName: url.lastPathComponent,
    mimeType: "text/csv",
    data: fileData
)
let data = try await graphQLClient.perform(
    mutation: UploadStatementMutation(ledgerId: ledgerId.uuidString, file: upload)
)
importedCount = data.uploadStatement.imported
duplicateCount = data.uploadStatement.duplicates
errors = data.uploadStatement.errors
```

- [ ] **Step 3: Build and verify**

```
Cmd+B
```

- [ ] **Step 4: Commit**

```bash
git add -p
git commit -m "feat: replace local import pipeline with uploadStatement GraphQL mutation"
```

---

### Task 6: Update AppContainer + remove dead packages

**Files:**
- Modify: `Packages/FinanceCore/Sources/FinanceCore/AppContainer/AppContainer.swift`
- Modify: root `Package.swift` (remove FinanceParsers, FinanceIntelligence from app target deps)

- [ ] **Step 1: Update AppContainer to vend `ApolloGraphQLClient`**

```swift
// In AppContainer.swift, replace GRDB setup with:
public let graphQLClient = ApolloGraphQLClient(
    url: URL(string: ProcessInfo.processInfo.environment["GRAPHQL_URL"] ?? "http://localhost:4000/graphql")!
)
```

Remove: `DatabaseManager`, `GRDBBankRepository`, `GRDBLedgerRepository`, `GRDBTransactionRepository`, `GRDBSpendingService` instantiation.

- [ ] **Step 2: Remove FinanceParsers and FinanceIntelligence from app target**

In Xcode: target → General → Frameworks, Libraries → remove `FinanceParsers` and `FinanceIntelligence`.

Or in `Package.swift`, remove from the app target's `dependencies`.

- [ ] **Step 3: Build — resolve any remaining compilation errors**

```
Cmd+B
```

Fix any remaining references to deleted repositories. Each should be replaced with the equivalent GraphQL query via `ApolloGraphQLClient`.

- [ ] **Step 4: Run the app**

```
Cmd+R in Xcode (requires backend running at localhost:4000)
```

Expected: App launches, ledgers list loads from GraphQL, file import sends to backend.

- [ ] **Step 5: Commit**

```bash
git add Packages/FinanceCore/Sources/FinanceCore/AppContainer/AppContainer.swift
git commit -m "feat: update AppContainer to vend ApolloGraphQLClient, remove GRDB repos"
```

---

### Task 7: End-to-end manual test

**Files:** No new files.

Before running this task, ensure `docker compose up` is running in `financeos-backend/`.

- [ ] **Step 1: Launch app in Xcode**

```
Cmd+R
```

- [ ] **Step 2: Verify ledgers list loads**

Navigate to the ledger/accounts list. Expect: shows ledgers from the backend DB (the ones created in Plan 3 testing).

- [ ] **Step 3: Import a statement file**

Use the import UI to upload `FinanceParsers/Tests/Fixtures/hdfc_card.csv`. Expect:
- Import shows "4 imported, 0 duplicates"
- Transactions appear in the ledger detail view
- Re-importing the same file shows "0 imported, 4 duplicates"

- [ ] **Step 4: View analytics**

Navigate to analytics/spending view. Expect: data loads from the backend.

- [ ] **Step 5: Final commit**

```bash
git tag v0.5.0-ios-thin-client
```

**Plan 5 complete. Full frontend/backend split operational.**
