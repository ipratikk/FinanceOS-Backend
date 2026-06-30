# FinanceOS — Plan 6: Complete iOS Thin Client Migration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove all GRDB repository dependencies from iOS ViewModels and AppContainer, replacing every data source with `ApolloGraphQLClient` calls to the backend at `localhost:4000/graphql`.

**Architecture:** All iOS ViewModels already conform to MVVM with injected dependencies. This plan replaces the injected `*Repository` and `SpendingServiceProtocol` instances with `ApolloGraphQLClient`. A shared mapping file (`GraphQLMappings.swift`) converts Apollo-generated types to FinanceCore models. FinanceIntelligence and FinanceParsers packages stay as iOS dependencies — only their GRDB data-source roles are removed. The backend receives 4 new schema additions (`deleteTransaction`, `createBank`, `clearAllData`, `limit` on transactions) before iOS changes begin.

**Tech Stack:** Apollo iOS SDK 1.25.6, FinanceOSAPI (generated local package), Node.js/Prisma (backend), Swift 6, SwiftUI

---

## Prerequisite

Plan 5 complete. Branch: create `feat/complete-thin-client(FINOS-XXX)` from `origin/main`.

```bash
git fetch origin main
git checkout -b feat/complete-thin-client origin/main
```

---

## File Map

### New files
- `Apps/FinanceOSMac/FinanceOSMac/GraphQL/GraphQLMappings.swift` — shared static mapping helpers (GraphQL types → FinanceCore models)

### Backend files (in `financeos-backend/`)
- Modify: `node_api/src/schema/typedefs.graphql` — add 3 mutations + limit on transactions
- Modify: `node_api/src/resolvers/transaction.ts` — add deleteTransaction + limit
- Modify: `node_api/src/resolvers/bank.ts` — add createBank + clearAllData

### iOS ViewModels (in `FinanceOS/Apps/FinanceOSMac/FinanceOSMac/Presentation/`)
- Modify: `Dashboard/DashboardViewModel.swift`
- Modify: `Analytics/AnalyticsViewModel.swift`
- Modify: `Transactions/TransactionsViewModel.swift`
- Modify: `Accounts/AccountTransactionsViewModel.swift`
- Modify: `Accounts/AccountTransactionsDestinationViewModel.swift`
- Modify: `Cards/CardTransactionsViewModel.swift`
- Modify: `Cards/CardTransactionsDestinationViewModel.swift`
- Modify: `Ledger/LedgerDetailViewModel.swift`
- Modify: `Banks/BanksViewModel.swift`
- Modify: `Settings/SettingsViewModel.swift`
- Modify: `Import/ImportViewModelTargetCreation.swift`
- Modify: `Navigation/DestinationWrappers.swift`
- Modify: `Navigation/AdaptiveNavigation.swift`

### AppContainer
- Modify: `Packages/FinanceCore/Sources/FinanceCore/AppContainer/AppContainer.swift`

---

## Task 1: Backend — Add missing schema + resolvers

**Repo:** `financeos-backend`

**Files:**
- Modify: `node_api/src/schema/typedefs.graphql`
- Modify: `node_api/src/resolvers/transaction.ts`
- Modify: `node_api/src/resolvers/bank.ts`

- [ ] **Step 1: Update schema**

Replace `node_api/src/schema/typedefs.graphql` with:

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

input CreateBankInput {
  name: String!
  code: String!
}

type Query {
  health: String!
  banks: [Bank!]!
  ledger(id: ID!): Ledger
  ledgers: [Ledger!]!
  transactions(ledgerId: ID, filter: TransactionFilter, limit: Int): [Transaction!]!
  analytics(ledgerId: ID, from: String, to: String): SpendingSummary!
}

type Mutation {
  uploadStatement(ledgerId: ID!, file: Upload!): ImportResult!
  createLedger(input: CreateLedgerInput!): Ledger!
  updateLedger(id: ID!, input: UpdateLedgerInput!): Ledger!
  deleteLedger(id: ID!): Boolean!
  recategorize(transactionId: ID!, category: String!): Transaction!
  deleteTransaction(id: ID!): Boolean!
  createBank(input: CreateBankInput!): Bank!
  clearAllData: Boolean!
}
```

- [ ] **Step 2: Update transaction resolver**

Replace `node_api/src/resolvers/transaction.ts` with:

```typescript
import prisma from '../prisma/client';

export const transactionResolvers = {
  Query: {
    transactions: (
      _: unknown,
      { ledgerId, filter, limit }: {
        ledgerId?: string;
        filter?: { from?: string; to?: string; category?: string };
        limit?: number;
      },
    ) => {
      const where: Record<string, unknown> = {};
      if (ledgerId) where.ledgerId = ledgerId;
      if (filter?.from) where.date = { gte: new Date(filter.from) };
      if (filter?.to) where.date = { ...(where.date as object ?? {}), lte: new Date(filter.to) };
      if (filter?.category) where.category = filter.category;
      return prisma.transaction.findMany({
        where,
        orderBy: { date: 'desc' },
        ...(limit != null ? { take: limit } : {}),
      });
    },
  },
  Mutation: {
    recategorize: (_: unknown, { transactionId, category }: { transactionId: string; category: string }) =>
      prisma.transaction.update({
        where: { id: transactionId },
        data: { category },
        include: { ledger: true },
      }),
    deleteTransaction: async (_: unknown, { id }: { id: string }) => {
      await prisma.transaction.delete({ where: { id } });
      return true;
    },
  },
  Transaction: {
    date: (parent: { date: Date | string }) =>
      parent.date instanceof Date ? parent.date.toISOString() : parent.date,
    ledger: (parent: { ledgerId: string }) =>
      prisma.ledger.findUnique({ where: { id: parent.ledgerId }, include: { bank: true } }),
  },
};
```

- [ ] **Step 3: Update bank resolver**

Replace `node_api/src/resolvers/bank.ts` with:

```typescript
import prisma from '../prisma/client';

export const bankResolvers = {
  Query: {
    banks: () => prisma.bank.findMany(),
  },
  Mutation: {
    createBank: (_: unknown, { input }: { input: { name: string; code: string } }) =>
      prisma.bank.create({ data: { name: input.name, code: input.code.toUpperCase() } }),
    clearAllData: async () => {
      await prisma.transaction.deleteMany();
      await prisma.ledger.deleteMany();
      await prisma.bank.deleteMany();
      return true;
    },
  },
  Bank: {
    ledgers: (parent: { id: string }) =>
      prisma.ledger.findMany({ where: { bankId: parent.id } }),
  },
};
```

- [ ] **Step 4: Rebuild and verify backend**

```bash
cd /path/to/financeos-backend
docker compose up --build -d
```

Wait ~15 seconds, then:

```bash
curl -s -X POST http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ health banks { id code } }"}'
```

Expected: `{"data":{"health":"ok","banks":[...]}}`

Test deleteTransaction:
```bash
# First get a transaction id
curl -s -X POST http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ transactions(limit: 1) { id narration } }"}'
```

Expected: returns 1 transaction.

- [ ] **Step 5: Run Python tests**

```bash
cd /path/to/financeos-backend
docker compose exec python-parser pytest tests/ -q
```

Expected: all pass (no Python changes in this task).

- [ ] **Step 6: Commit**

```bash
cd /path/to/financeos-backend
git add node_api/src/schema/typedefs.graphql \
        node_api/src/resolvers/transaction.ts \
        node_api/src/resolvers/bank.ts
git commit -m "feat(graphql): add deleteTransaction, createBank, clearAllData mutations; add limit to transactions query"
```

---

## Task 2: iOS — Update GraphQL operations + regen codegen

**Repo:** `FinanceOS`

**Files:**
- Modify: `Apps/FinanceOSMac/GraphQL/Operations/Queries.graphql`
- Modify: `Apps/FinanceOSMac/GraphQL/Operations/Mutations.graphql`
- Output: `Apps/FinanceOSMac/GraphQL/Generated/` (regen)

- [ ] **Step 1: Update Queries.graphql**

Replace `Apps/FinanceOSMac/GraphQL/Operations/Queries.graphql` with:

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

query GetLedger($id: ID!) {
  ledger(id: $id) {
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

query GetTransactions($ledgerId: ID, $filter: TransactionFilter, $limit: Int) {
  transactions(ledgerId: $ledgerId, filter: $filter, limit: $limit) {
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

- [ ] **Step 2: Update Mutations.graphql**

Replace `Apps/FinanceOSMac/GraphQL/Operations/Mutations.graphql` with:

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
      code
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

mutation DeleteTransaction($id: ID!) {
  deleteTransaction(id: $id)
}

mutation CreateBank($input: CreateBankInput!) {
  createBank(input: $input) {
    id
    name
    code
  }
}

mutation ClearAllData {
  clearAllData
}
```

- [ ] **Step 3: Run codegen**

