#!/bin/bash

set -e

echo "======================================"
echo "Setting up FinanceOS Card Scraper"
echo "======================================"

# Root folders

mkdir -p \
sources \
normalizers \
storage \
output/raw \
utils

# Bank source folders

BANKS=(
    hdfc
    icici
    axis
    amex
    sbi
    idfc
    au
    yesbank
    scapia
)

for bank in "${BANKS[@]}"
do
    mkdir -p "sources/$bank"

    touch "sources/$bank/cards.js"

    echo "Created sources/$bank/cards.js"
done

# Core files

touch \
index.js \
storage/cardsRepository.js \
normalizers/creditCardNormalizer.js \
utils/httpClient.js

# package.json if missing

if [ ! -f package.json ]; then
cat > package.json <<EOF
{
  "name": "card-scraper",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "start": "node index.js"
  }
}
EOF

echo "Created package.json"
fi

# HTTP utility

cat > utils/httpClient.js <<EOF
export async function fetchJSON(url) {
    const response =
        await fetch(url, {
            headers: {
                "User-Agent":
                    "Mozilla/5.0"
            }
        });

    if (!response.ok) {
        throw new Error(
            \`HTTP \${response.status}\`
        );
    }

    return response.json();
}
EOF

# Normalizer

cat > normalizers/creditCardNormalizer.js <<EOF
export function normalizeCard(
    rawCard,
    bank
) {
    return {
        bank,

        id:
            rawCard.id ?? null,

        name:
            rawCard.cardTitle ??
            rawCard.name ??
            null,

        description:
            rawCard.cardDescription ??
            null,

        image:
            rawCard.cardImage ??
            null,

        applyLink:
            rawCard.primaryButtonLink ??
            null,

        detailsLink:
            rawCard.secondaryButtonLink ??
            null,

        rewards:
            rawCard.featureList ??
            [],

        benefits:
            rawCard.benefitList ??
            []
    };
}
EOF

# Repository

cat > storage/cardsRepository.js <<EOF
import fs from "fs";

export function saveCards(
    filename,
    cards
) {
    fs.writeFileSync(
        filename,
        JSON.stringify(
            cards,
            null,
            2
        )
    );
}
EOF

# HDFC scraper template

cat > sources/hdfc/cards.js <<EOF
import {
    fetchJSON
} from "../../utils/httpClient.js";

const API_URL =
    "https://www.hdfc.bank.in/content/hdfcbankpws/api/products.json/content-fragments/cards/credit-cards/credit-card-listing";

export async function fetchHDFCCards() {
    const json =
        await fetchJSON(
            API_URL
        );

    return (
        json.response ?? []
    );
}
EOF

# Main orchestrator

cat > index.js <<EOF
import {
    fetchHDFCCards
} from "./sources/hdfc/cards.js";

import {
    normalizeCard
} from "./normalizers/creditCardNormalizer.js";

import {
    saveCards
} from "./storage/cardsRepository.js";

async function main() {
    console.log(
        "Fetching HDFC cards..."
    );

    const rawCards =
        await fetchHDFCCards();

    console.log(
        \`Found \${rawCards.length} cards\`
    );

    const normalized =
        rawCards.map(
            card =>
                normalizeCard(
                    card,
                    "HDFC"
                )
        );

    saveCards(
        "./output/cards_catalog.json",
        normalized
    );

    saveCards(
        "./output/raw/hdfc_raw.json",
        rawCards
    );

    console.log(
        "Saved output/cards_catalog.json"
    );

    console.log(
        "Saved output/raw/hdfc_raw.json"
    );
}

main().catch(
    console.error
);
EOF

echo ""
echo "======================================"
echo "Architecture setup complete"
echo "======================================"

echo ""
echo "Run:"
echo "npm install"
echo "node index.js"