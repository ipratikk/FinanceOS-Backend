# FinanceOS Card Scraper

Standalone, offline data-acquisition tool. Scrapes credit card metadata from bank
websites, normalizes it, and (optionally) enriches/validates it via Claude. Not
part of the runtime services (`node_api`, `python_service`) — run manually when
the card catalog needs refreshing, commit the resulting JSON.

Moved here from `ipratikk/FinanceOS` (`tools/card-scraper`) since scraped card
metadata is a backend/data-catalog concern, not app code.

## Prerequisites

```bash
cd card-scraper
npm install
npx playwright install chromium
```

Requires `ANTHROPIC_API_KEY` in env for the Claude enrichment step (if used).

## Running

```bash
npm run hdfc     # scrape + normalize HDFC only
npm run icici    # scrape + normalize ICICI only
npm run scrape   # scrape all banks + enrich + validate
```

## Pipeline

```
Stage 1 — Scrape (Playwright / fetch)
  sources/<bank>/cards.js → output/raw/<bank>_raw.json

  HDFC:  Playwright intercepts XHR on hdfc.bank.in listing page.
         Then visits each card's detailsLink on hdfc.bank.in to scrape network.

  ICICI: fetch() scrapes icici.bank.in listing, then visits each card detail
         page for description, image, rewards, benefits, and network.
         Network detected from already-loaded page — no extra HTTP requests.

Stage 2 — Normalize (field mapping)
  normalizers/creditCardNormalizer.js → output/normalized/<bank>_cards.json
  Passes network through from raw. Resolves relative image URLs using
  bank base domains: hdfc.bank.in / icici.bank.in

Stage 3 — Enrich + Validate (Claude, via cardEnricher.js)
  processors/cardEnricher.js
    → normalizes names (strips bank prefix, "Credit Card" suffix, double spaces/hyphens)
    → passes network through unchanged — never inferred from name
    → synthesizes description if missing (≥20 chars required)
    → deduplicates rewards and benefits arrays
    → fixes relative detailsLinks to full HTTPS URLs
    → drops cards missing image or applyLink (hard errors)
    → warns on null network, short description, dirty names
```

## Network detection — `utils/networkDetector.js`

Network is scraped from each card's detail page, not inferred from card names.

Detection order (stops at first match):
1. `<img>` `src` and `alt` attributes — most reliable (payment network logos)
2. Targeted CSS selectors — `.card-network`, `[class*="visa"]`, `h1`, `.card-title`, etc.
3. Full body text — last resort

Valid values: `"Visa"` `"Mastercard"` `"Amex"` `"RuPay"` `"Diners"`

If the detail page doesn't expose the network, `network` is `null` — card is kept with a validation warning.

## Output schema

```json
{
  "bank": "HDFC",
  "name": "Millennia",
  "network": "Visa",
  "description": "Earn 5% cashback on online shopping at Amazon, Flipkart, and Myntra.",
  "image": "https://www.hdfc.bank.in/.../millennia.png",
  "applyLink": "https://applyonline.hdfc.bank.in/...",
  "detailsLink": "https://www.hdfc.bank.in/credit-cards/millennia",
  "rewards": ["5% cashback on Amazon, Flipkart, Myntra", "₹1000 gift voucher on ₹1L quarterly spend"],
  "benefits": ["Shopping", "Dining"]
}
```

## Validation rules

| Field | Rule | On fail |
|-------|------|---------|
| `name` | Non-empty, no `  ` or `--` artifacts | Drop |
| `network` | One of: Visa, Mastercard, Amex, RuPay, Diners | Warn |
| `description` | Non-empty, ≥20 chars | Warn (Claude synthesizes) |
| `image` | Full HTTPS URL | Drop |
| `applyLink` | Full HTTPS URL | Drop |
| `detailsLink` | Full HTTPS URL | Drop |
| `rewards` | Array ≥1 unique item | Drop |
| `benefits` | Array ≥1 unique item from valid list | Drop |

**Drop** = excluded from output. **Warn** = kept, issue logged to console.

## Output files

```
card-scraper/output/
├── raw/                     ← gitignored, debug only
│   ├── hdfc_raw.json
│   └── icici_raw.json
└── normalized/               ← committed
    ├── hdfc_cards.json
    ├── icici_cards.json
    └── all_cards.json        ← merged (when running all)
```

## Supported banks

| Bank | Source | Network scrape | Runner |
|------|--------|----------------|--------|
| HDFC | `sources/hdfc/cards.js` | detail page visit (hdfc.bank.in) | `npm run hdfc` |
| ICICI | `sources/icici/cards.js` | inline from detail page (icici.bank.in) | `npm run icici` |
| Amex | `sources/amex/` | — | no runner yet |
| Axis | `sources/axis/` | — | no runner yet |
| AU | `sources/au/` | — | no runner yet |
| IDFC | `sources/idfc/` | — | no runner yet |
| SBI | `sources/sbi/` | — | no runner yet |
| Scapia | `sources/scapia/` | — | no runner yet |
| Yes Bank | `sources/yesbank/` | — | no runner yet |

## Adding a new bank

1. Create `sources/<bank>/cards.js` — export `fetch<Bank>Cards()`
2. Import `detectNetworkFromHTML` or `fetchNetworkFromURL` from `utils/networkDetector.js`
3. Extract `network` from each card's detail page and include it in the card object
4. Create `runners/run-<bank>.js` following the HDFC runner pattern
5. Add `"<bank>": "node runners/run-<bank>.js"` to `package.json`

## Troubleshooting

- 0 cards scraped → bank site structure changed, source parser needs updating
- High `null` network rate → detail pages don't expose network logos; inspect HTML and update selectors in `utils/networkDetector.js`
- Playwright launch fails → run `npx playwright install chromium`
- Enrichment JSON parse error → Claude response malformed; re-run or reduce batch size in `cardEnricher.js`