```bash
cd Apps/FinanceOSMac/GraphQL
../../../.build/checkouts/apollo-ios/apollo-ios-cli generate
# If binary not in .build, use the downloaded one:
# ~/apollo-ios-cli generate
```

Expected: `Generated/SchemaTypes/Sources/Operations/` now contains `GetLedgerQuery.graphql.swift`, `DeleteTransactionMutation.graphql.swift`, `CreateBankMutation.graphql.swift`, `ClearAllDataMutation.graphql.swift`.

- [ ] **Step 4: Build to verify codegen is valid**

```bash
xcodebuild build \
  -workspace FinanceOS.xcworkspace \
  -scheme FinanceOSMac \
  -destination 'platform=macOS,arch=arm64' \
  COMPILER_INDEX_STORE_ENABLE=NO \
  -quiet 2>&1 | grep -E "error:|BUILD SUCCEEDED|BUILD FAILED"
```

Expected: `BUILD SUCCEEDED`

- [ ] **Step 5: Commit**

```bash
git add Apps/FinanceOSMac/GraphQL/
git commit -m "feat(graphql): add GetLedger, DeleteTransaction, CreateBank, ClearAllData operations; add limit to GetTransactions"
```

---

## Task 3: iOS — Add shared GraphQL mapping helpers

**Files:**
- Create: `Apps/FinanceOSMac/FinanceOSMac/GraphQL/GraphQLMappings.swift`

- [ ] **Step 1: Create GraphQLMappings.swift**

```swift
import FinanceCore
import FinanceOSAPI
import Foundation

enum GraphQLMappings {
    static let iso8601: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    static let iso8601Short: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    static func parseDate(_ string: String) -> Date {
        iso8601.date(from: string) ?? iso8601Short.date(from: string) ?? Date()
    }

    static func mapTransaction(_ item: GetTransactionsQuery.Data.Transaction) -> Transaction {
        let amountMinorUnits = Int64(item.amount * 100)
        return Transaction(
            id: UUID(uuidString: item.id) ?? UUID(),
            ledgerId: UUID(uuidString: item.ledger.id),
            postedAt: parseDate(item.date),
            description: item.narration,
            amountMinorUnits: amountMinorUnits,
            currencyCode: "INR",
            transactionType: amountMinorUnits < 0 ? .debit : .credit,
            sourceFingerprint: item.sourceFingerprint,
            categoryId: item.category,
            merchantName: item.merchant
        )
    }

    static func mapLedger(_ item: GetLedgersQuery.Data.Ledger) -> Ledger {
        let kind: FinanceCore.LedgerKind = item.kind.value == .creditCard ? .creditCard : .bankAccount
        return Ledger(
            id: UUID(uuidString: item.id) ?? UUID(),
            bankId: UUID(uuidString: item.bank.id) ?? UUID(),
            kind: kind,
            displayName: item.displayName,
            last4: item.last4 ?? "",
            closingBalance: Int64(item.balance * 100)
        )
    }

    static func mapBank(_ item: GetBanksQuery.Data.Bank) -> Bank {
        Bank(
            id: UUID(uuidString: item.id) ?? UUID(),
            bank: Banks(rawValue: item.code.lowercased()) ?? .hdfc
        )
    }

    static func mapMonthly(_ item: GetAnalyticsQuery.Data.Analytics.ByMonth) -> MonthlySpendingSummary {
        let components = item.month.split(separator: "-")
        var dc = DateComponents()
        dc.year = components.count > 0 ? Int(components[0]) : nil
        dc.month = components.count > 1 ? Int(components[1]) : nil
        dc.day = 1
        let date = Calendar.current.date(from: dc) ?? Date()
        return MonthlySpendingSummary(
            month: date,
            totalDebit: Int64(item.spend * 100),
            totalCredit: Int64(item.income * 100)
        )
    }
}
```

- [ ] **Step 2: Update AccountsViewModel and CardsViewModel to use GraphQLMappings**

In `AccountsViewModel.swift`, replace the private `mapLedger` and `mapBank` static functions:

```swift
// Before:
private static func mapLedger(_ item: GetLedgersQuery.Data.Ledger) -> Ledger { ... }
private static func mapBank(_ item: GetBanksQuery.Data.Bank) -> Bank { ... }

// After — delete both private statics, update call sites:
// loadAccounts() line: let allLedgers = data.ledgers.map(GraphQLMappings.mapLedger)
//                      self.banks = bankData.banks.map(GraphQLMappings.mapBank)
```

In `CardsViewModel.swift`, same replacement.

In `ImportViewModelStateManagement.swift`, remove the `mapLedger` and `mapBank` static functions, update call sites to use `GraphQLMappings.mapLedger` and `GraphQLMappings.mapBank`.

- [ ] **Step 3: Build**

```bash
xcodebuild build \
  -workspace FinanceOS.xcworkspace \
  -scheme FinanceOSMac \
  -destination 'platform=macOS,arch=arm64' \
  COMPILER_INDEX_STORE_ENABLE=NO \
  -quiet 2>&1 | grep -E "error:|BUILD SUCCEEDED|BUILD FAILED"
```

Expected: `BUILD SUCCEEDED`

- [ ] **Step 4: Commit**

```bash
git add Apps/FinanceOSMac/FinanceOSMac/GraphQL/GraphQLMappings.swift \
        Apps/FinanceOSMac/FinanceOSMac/Presentation/Accounts/AccountsViewModel.swift \
        Apps/FinanceOSMac/FinanceOSMac/Presentation/Cards/CardsViewModel.swift \
        Apps/FinanceOSMac/FinanceOSMac/Presentation/Import/ImportViewModelStateManagement.swift
git commit -m "refactor: extract shared GraphQLMappings helpers, update Accounts/Cards/Import VMs"
```

---

## Task 4: iOS — Migrate DashboardViewModel

**Files:**
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Dashboard/DashboardViewModel.swift`
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/AdaptiveNavigation.swift`

- [ ] **Step 1: Rewrite DashboardViewModel**

Replace the entire file:

```swift
import FinanceCore
import FinanceOSAPI
import FinanceUI
import Foundation

enum TimeRange: String, CaseIterable, Identifiable {
    case threeMonths = "3M"
    case sixMonths = "6M"
    case oneYear = "1Y"
    case all = "All"

    var id: String { rawValue }

    var months: Int? {
        switch self {
        case .threeMonths: return 3
        case .sixMonths: return 6
        case .oneYear: return 12
        case .all: return nil
        }
    }

    var visibleDays: Int? {
        switch self {
        case .threeMonths: return 90
        case .sixMonths: return 180
        case .oneYear: return 365
        case .all: return nil
        }
    }
}

@Observable @MainActor
class DashboardViewModel: AsyncLoadable {
    var currentTotals: SpendingTotals?
    var monthlySummaries: [MonthlySpendingSummary] = []
    var recentTransactions: [TransactionRow] = []
    var ledgers: [Ledger] = []
    var isLoading = false
    var error: String?
    var selectedTimeRange: TimeRange = .sixMonths

    var effectiveTotals: SpendingTotals? {
        if let totals = currentTotals, totals.transactionCount > 0 { return totals }
        guard let last = monthlySummaries.last else { return currentTotals }
        return SpendingTotals(totalDebit: last.totalDebit, totalCredit: last.totalCredit, transactionCount: 0)
    }

    var effectiveMonth: Date {
        if let totals = currentTotals, totals.transactionCount > 0 { return Date() }
        return monthlySummaries.last?.month ?? Date()
    }

    var inflowsText: String { FormatterCache.formatCurrency(minorUnits: effectiveTotals?.totalCredit ?? 0) }
    var outflowsText: String { FormatterCache.formatCurrency(minorUnits: effectiveTotals?.totalDebit ?? 0) }

    var netSavingsText: String {
        let net = max(0, (effectiveTotals?.totalCredit ?? 0) - (effectiveTotals?.totalDebit ?? 0))
        return FormatterCache.formatCurrency(minorUnits: net)
    }

    var transactionCountBadge: String {
        guard let count = effectiveTotals?.transactionCount, count > 0 else { return "" }
        return "\(count) Txns"
    }

    private let graphQLClient: ApolloGraphQLClient
    private let exportService: any ExportServiceProtocol

    init(graphQLClient: ApolloGraphQLClient, exportService: any ExportServiceProtocol) {
        self.graphQLClient = graphQLClient
        self.exportService = exportService
    }

    func load() async {
        await withLoading(onError: { [self] error in
            self.error = error.localizedDescription
            FinanceLogger.userInterface.logError("Dashboard load failed", caughtError: error, [:])
        }, {
            let months = selectedTimeRange.months
            let from = months.flatMap { Calendar.current.date(byAdding: .month, value: -$0, to: Date()) }
            let fromStr = from.map { ISO8601DateFormatter().string(from: $0) }

            async let analyticsQuery = graphQLClient.fetch(query: GetAnalyticsQuery(from: fromStr))
            async let recentQuery = graphQLClient.fetch(
                query: GetTransactionsQuery(limit: GraphQLNullable<Int>(integerLiteral: 6))
            )
            async let ledgersQuery = graphQLClient.fetch(query: GetLedgersQuery())

            let (analyticsData, recentData, ledgersData) = try await (analyticsQuery, recentQuery, ledgersQuery)
            let analytics = analyticsData.analytics

            monthlySummaries = analytics.byMonth.map(GraphQLMappings.mapMonthly)
            currentTotals = SpendingTotals(
                totalDebit: Int64(analytics.totalSpend * 100),
                totalCredit: Int64(analytics.totalIncome * 100),
                transactionCount: recentData.transactions.count
            )
            recentTransactions = recentData.transactions.map { item in
                let txn = GraphQLMappings.mapTransaction(item)
                return TransactionRow(
                    id: txn.id,
                    title: txn.description,
                    subtitle: item.ledger.displayName,
                    amountText: txn.amountMinorUnits.formattedAsAmount(
                        currencyCode: txn.currencyCode,
                        transactionType: txn.transactionType
                    ),
                    amountMinorUnits: abs(txn.amountMinorUnits),
                    transactionType: txn.transactionType,
                    postedAt: txn.postedAt,
                    merchantName: txn.merchantName,
                    categoryId: txn.categoryId,
                    sourceTransaction: txn
                )
            }
            ledgers = ledgersData.ledgers.map(GraphQLMappings.mapLedger)
        })
    }

    func setTimeRange(_ range: TimeRange) async {
        selectedTimeRange = range
        await load()
    }

    func exportNetWorthCSV() -> String {
        exportService.netWorthCSV(series: [])
    }
}
```

- [ ] **Step 2: Update AdaptiveNavigation.swift — DashboardViewModel init**

In `AdaptiveNavigation.swift`, find both `DashboardViewModel(` calls (iPhone tab + iPad detail) and replace:

```swift
// Before:
DashboardViewModel(
    spendingService: appContainer.spendingService,
    transactionRepository: appContainer.transactionRepository,
    ledgerRepository: appContainer.ledgerRepository,
    exportService: ExportService()
)

// After:
DashboardViewModel(
    graphQLClient: appContainer.graphQLClient,
    exportService: ExportService()
)
```

Also remove the `InsightNarrativeViewModel` usage in Dashboard — check if `DashboardView` still requires it. If so, pass a stub:

```swift
// If DashboardView.insightsViewModel is still required:
insightsViewModel: InsightNarrativeViewModel(
    transactionRepository: appContainer.transactionRepository  // keep for now — InsightNarrativeViewModel migrated in Task 5
)
```

- [ ] **Step 3: Build**

```bash
xcodebuild build \
  -workspace FinanceOS.xcworkspace \
  -scheme FinanceOSMac \
  -destination 'platform=macOS,arch=arm64' \
  COMPILER_INDEX_STORE_ENABLE=NO \
  -quiet 2>&1 | grep -E "error:|BUILD SUCCEEDED|BUILD FAILED"
```

Fix any type errors. Common issue: `GetTransactionsQuery` `limit` parameter is `GraphQLNullable<Int>` — use `.some(6)` if `GraphQLNullable(integerLiteral:)` isn't available:

```swift
// Alternative:
GetTransactionsQuery(ledgerId: .none, filter: .none, limit: .some(6))
```

Expected: `BUILD SUCCEEDED`

- [ ] **Step 4: Commit**

```bash
git add Apps/FinanceOSMac/FinanceOSMac/Presentation/Dashboard/DashboardViewModel.swift \
        Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/AdaptiveNavigation.swift
git commit -m "feat: migrate DashboardViewModel from GRDB to GraphQL"
```

---

## Task 5: iOS — Migrate AnalyticsViewModel

**Files:**
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Analytics/AnalyticsViewModel.swift`
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/AdaptiveNavigation.swift`

- [ ] **Step 1: Rewrite AnalyticsViewModel**

Replace the entire file:

```swift
import FinanceCore
import FinanceIntelligence
import FinanceOSAPI
import FinanceUI
import Foundation

@Observable @MainActor
class AnalyticsViewModel: AsyncLoadable {
    var monthlySummaries: [MonthlySpendingSummary] = []
    var merchantSummaries: [MerchantSummary] = []
    var categorySpend: [CategorySpendSummary] = []
    var insights: [TransactionInsight] = []
    var recentFluctuations: [FluctuationRow] = []
    var totalOutflow: Int64 = 0
    var outflowChange: Double?
    var isLoading = false
    var error: String?

    private let graphQLClient: ApolloGraphQLClient
    private let intelligenceService: (any TransactionIntelligenceService)?
    private let aggregator: any AnalyticsAggregatorProtocol

    init(
        graphQLClient: ApolloGraphQLClient,
        intelligenceService: (any TransactionIntelligenceService)? = nil,
        aggregator: any AnalyticsAggregatorProtocol
    ) {
        self.graphQLClient = graphQLClient
        self.intelligenceService = intelligenceService
        self.aggregator = aggregator
    }

    var totalOutflowText: String { MoneyFormatting.formatRounded(minorUnits: totalOutflow) }

    var categoryTotalText: String {
        let total = categorySpend.reduce(Int64(0)) { $0 + $1.totalDebit }
        return MoneyFormatting.formatRounded(minorUnits: total)
    }

    var periodLabel: String {
        guard let first = monthlySummaries.first?.id, let last = monthlySummaries.last?.id else { return "" }
        let year = Calendar.current.component(.year, from: last)
        let firstLabel = FormatterCache.shortMonth.string(from: first).uppercased()
        let lastLabel = FormatterCache.shortMonth.string(from: last).uppercased()
        return "\(firstLabel)-\(lastLabel) \(year)"
    }

    func load() async {
        await withLoading(onError: { [self] error in
            self.error = error.localizedDescription
            FinanceLogger.userInterface.logError("Analytics load failed", caughtError: error, [:])
        }, {
            let from = Calendar.current.date(byAdding: .month, value: -6, to: Date())
            let fromStr = from.map { ISO8601DateFormatter().string(from: $0) }

            async let analyticsQuery = graphQLClient.fetch(query: GetAnalyticsQuery(from: fromStr))
            async let txnsQuery = graphQLClient.fetch(query: GetTransactionsQuery())

            let (analyticsData, txnsData) = try await (analyticsQuery, txnsQuery)

            monthlySummaries = analyticsData.analytics.byMonth.map(GraphQLMappings.mapMonthly)
            totalOutflow = monthlySummaries.reduce(0) { $0 + $1.totalDebit }
            outflowChange = computeOutflowChange()

            let allTransactions = txnsData.transactions.map(GraphQLMappings.mapTransaction)
            merchantSummaries = aggregator.aggregateMerchants(allTransactions)
            categorySpend = aggregator.aggregateCategorySpend(allTransactions)

            if let service = intelligenceService {
                insights = await (try? service.generateInsights(for: allTransactions)) ?? []
                let fluctTxns = aggregator.fluctuationTransactions(from: insights, all: allTransactions)
                recentFluctuations = fluctTxns.map { txn in
                    FluctuationRow(
                        id: txn.id,
                        merchantName: txn.merchantName ?? txn.description,
                        dateText: FormatterCache.dayMonthCommaYear.string(from: txn.postedAt),
                        currencyCode: txn.currencyCode,
                        amountText: MoneyFormatting.formatWithSign(
                            minorUnits: txn.amountMinorUnits,
                            isDebit: txn.transactionType == .debit
                        ),
                        isDebit: txn.transactionType == .debit,
                        sourceTransaction: txn
                    )
                }
            }
        })
    }

    private func computeOutflowChange() -> Double? {
        guard monthlySummaries.count >= 2 else { return nil }
        let recent = monthlySummaries.suffix(3).reduce(0) { $0 + $1.totalDebit }
        let prior = monthlySummaries.prefix(3).reduce(0) { $0 + $1.totalDebit }
        guard prior > 0 else { return nil }
        return Double(recent - prior) / Double(prior) * 100
    }
}
```

- [ ] **Step 2: Update AdaptiveNavigation.swift — AnalyticsView init**

```swift
// Before:
AnalyticsView(viewModel: AnalyticsViewModel(
    spendingService: appContainer.spendingService,
    transactionRepository: appContainer.transactionRepository,
    intelligenceService: intelligence,
    aggregator: AnalyticsAggregatorService()
))

// After:
AnalyticsView(viewModel: AnalyticsViewModel(
    graphQLClient: appContainer.graphQLClient,
    intelligenceService: intelligence,
    aggregator: AnalyticsAggregatorService()
))
```

- [ ] **Step 3: Build**

```bash
xcodebuild build \
  -workspace FinanceOS.xcworkspace \
  -scheme FinanceOSMac \
  -destination 'platform=macOS,arch=arm64' \
  COMPILER_INDEX_STORE_ENABLE=NO \
  -quiet 2>&1 | grep -E "error:|BUILD SUCCEEDED|BUILD FAILED"
```

Expected: `BUILD SUCCEEDED`

- [ ] **Step 4: Commit**

```bash
git add Apps/FinanceOSMac/FinanceOSMac/Presentation/Analytics/AnalyticsViewModel.swift \
        Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/AdaptiveNavigation.swift
git commit -m "feat: migrate AnalyticsViewModel from GRDB to GraphQL"
```

---

## Task 6: iOS — Migrate TransactionsViewModel

**Files:**
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Transactions/TransactionsViewModel.swift`
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/AdaptiveNavigation.swift`

- [ ] **Step 1: Replace repository dependencies**

At the top of `TransactionsViewModel.swift`, replace:

```swift
// Before:
private let transactionRepository: TransactionRepository
private let ledgerRepository: LedgerRepository
private let intelligenceService: (any TransactionIntelligenceService)?

init(
    transactionRepository: TransactionRepository,
    ledgerRepository: LedgerRepository,
    intelligenceService: (any TransactionIntelligenceService)? = nil
) {
    self.transactionRepository = transactionRepository
    self.ledgerRepository = ledgerRepository
    self.intelligenceService = intelligenceService
}

// After:
private let graphQLClient: ApolloGraphQLClient
private let intelligenceService: (any TransactionIntelligenceService)?

init(
    graphQLClient: ApolloGraphQLClient,
    intelligenceService: (any TransactionIntelligenceService)? = nil
) {
    self.graphQLClient = graphQLClient
    self.intelligenceService = intelligenceService
}
```

- [ ] **Step 2: Replace loadTransactions()**

```swift
// Before:
func loadTransactions() async {
    await withLoading(onError: { error in
        FinanceLogger.userInterface.logError("Failed to load transactions", caughtError: error, [:])
    }, {
        rawTransactions = try await transactionRepository.fetchTransactions()
        cachedLedgers = try await ledgerRepository.fetchLedgers()
        transactionRows = makeRows(transactions: rawTransactions, results: [:])
        listState.updateAvailableYears(from: transactionRows)
    })
    Task.detached(priority: .background) { [weak self] in
        await self?.analyzeUncategorized()
    }
}

// After:
func loadTransactions() async {
    await withLoading(onError: { error in
        FinanceLogger.userInterface.logError("Failed to load transactions", caughtError: error, [:])
    }, {
        async let txnsQuery = graphQLClient.fetch(query: GetTransactionsQuery())
        async let ledgersQuery = graphQLClient.fetch(query: GetLedgersQuery())
        let (txnsData, ledgersData) = try await (txnsQuery, ledgersQuery)
        rawTransactions = txnsData.transactions.map(GraphQLMappings.mapTransaction)
        cachedLedgers = ledgersData.ledgers.map(GraphQLMappings.mapLedger)
        transactionRows = makeRows(transactions: rawTransactions, results: [:])
        listState.updateAvailableYears(from: transactionRows)
    })
    Task.detached(priority: .background) { [weak self] in
        await self?.analyzeUncategorized()
    }
}
```

- [ ] **Step 3: Replace deleteTransaction()**

```swift
// Before:
func deleteTransaction(id: UUID) async {
    await performDelete({
        try await transactionRepository.delete(id: id)
    }, onSuccess: loadTransactions)
}

// After:
func deleteTransaction(id: UUID) async {
    await performDelete({
        _ = try await graphQLClient.perform(mutation: DeleteTransactionMutation(id: id.uuidString))
    }, onSuccess: loadTransactions)
}
```

- [ ] **Step 4: Replace applyCorrection() persistence calls**

In `applyCorrection(transactionId:correctedCategoryId:)`, replace the `transactionRepository` call:

```swift
// Before:
try await transactionRepository.updateIntelligence(
    id: transactionId, categoryId: correctedCategoryId, merchantName: old.merchantName
)

// After:
_ = try await graphQLClient.perform(
    mutation: RecategorizeMutation(transactionId: transactionId.uuidString, category: correctedCategoryId)
)
```

- [ ] **Step 5: Remove batch provenance writes in runAnalyzingStage()**

In `runAnalyzingStage(service:transactions:)`, remove the two batch-write calls at the end of the loop (they write to local GRDB which no longer exists):

```swift
// Remove these two lines:
try? await transactionRepository.updateEnrichmentProvenanceBatch(provenanceBatch)
try? await transactionRepository.updateEnrichedDescriptionBatch(descriptionBatch)
```

- [ ] **Step 6: Remove provenance writes in runAnalysis()**

In `runAnalysis(service:transactions:)`, remove the inner loop that calls `repo.updateEnrichmentProvenance(...)`:

```swift
// Remove this block:
let repo = await MainActor.run { transactionRepository }
for result in results {
    try? await repo.updateEnrichmentProvenance(
        id: result.transaction.id,
        EnrichmentProvenance(...)
    )
}
```

- [ ] **Step 7: Add missing imports**

At the top of `TransactionsViewModel.swift`, add:
```swift
import FinanceOSAPI
```

- [ ] **Step 8: Update AdaptiveNavigation.swift — TransactionsView init**

```swift
// Before:
TransactionsView(
    viewModel: TransactionsViewModel(
        transactionRepository: appContainer.transactionRepository,
        ledgerRepository: appContainer.ledgerRepository,
        intelligenceService: intelligence
    )
)

// After:
TransactionsView(
    viewModel: TransactionsViewModel(
        graphQLClient: appContainer.graphQLClient,
        intelligenceService: intelligence
    )
)
```

Also update `InsightNarrativeViewModel` if it still uses `transactionRepository`:

```swift
// Check InsightNarrativeViewModel.swift — if it takes transactionRepository, 
// migrate it similarly or replace with graphQLClient temporarily
```

- [ ] **Step 9: Build**

```bash
xcodebuild build \
  -workspace FinanceOS.xcworkspace \
  -scheme FinanceOSMac \
  -destination 'platform=macOS,arch=arm64' \
  COMPILER_INDEX_STORE_ENABLE=NO \
  -quiet 2>&1 | grep -E "error:|BUILD SUCCEEDED|BUILD FAILED"
```

Expected: `BUILD SUCCEEDED`

- [ ] **Step 10: Commit**

```bash
git add Apps/FinanceOSMac/FinanceOSMac/Presentation/Transactions/TransactionsViewModel.swift \
        Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/AdaptiveNavigation.swift
git commit -m "feat: migrate TransactionsViewModel from GRDB to GraphQL"
```

---

## Task 7: iOS — Migrate AccountTransactions ViewModels

**Files:**
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Accounts/AccountTransactionsViewModel.swift`
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/AccountTransactionsDestinationViewModel.swift`
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/DestinationWrappers.swift`

- [ ] **Step 1: Rewrite AccountTransactionsDestinationViewModel**

Replace the entire file:

```swift
import FinanceCore
import FinanceOSAPI
import Foundation
import Observation

@Observable
@MainActor
final class AccountTransactionsDestinationViewModel: AsyncLoadable {
    private let ledgerId: UUID
    private let graphQLClient: ApolloGraphQLClient

    private(set) var ledger: Ledger?
    var isLoading = false

    init(ledgerId: UUID, graphQLClient: ApolloGraphQLClient) {
        self.ledgerId = ledgerId
        self.graphQLClient = graphQLClient
    }

    func load() async {
        await withLoading {
            let data = try await graphQLClient.fetch(query: GetLedgersQuery())
            ledger = data.ledgers
                .first { $0.id == ledgerId.uuidString }
                .map(GraphQLMappings.mapLedger)
        }
    }
}
```

- [ ] **Step 2: Rewrite AccountTransactionsViewModel init + load**

Replace the top of `AccountTransactionsViewModel.swift`:

```swift
// Before imports — add:
import FinanceOSAPI

// Replace stored properties:
private let graphQLClient: ApolloGraphQLClient
private let balanceService: any AccountBalanceProtocol

// Replace init:
init(
    graphQLClient: ApolloGraphQLClient,
    balanceService: (any AccountBalanceProtocol)? = nil
) {
    self.graphQLClient = graphQLClient
    self.balanceService = balanceService ?? AccountBalanceService()
}

// Replace loadTransactions(for:bankId:closingBalance:):
func loadTransactions(for accountID: UUID, bankId: UUID, closingBalance: Int64?) async {
    await withLoading(onError: { error in
        FinanceLogger.userInterface.logError(
            "Failed to load account transactions for {accountID}",
            caughtError: error,
            ["accountID": accountID.uuidString]
        )
    }, {
        async let txnsQuery = graphQLClient.fetch(
            query: GetTransactionsQuery(ledgerId: .some(accountID.uuidString))
        )
        async let ledgersQuery = graphQLClient.fetch(query: GetLedgersQuery())
        async let banksQuery = graphQLClient.fetch(query: GetBanksQuery())
        let (txnsData, ledgersData, banksData) = try await (txnsQuery, ledgersQuery, banksQuery)

        let transactions = txnsData.transactions.map(GraphQLMappings.mapTransaction)
        let ledgers = ledgersData.ledgers.map(GraphQLMappings.mapLedger)
        let banks = banksData.banks.map(GraphQLMappings.mapBank)
        bank = banks.first { $0.id == bankId }
        transactionRows = makeTransactionRows(
            transactions: transactions,
            ledgers: ledgers,
            closingBalance: closingBalance
        )
        listState.updateAvailableYears(from: transactionRows)
    })
}
```

Replace `deleteTransaction(id:accountID:bankId:closingBalance:)`:

```swift
func deleteTransaction(id: UUID, accountID: UUID, bankId: UUID, closingBalance: Int64?) async {
    await performDelete({
        _ = try await graphQLClient.perform(mutation: DeleteTransactionMutation(id: id.uuidString))
    }, onSuccess: { [self] in
        await loadTransactions(for: accountID, bankId: bankId, closingBalance: closingBalance)
    })
}
```

- [ ] **Step 3: Update AccountTransactionsDestinationView in DestinationWrappers.swift**

```swift
// Before:
struct AccountTransactionsDestinationView: View {
    let transactionRepository: any TransactionRepository
    let ledgerRepository: any LedgerRepository
    let bankRepository: any BankRepository
    @State private var viewModel: AccountTransactionsDestinationViewModel

    init(
        ledgerId: UUID,
        transactionRepository: any TransactionRepository,
        ledgerRepository: any LedgerRepository,
        bankRepository: any BankRepository
    ) {
        self.transactionRepository = transactionRepository
        self.ledgerRepository = ledgerRepository
        self.bankRepository = bankRepository
        _viewModel = State(initialValue: AccountTransactionsDestinationViewModel(
            ledgerId: ledgerId,
            ledgerRepository: ledgerRepository
        ))
    }

    var body: some View {
        ...
        AccountTransactionsView(
            ledger: ledger,
            viewModel: AccountTransactionsViewModel(
                transactionRepository: transactionRepository,
                ledgerRepository: ledgerRepository,
                bankRepository: bankRepository
            )
        )
        ...
    }
}

// After:
struct AccountTransactionsDestinationView: View {
    let graphQLClient: ApolloGraphQLClient
    @State private var viewModel: AccountTransactionsDestinationViewModel

    init(ledgerId: UUID, graphQLClient: ApolloGraphQLClient) {
        self.graphQLClient = graphQLClient
        _viewModel = State(initialValue: AccountTransactionsDestinationViewModel(
            ledgerId: ledgerId,
            graphQLClient: graphQLClient
        ))
    }

    var body: some View {
        Group {
            if let ledger = viewModel.ledger {
                AccountTransactionsView(
                    ledger: ledger,
                    viewModel: AccountTransactionsViewModel(graphQLClient: graphQLClient)
                )
                .navigationTitle(ledger.displayName)
            } else if !viewModel.isLoading {
                FDSLabel("Account not found")
            } else {
                ProgressView()
            }
        }
        .task { await viewModel.load() }
    }
}
```

- [ ] **Step 4: Update AdaptiveNavigation call site for accountTransactions**

```swift
// Before:
case let .accountTransactions(ledgerId):
    AccountTransactionsDestinationView(
        ledgerId: ledgerId,
        transactionRepository: appContainer.transactionRepository,
        ledgerRepository: appContainer.ledgerRepository,
        bankRepository: appContainer.bankRepository
    )

// After:
case let .accountTransactions(ledgerId):
    AccountTransactionsDestinationView(
        ledgerId: ledgerId,
        graphQLClient: appContainer.graphQLClient
    )
```

- [ ] **Step 5: Build**

```bash
xcodebuild build \
  -workspace FinanceOS.xcworkspace \
  -scheme FinanceOSMac \
  -destination 'platform=macOS,arch=arm64' \
  COMPILER_INDEX_STORE_ENABLE=NO \
  -quiet 2>&1 | grep -E "error:|BUILD SUCCEEDED|BUILD FAILED"
```

Expected: `BUILD SUCCEEDED`

- [ ] **Step 6: Commit**

```bash
git add Apps/FinanceOSMac/FinanceOSMac/Presentation/Accounts/AccountTransactionsViewModel.swift \
        Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/AccountTransactionsDestinationViewModel.swift \
        Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/DestinationWrappers.swift \
        Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/AdaptiveNavigation.swift
git commit -m "feat: migrate AccountTransactionsViewModel from GRDB to GraphQL"
```

---

## Task 8: iOS — Migrate CardTransactions ViewModels

**Files:**
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Cards/CardTransactionsViewModel.swift`
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/CardTransactionsDestinationViewModel.swift`
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/DestinationWrappers.swift`

- [ ] **Step 1: Rewrite CardTransactionsDestinationViewModel**

Replace the entire file:

```swift
import FinanceCore
import FinanceOSAPI
import Foundation
import Observation

@Observable
@MainActor
final class CardTransactionsDestinationViewModel: AsyncLoadable {
    private let ledgerId: UUID
    private let graphQLClient: ApolloGraphQLClient

    private(set) var ledger: Ledger?
    var isLoading = false

    init(ledgerId: UUID, graphQLClient: ApolloGraphQLClient) {
        self.ledgerId = ledgerId
        self.graphQLClient = graphQLClient
    }

    func load() async {
        await withLoading {
            let data = try await graphQLClient.fetch(query: GetLedgersQuery())
            ledger = data.ledgers
                .first { $0.id == ledgerId.uuidString }
                .map(GraphQLMappings.mapLedger)
        }
    }
}
```

- [ ] **Step 2: Rewrite CardTransactionsViewModel**

Replace the entire file:

```swift
import FinanceCore
import FinanceOSAPI
import Foundation
import Observation

@MainActor
@Observable
final class CardTransactionsViewModel: AsyncLoadable, DeletableViewModel {
    private let graphQLClient: ApolloGraphQLClient

    var transactionRows: [TransactionRow] = []
    var listState = TransactionListState()
    var isLoading = false
    var deleteError: String?

    var sections: [TransactionSection] { listState.sections(from: transactionRows) }

    init(graphQLClient: ApolloGraphQLClient) {
        self.graphQLClient = graphQLClient
    }

    func loadTransactions(for cardID: UUID) async {
        await withLoading(onError: { error in
            FinanceLogger.userInterface.logError(
                "Failed to load transactions for {cardID}",
                caughtError: error,
                ["cardID": cardID.uuidString]
            )
        }, {
            let data = try await graphQLClient.fetch(
                query: GetTransactionsQuery(ledgerId: .some(cardID.uuidString))
            )
            let transactions = data.transactions.map(GraphQLMappings.mapTransaction)
            transactionRows = transactions.map { txn in
                TransactionRow(
                    id: txn.id,
                    title: txn.description,
                    subtitle: "",
                    amountText: txn.amountMinorUnits.formattedAsAmount(
                        currencyCode: txn.currencyCode,
                        transactionType: txn.transactionType
                    ),
                    transactionType: txn.transactionType,
                    postedAt: txn.postedAt,
                    merchantName: txn.merchantName
                )
            }
            listState.updateAvailableYears(from: transactionRows)
        })
    }

    func deleteTransaction(id: UUID, cardID: UUID) async {
        await performDelete({
            _ = try await graphQLClient.perform(mutation: DeleteTransactionMutation(id: id.uuidString))
        }, onSuccess: { [self] in
            await loadTransactions(for: cardID)
        })
    }
}
```

- [ ] **Step 3: Update CardTransactionsDestinationView in DestinationWrappers.swift**

```swift
// Before:
struct CardTransactionsDestinationView: View {
    let transactionRepository: any TransactionRepository
    let ledgerRepository: any LedgerRepository
    @State private var viewModel: CardTransactionsDestinationViewModel

    init(ledgerId: UUID, transactionRepository: any TransactionRepository, ledgerRepository: any LedgerRepository) {
        self.transactionRepository = transactionRepository
        self.ledgerRepository = ledgerRepository
        _viewModel = State(initialValue: CardTransactionsDestinationViewModel(
            ledgerId: ledgerId,
            ledgerRepository: ledgerRepository
        ))
    }

    var body: some View {
        ...
        CardTransactionsView(
            ledger: ledger,
            viewModel: CardTransactionsViewModel(transactionRepository: transactionRepository)
        )
        ...
    }
}

// After:
struct CardTransactionsDestinationView: View {
    let graphQLClient: ApolloGraphQLClient
    @State private var viewModel: CardTransactionsDestinationViewModel

    init(ledgerId: UUID, graphQLClient: ApolloGraphQLClient) {
        self.graphQLClient = graphQLClient
        _viewModel = State(initialValue: CardTransactionsDestinationViewModel(
            ledgerId: ledgerId,
            graphQLClient: graphQLClient
        ))
    }

    var body: some View {
        Group {
            if let ledger = viewModel.ledger {
                CardTransactionsView(
                    ledger: ledger,
                    viewModel: CardTransactionsViewModel(graphQLClient: graphQLClient)
                )
                .navigationTitle(ledger.displayName)
            } else if !viewModel.isLoading {
                FDSLabel("Card not found")
            } else {
                ProgressView()
            }
        }
        .task { await viewModel.load() }
    }
}
```

- [ ] **Step 4: Update AdaptiveNavigation call site for cardTransactions**

```swift
// Before:
case let .cardTransactions(ledgerId):
    CardTransactionsDestinationView(
        ledgerId: ledgerId,
        transactionRepository: appContainer.transactionRepository,
        ledgerRepository: appContainer.ledgerRepository
    )

// After:
case let .cardTransactions(ledgerId):
    CardTransactionsDestinationView(
        ledgerId: ledgerId,
        graphQLClient: appContainer.graphQLClient
    )
```

- [ ] **Step 5: Build + commit**

```bash
xcodebuild build \
  -workspace FinanceOS.xcworkspace \
  -scheme FinanceOSMac \
  -destination 'platform=macOS,arch=arm64' \
  COMPILER_INDEX_STORE_ENABLE=NO \
  -quiet 2>&1 | grep -E "error:|BUILD SUCCEEDED|BUILD FAILED"
```

Expected: `BUILD SUCCEEDED`

```bash
git add Apps/FinanceOSMac/FinanceOSMac/Presentation/Cards/CardTransactionsViewModel.swift \
        Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/CardTransactionsDestinationViewModel.swift \
        Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/DestinationWrappers.swift \
        Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/AdaptiveNavigation.swift
git commit -m "feat: migrate CardTransactionsViewModel from GRDB to GraphQL"
```

---

## Task 9: iOS — Migrate LedgerDetailViewModel

**Files:**
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Ledger/LedgerDetailViewModel.swift`
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/DestinationWrappers.swift`

- [ ] **Step 1: Rewrite LedgerDetailViewModel**

Replace the entire file:

```swift
import FinanceCore
import FinanceOSAPI
import FinanceUI
import Foundation
import Observation

@Observable
@MainActor
final class LedgerDetailViewModel: AsyncLoadable {
    private let ledgerId: UUID
    private let graphQLClient: ApolloGraphQLClient

    private(set) var ledger: Ledger?
    private(set) var bank: Bank?
    var isLoading = false

    init(ledgerId: UUID, graphQLClient: ApolloGraphQLClient) {
        self.ledgerId = ledgerId
        self.graphQLClient = graphQLClient
    }

    func load() async {
        await withLoading {
            async let ledgerQuery = graphQLClient.fetch(query: GetLedgersQuery())
            async let banksQuery = graphQLClient.fetch(query: GetBanksQuery())
            let (ledgerData, banksData) = try await (ledgerQuery, banksQuery)

            let allLedgers = ledgerData.ledgers.map(GraphQLMappings.mapLedger)
            ledger = allLedgers.first { $0.id == ledgerId }
            let allBanks = banksData.banks.map(GraphQLMappings.mapBank)
            if let bankId = ledger?.bankId {
                bank = allBanks.first { $0.id == bankId }
            }
        }
    }

    var balanceText: String {
        FormatterCache.formatCurrency(minorUnits: ledger?.closingBalance ?? 0)
    }

    var navigationTitle: String {
        ledger?.displayName ?? "Ledger"
    }
}
```

- [ ] **Step 2: Update LedgerDetailDestinationView in DestinationWrappers.swift**

```swift
// Before:
struct LedgerDetailDestinationView: View {
    @State private var viewModel: LedgerDetailViewModel

    init(ledgerId: UUID) {
        let container = AppContainer.shared
        _viewModel = State(initialValue: LedgerDetailViewModel(
            ledgerId: ledgerId,
            ledgerRepository: container.ledgerRepository,
            bankRepository: container.bankRepository
        ))
    }
    ...
}

// After:
struct LedgerDetailDestinationView: View {
    @State private var viewModel: LedgerDetailViewModel

    init(ledgerId: UUID) {
        _viewModel = State(initialValue: LedgerDetailViewModel(
            ledgerId: ledgerId,
            graphQLClient: AppContainer.shared.graphQLClient
        ))
    }

    var body: some View {
        LedgerDetailView(viewModel: viewModel)
    }
}
```

- [ ] **Step 3: Build + commit**

```bash
xcodebuild build \
  -workspace FinanceOS.xcworkspace \
  -scheme FinanceOSMac \
  -destination 'platform=macOS,arch=arm64' \
  COMPILER_INDEX_STORE_ENABLE=NO \
  -quiet 2>&1 | grep -E "error:|BUILD SUCCEEDED|BUILD FAILED"
```

Expected: `BUILD SUCCEEDED`

```bash
git add Apps/FinanceOSMac/FinanceOSMac/Presentation/Ledger/LedgerDetailViewModel.swift \
        Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/DestinationWrappers.swift
git commit -m "feat: migrate LedgerDetailViewModel from GRDB to GraphQL"
```

---

## Task 10: iOS — Migrate BanksViewModel

**Files:**
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Banks/BanksViewModel.swift`
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/AdaptiveNavigation.swift`

Note: The backend has no `updateBank` or `deleteBank` mutations. These methods are removed; the UI's edit/delete actions should be hidden or disabled (check BanksView for the controls that trigger them).

- [ ] **Step 1: Rewrite BanksViewModel**

Replace the entire file:

```swift
import FinanceCore
import FinanceOSAPI
import Foundation
import Observation

@MainActor
@Observable
final class BanksViewModel: AsyncLoadable {
    private let graphQLClient: ApolloGraphQLClient

    var banks: [Bank] = []
    var ledgersByBank: [UUID: [Ledger]] = [:]
    var isLoading = false

    init(graphQLClient: ApolloGraphQLClient) {
        self.graphQLClient = graphQLClient
    }

    func loadBanks() async {
        await withLoading(onError: { error in
            FinanceLogger.userInterface.logError("Failed to load banks", caughtError: error, [:])
        }, {
            async let banksQuery = graphQLClient.fetch(query: GetBanksQuery())
            async let ledgersQuery = graphQLClient.fetch(query: GetLedgersQuery())
            let (banksData, ledgersData) = try await (banksQuery, ledgersQuery)

            banks = banksData.banks.map(GraphQLMappings.mapBank)
            let allLedgers = ledgersData.ledgers.map(GraphQLMappings.mapLedger)
            var map: [UUID: [Ledger]] = [:]
            for ledger in allLedgers {
                map[ledger.bankId, default: []].append(ledger)
            }
            ledgersByBank = map
        })
    }
}
```

- [ ] **Step 2: Update AdaptiveNavigation.swift — BanksView init**

```swift
// Before:
BanksView(
    viewModel: BanksViewModel(
        repository: appContainer.bankRepository,
        ledgerRepository: appContainer.ledgerRepository
    )
)

// After:
BanksView(
    viewModel: BanksViewModel(graphQLClient: appContainer.graphQLClient)
)
```

- [ ] **Step 3: Fix BanksView if it references removed methods**

Open `Apps/FinanceOSMac/FinanceOSMac/Presentation/Banks/BanksView.swift`. If it calls `viewModel.updateBank()` or `viewModel.deleteBank()`, either:
- Remove the button/control that triggers those actions
- Or comment them out with `// TODO: bank edit/delete not yet supported in backend`

- [ ] **Step 4: Build + commit**

```bash
xcodebuild build \
  -workspace FinanceOS.xcworkspace \
  -scheme FinanceOSMac \
  -destination 'platform=macOS,arch=arm64' \
  COMPILER_INDEX_STORE_ENABLE=NO \
  -quiet 2>&1 | grep -E "error:|BUILD SUCCEEDED|BUILD FAILED"
```

Expected: `BUILD SUCCEEDED`

```bash
git add Apps/FinanceOSMac/FinanceOSMac/Presentation/Banks/BanksViewModel.swift \
        Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/AdaptiveNavigation.swift
git commit -m "feat: migrate BanksViewModel from GRDB to GraphQL (read-only)"
```

---

## Task 11: iOS — Migrate SettingsViewModel

**Files:**
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Settings/SettingsViewModel.swift`
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/AdaptiveNavigation.swift`

- [ ] **Step 1: Rewrite SettingsViewModel**

Replace the entire file:

```swift
import FinanceCore
import FinanceOSAPI
import Foundation
import Observation

@Observable
@MainActor
final class SettingsViewModel {
    private let graphQLClient: ApolloGraphQLClient
    var errorMessage: String?

    init(graphQLClient: ApolloGraphQLClient) {
        self.graphQLClient = graphQLClient
    }

    func clearAllData() async {
        do {
            _ = try await graphQLClient.perform(mutation: ClearAllDataMutation())
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
```

- [ ] **Step 2: Update AdaptiveNavigation.swift — SettingsView init**

```swift
// Before:
SettingsView(viewModel: SettingsViewModel(bankRepository: appContainer.bankRepository))

// After:
SettingsView(viewModel: SettingsViewModel(graphQLClient: appContainer.graphQLClient))
```

- [ ] **Step 3: Build + commit**

```bash
xcodebuild build \
  -workspace FinanceOS.xcworkspace \
  -scheme FinanceOSMac \
  -destination 'platform=macOS,arch=arm64' \
  COMPILER_INDEX_STORE_ENABLE=NO \
  -quiet 2>&1 | grep -E "error:|BUILD SUCCEEDED|BUILD FAILED"
```

Expected: `BUILD SUCCEEDED`

```bash
git add Apps/FinanceOSMac/FinanceOSMac/Presentation/Settings/SettingsViewModel.swift \
        Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/AdaptiveNavigation.swift
git commit -m "feat: migrate SettingsViewModel from GRDB to clearAllData GraphQL mutation"
```

---

## Task 12: iOS — Migrate ImportViewModelTargetCreation

**Files:**
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Import/ImportViewModelTargetCreation.swift`
- Modify: `Apps/FinanceOSMac/FinanceOSMac/Presentation/Import/ImportViewModel.swift`

- [ ] **Step 1: Rewrite ImportViewModelTargetCreation.swift**

Replace the entire file:

```swift
import FinanceCore
import FinanceOSAPI
import FinanceParsers
import Foundation
import OSLog

extension ImportViewModel {
    private struct TargetParams {
        let bankId: UUID
        let bankName: String
        let statement: ParsedStatement
        let customName: String?
        let last4: String
        let nickname: String
    }

    func createTargetFromDetected(
        customName: String? = nil,
        nickname: String = "",
        last4: String = "",
        selectedBank: Banks? = nil,
        ownerName: String = "",
        accountType: String = "savings",
        cardType: CardNetwork = .other,
        cardProductId: String = "",
        encryptedCardNumber: String = "",
        linkedLedgerId: UUID? = nil,
        isCard: Bool? = nil
    ) async {
        guard let statement = importSession.parsedStatements.first else {
            importSession.errorMessage = ImportError
                .importFailed(reason: "No parsed statements available").userMessage
            return
        }

        do {
            let (bankId, bankName) = try await resolveOrCreateBank(
                for: statement, selectedBank: selectedBank
            )
            let params = TargetParams(
                bankId: bankId,
                bankName: bankName,
                statement: statement,
                customName: customName,
                last4: last4,
                nickname: nickname
            )
            let isCardTarget = isCard ?? (statement.cardLast4 != nil)
            if isCardTarget {
                try await createCard(
                    params,
                    ownerName: ownerName,
                    cardType: cardType,
                    cardProductId: cardProductId,
                    linkedLedgerId: linkedLedgerId
                )
            } else {
                try await createAccount(params, ownerName: ownerName, accountType: accountType)
            }
        } catch {
            let errorDesc = error.localizedDescription
            logger.error("Failed to create target: \(errorDesc)")
            importSession.errorMessage = "Failed to create target: \(errorDesc)"
        }
    }

    private func resolveOrCreateBank(
        for statement: ParsedStatement,
        selectedBank: Banks?
    ) async throws -> (id: UUID, name: String) {
        let banksData = try await graphQLClient.fetch(query: GetBanksQuery())
        let existingBanks = banksData.banks

        if let bankCase = selectedBank {
            if let found = existingBanks.first(where: { $0.code.lowercased() == bankCase.rawValue }) {
                return (UUID(uuidString: found.id) ?? UUID(), found.name)
            }
            let result = try await graphQLClient.perform(
                mutation: CreateBankMutation(input: CreateBankInput(
                    name: bankCase.displayName,
                    code: bankCase.rawValue.uppercased()
                ))
            )
            return (UUID(uuidString: result.createBank.id) ?? UUID(), result.createBank.name)
        }

        let detectedBankName = statement.bankName
        if let found = existingBanks.first(where: { $0.name == detectedBankName }) {
            return (UUID(uuidString: found.id) ?? UUID(), found.name)
        }

        let matchingBankCase = Banks.allCases.first { bankCase in
            ImportHelpers.fuzzyMatch(bankCase.displayName, detectedBankName)
        }
        if let bankCase = matchingBankCase {
            let result = try await graphQLClient.perform(
                mutation: CreateBankMutation(input: CreateBankInput(
                    name: bankCase.displayName,
                    code: bankCase.rawValue.uppercased()
                ))
            )
            return (UUID(uuidString: result.createBank.id) ?? UUID(), result.createBank.name)
        }

        throw BankResolutionError(detected: detectedBankName)
    }

    private func createCard(
        _ params: TargetParams,
        ownerName: String = "",
        cardType: CardNetwork,
        cardProductId: String = "",
        linkedLedgerId: UUID? = nil
    ) async throws {
        let customNameTrimmed = params.customName?.trimmingCharacters(in: .whitespaces)
        let displayName = customNameTrimmed ?? params.bankName
        let cardDisplayName = params.last4.isEmpty ? displayName : "\(displayName) •••• \(params.last4)"

        let input = CreateLedgerInput(
            displayName: cardDisplayName,
            kind: .init(FinanceOSAPI.LedgerKind.creditCard),
            last4: params.last4.isEmpty ? .none : .some(params.last4),
            bankId: .some(params.bankId.uuidString)
        )
        let result = try await graphQLClient.perform(mutation: CreateLedgerMutation(input: input))
        let newId = UUID(uuidString: result.createLedger.id) ?? UUID()

        let ledgersData = try await graphQLClient.fetch(query: GetLedgersQuery())
        ledgers = ledgersData.ledgers.map(GraphQLMappings.mapLedger)
        importSession.selectedTarget = .ledger(newId)
        logger.info("Created credit card via GraphQL: \(cardDisplayName)")
    }

    private func createAccount(
        _ params: TargetParams,
        ownerName: String = "",
        accountType: String
    ) async throws {
        let customNameTrimmed = params.customName?.trimmingCharacters(in: .whitespaces)
        let displayName = customNameTrimmed ?? params.bankName
        let accountDisplayName = params.last4.isEmpty ? displayName : "\(displayName) •••• \(params.last4)"

        let input = CreateLedgerInput(
            displayName: accountDisplayName,
            kind: .init(FinanceOSAPI.LedgerKind.bankAccount),
            last4: params.last4.isEmpty ? .none : .some(params.last4),
            bankId: .some(params.bankId.uuidString)
        )
        let result = try await graphQLClient.perform(mutation: CreateLedgerMutation(input: input))
        let newId = UUID(uuidString: result.createLedger.id) ?? UUID()

        let ledgersData = try await graphQLClient.fetch(query: GetLedgersQuery())
        ledgers = ledgersData.ledgers.map(GraphQLMappings.mapLedger)
        importSession.selectedTarget = .ledger(newId)
        logger.info("Created bank account via GraphQL: \(accountDisplayName)")
    }
}
```

- [ ] **Step 2: Remove bankRepository and ledgerRepository from ImportViewModel**

In `ImportViewModel.swift`, remove the `bankRepository` and `ledgerRepository` stored properties and init parameters:

```swift
// Remove from stored properties:
let bankRepository: any BankRepository
let ledgerRepository: any LedgerRepository

// Remove from init parameters:
bankRepository: any BankRepository,
ledgerRepository: any LedgerRepository,

// Remove from init body:
self.bankRepository = bankRepository
self.ledgerRepository = ledgerRepository

// Update AccountMatcher init (it takes repos — check if it's still needed):
// If AccountMatcher is only used for autoSelectMatchingTarget(), and it
// internally fetches via repos, replace with a GraphQL-based lookup instead.
// See Step 3.
```

- [ ] **Step 3: Replace AccountMatcher with GraphQL-based matching**

`AccountMatcher` takes `ledgerRepository` and `bankRepository`. Since those are removed, replace `autoSelectMatchingTarget()` in `ImportViewModelStateManagement.swift` to match against the already-loaded `ledgers` and `banks` arrays instead:

```swift
func autoSelectMatchingTarget() async {
    guard let statement = importSession.parsedStatements.first else { return }
    if let target = FinanceCore.ImportTargetMatcher.bestTarget(
        for: statement,
        ledgers: ledgers,
        banks: banks
    ) {
        importSession.selectedTarget = target
        await detectDuplicates(for: target)
    }
}
```

Check that `ImportTargetMatcher.bestTarget(for:ledgers:banks:)` exists in FinanceCore. If it does, this replaces the AccountMatcher entirely without the repos.

- [ ] **Step 4: Update ImportViewModel init — new signature**

After removing bankRepository and ledgerRepository:

```swift
init(
    graphQLClient: ApolloGraphQLClient,
    initialTarget: TransactionImportTarget? = nil,
    categorizationScheduler: CategorizationScheduler? = nil,
    fileParser: (any StatementParsingProtocol)? = nil,
    duplicateDetector: (any DuplicateDetectingProtocol)? = nil
) {
    importSession = ImportSession()
    self.graphQLClient = graphQLClient
    self.categorizationScheduler = categorizationScheduler
    self.fileParser = fileParser ?? ImportFileParser()
    self.duplicateDetector = duplicateDetector ?? ImportDuplicateDetector()
    if let initialTarget {
        importSession.selectedTarget = initialTarget
    }
}
```

- [ ] **Step 5: Update AdaptiveNavigation.swift + ImportView.swift + ImportFlowSnapshotTests.swift call sites**

```swift
// AdaptiveNavigation.swift — Before:
ImportView(
    viewModel: ImportViewModel(
        graphQLClient: appContainer.graphQLClient,
        bankRepository: appContainer.bankRepository,
        ledgerRepository: appContainer.ledgerRepository,
        initialTarget: navigator.pendingImportTarget,
        categorizationScheduler: categorizationScheduler
    )
)

// After:
ImportView(
    viewModel: ImportViewModel(
        graphQLClient: appContainer.graphQLClient,
        initialTarget: navigator.pendingImportTarget,
        categorizationScheduler: categorizationScheduler
    )
)
```

```swift
// ImportView.swift preview — Before:
ImportView(
    viewModel: ImportViewModel(
        graphQLClient: ApolloGraphQLClient(),
        bankRepository: MockBankRepository(),
        ledgerRepository: MockLedgerRepository()
    )
)

// After:
ImportView(
    viewModel: ImportViewModel(graphQLClient: ApolloGraphQLClient())
)
```

```swift
// ImportFlowSnapshotTests.swift — Before:
let viewModel = ImportViewModel(
    graphQLClient: ApolloGraphQLClient(),
    bankRepository: MockBankRepository(),
    ledgerRepository: MockLedgerRepository()
)

// After:
let viewModel = ImportViewModel(graphQLClient: ApolloGraphQLClient())
```

- [ ] **Step 6: Build**

```bash
xcodebuild build \
  -workspace FinanceOS.xcworkspace \
  -scheme FinanceOSMac \
  -destination 'platform=macOS,arch=arm64' \
  COMPILER_INDEX_STORE_ENABLE=NO \
  -quiet 2>&1 | grep -E "error:|BUILD SUCCEEDED|BUILD FAILED"
```

Expected: `BUILD SUCCEEDED`

- [ ] **Step 7: Commit**

```bash
git add Apps/FinanceOSMac/FinanceOSMac/Presentation/Import/ \
        Apps/FinanceOSMac/FinanceOSMac/Presentation/Navigation/AdaptiveNavigation.swift \
        Apps/FinanceOSMac/FinanceOSMacSnapshotTests/Flows/ImportFlowSnapshotTests.swift
git commit -m "feat: migrate ImportViewModelTargetCreation to CreateLedger/CreateBank GraphQL mutations"
```

---

## Task 13: iOS — Clean AppContainer + remove GRDB repos

**Files:**
- Modify: `Packages/FinanceCore/Sources/FinanceCore/AppContainer/AppContainer.swift`

- [ ] **Step 1: Rewrite AppContainer**

Replace the entire file:

```swift
import Foundation

/// Composition root. Vends ApolloGraphQLClient as the sole data source.
/// All ViewModels receive graphQLClient via init injection.
@MainActor
public final class AppContainer {
    public static let shared = AppContainer()

    public let graphQLClient: ApolloGraphQLClient = {
        let urlString = ProcessInfo.processInfo.environment["GRAPHQL_URL"] ?? "http://localhost:4000/graphql"
        // swiftlint:disable:next force_unwrapping
        return ApolloGraphQLClient(url: URL(string: urlString)!)
    }()

    private init() {}
}
```

- [ ] **Step 2: Build**

```bash
xcodebuild build \
  -workspace FinanceOS.xcworkspace \
  -scheme FinanceOSMac \
  -destination 'platform=macOS,arch=arm64' \
  COMPILER_INDEX_STORE_ENABLE=NO \
  -quiet 2>&1 | grep -E "error:|BUILD SUCCEEDED|BUILD FAILED"
```

If there are remaining references to `appContainer.transactionRepository`, `appContainer.bankRepository`, etc., fix them by replacing with `appContainer.graphQLClient` and updating the corresponding ViewModel init. Every such reference is a missed migration — find and fix.

Expected: `BUILD SUCCEEDED`

- [ ] **Step 3: Run parser tests**

```bash
swift test --package-path Packages/FinanceParsers --parallel 2>&1 | tail -5
swift test --package-path Packages/FinanceCore --parallel 2>&1 | tail -5
```

Expected: all pass.

- [ ] **Step 4: SwiftLint**

```bash
swiftlint lint --strict --quiet 2>&1
```

Fix any violations before committing.

- [ ] **Step 5: Commit**

```bash
git add Packages/FinanceCore/Sources/FinanceCore/AppContainer/AppContainer.swift
git commit -m "feat: remove GRDB repos from AppContainer — graphQLClient is now the sole data source"
```

---

## Task 14: End-to-end test + tag

**Files:** None.

Requires: `docker compose up` running in `financeos-backend/`.

- [ ] **Step 1: Verify backend healthy**

```bash
curl -s http://localhost:4000/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 2: Build and run in Xcode**

```
Cmd+R in Xcode
```

Expected: App launches.

- [ ] **Step 3: Verify Accounts list loads**

Navigate to Accounts tab. Expected: ledgers from backend appear (HDFC Card Test, HDFC Card GraphQL).

- [ ] **Step 4: Verify Transactions list loads**

Navigate to Transactions tab. Expected: transactions from backend appear with dates and amounts.

- [ ] **Step 5: Verify Analytics loads**

Navigate to Analytics tab. Expected: monthly spending chart renders, category breakdown visible.

- [ ] **Step 6: Verify Dashboard loads**

Navigate to Dashboard. Expected: inflows/outflows cards show backend totals, recent transactions listed.

- [ ] **Step 7: Verify Import flow**

Navigate to Import. Select a ledger, upload `Packages/FinanceParsers/Tests/Fixtures/hdfc_card.csv`. Expected:
- Import result shows N imported, M duplicates
- Re-importing same file → 0 imported, N duplicates

- [ ] **Step 8: Verify delete transaction**

In Transactions list, delete one transaction. Expected: row disappears, backend confirms deletion.

- [ ] **Step 9: Lint + tests**

```bash
swiftlint lint --strict --quiet 2>&1
swift test --package-path Packages/FinanceParsers --parallel 2>&1 | tail -3
swift test --package-path Packages/FinanceCore --parallel 2>&1 | tail -3
```

Expected: 0 lint violations, all tests pass.

- [ ] **Step 10: Tag**

```bash
git tag -a v0.6.0-full-thin-client -m "Plan 6 complete: all ViewModels migrated to GraphQL, GRDB repos removed from AppContainer"
git push origin feat/complete-thin-client
git push origin v0.6.0-full-thin-client
```

---

## Self-Review Notes

**Spec coverage:**
- ✅ Backend: deleteTransaction, createBank, clearAllData mutations, limit on transactions
- ✅ iOS: DashboardViewModel, AnalyticsViewModel, TransactionsViewModel migrated
- ✅ iOS: AccountTransactionsViewModel, CardTransactionsViewModel migrated
- ✅ iOS: LedgerDetailViewModel, BanksViewModel, SettingsViewModel migrated
- ✅ iOS: ImportViewModelTargetCreation migrated
- ✅ iOS: AppContainer cleaned
- ⚠️ Not in scope: FinanceParsers removal (Import preview still uses local parsers — acceptable, file upload goes to backend)
- ⚠️ Not in scope: FinanceIntelligence removal (Intelligence Hub uses local ML — deferred to Plan 7)
- ⚠️ Not in scope: Bank edit/delete mutations (BanksViewModel is now read-only)
- ⚠️ Not in scope: Dashboard netWorthTimeSeries (no backend equivalent, removed)
- ⚠️ Not in scope: InsightNarrativeViewModel migration (check if it uses transactionRepository; if so, migrate same pattern as TransactionsViewModel)
