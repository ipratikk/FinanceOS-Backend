#!/bin/bash

set -e

echo ""
echo "======================================"
echo "FinanceOS Card Scraper Rebootstrap"
echo "======================================"
echo ""

# ---------------------------------------------------
# CLEAN OLD STRUCTURE
# ---------------------------------------------------

echo "Cleaning old structure..."

rm -rf \
normalizers \
storage \
utils \
runners \
scratch \
output \
scripts

mkdir -p sources

FILES_TO_REMOVE=(
  index.js
  apis.json
  responses.json
  debug.html
  debug.txt
  output.txt
  hdfc-cards.json
)

for file in "${FILES_TO_REMOVE[@]}"
do
  if [ -f "$file" ]; then
    rm "$file"
    echo "Removed $file"
  fi
done

# ---------------------------------------------------
# CREATE NEW STRUCTURE
# ---------------------------------------------------

mkdir -p \
sources/hdfc \
sources/icici \
sources/axis \
sources/amex \
sources/sbi \
sources/idfc \
sources/au \
sources/yesbank \
sources/scapia \
normalizers \
storage \
utils \
runners \
scripts \
scratch \
output/raw \
output/normalized

# ---------------------------------------------------
# README
# ---------------------------------------------------

cat > README.md <<EOF
# FinanceOS Card Scraper

Scalable multi-bank card ingestion pipeline.

## Run Individual Banks

npm run hdfc
npm run icici
EOF

# ---------------------------------------------------
# GITIGNORE
# ---------------------------------------------------

cat > .gitignore <<EOF
node_modules/
scratch/
output/raw/
.env
.DS_Store
EOF

# ---------------------------------------------------
# PACKAGE.JSON
# ---------------------------------------------------

cat > package.json <<EOF
{
  "name": "financeos-card-scraper",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "hdfc": "node runners/run-hdfc.js",
    "icici": "node runners/run-icici.js"
  },
  "dependencies": {
    "playwright": "^1.55.0",
    "cheerio": "^1.1.2"
  }
}
EOF

# ---------------------------------------------------
# LOGGER
# ---------------------------------------------------

cat > utils/logger.js <<EOF
export function log(
    ...args
) {
    console.log(
        "[FinanceOS]",
        ...args
    );
}

export function error(
    ...args
) {
    console.error(
        "[FinanceOS ERROR]",
        ...args
    );
}
EOF

# ---------------------------------------------------
# JSON UTILS
# ---------------------------------------------------

cat > utils/json.js <<EOF
import fs from "fs";

export function saveJSON(
    path,
    data
) {
    fs.writeFileSync(
        path,
        JSON.stringify(
            data,
            null,
            2
        )
    );
}
EOF

# ---------------------------------------------------
# STORAGE
# ---------------------------------------------------

cat > storage/cardsRepository.js <<EOF
import { saveJSON }
from "../utils/json.js";

export function saveCards(
    path,
    cards
) {
    saveJSON(
        path,
        cards
    );
}
EOF

# ---------------------------------------------------
# NORMALIZER
# ---------------------------------------------------

cat > normalizers/creditCardNormalizer.js <<EOF
const BANK_IMAGE_BASES = {
    HDFC:
        "https://www.hdfcbank.com",

    ICICI:
        "https://www.icici.bank.in"
};

function buildImageURL(
    imagePath,
    bank
) {
    if (!imagePath) {
        return null;
    }

    if (
        imagePath.startsWith(
            "http"
        )
    ) {
        return imagePath;
    }

    const base =
        BANK_IMAGE_BASES[
            bank
        ] ?? "";

    return \`\${base}\${imagePath}\`;
}

export function normalizeCard(
    rawCard,
    bank
) {
    return {
        bank,

        id:
            rawCard.id ??
            rawCard.slug ??
            rawCard.name
                ?.toLowerCase()
                ?.replaceAll(
                    " ",
                    "-"
                ) ??
            null,

        name:
            rawCard.cardTitle ??
            rawCard.name ??
            rawCard.title ??
            null,

        description:
            rawCard.cardDescription ??
            rawCard.description ??
            null,

        image:
            buildImageURL(
                rawCard.cardImage ??
                rawCard.image,
                bank
            ),

        applyLink:
            rawCard.primaryButtonLink ??
            rawCard.applyLink ??
            null,

        detailsLink:
            rawCard.secondaryButtonLink ??
            rawCard.detailsLink ??
            null,

        rewards:
            rawCard.featureList ??
            rawCard.rewards ??
            [],

        benefits:
            rawCard.benefitList ??
            rawCard.benefits ??
            []
    };
}
EOF

# ---------------------------------------------------
# HDFC SCRAPER
# ---------------------------------------------------

cat > sources/hdfc/cards.js <<EOF
import { chromium }
from "playwright";

const PAGE_URL =
    "https://www.hdfcbank.com/personal/pay/cards/credit-cards";

const API_PART =
    "credit-card-listing";

export async function fetchHDFCCards() {
    const browser =
        await chromium.launch({
            headless: true
        });

    const page =
        await browser.newPage({
            userAgent:
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        });

    try {
        console.log(
            "Opening HDFC cards page..."
        );

        let apiResponse =
            null;

        page.on(
            "response",
            async response => {
                try {
                    const url =
                        response.url();

                    if (
                        url.includes(
                            API_PART
                        )
                    ) {
                        apiResponse =
                            await response.json();
                    }
                } catch {}
            }
        );

        await page.goto(
            PAGE_URL,
            {
                waitUntil:
                    "networkidle",
                timeout: 120000
            }
        );

        await page.waitForTimeout(
            5000
        );

        if (
            !apiResponse
        ) {
            throw new Error(
                "Failed to capture HDFC API response"
            );
        }

        return (
            apiResponse.response ??
            []
        );
    } finally {
        await browser.close();
    }
}
EOF

# ---------------------------------------------------
# ICICI SCRAPER
# ---------------------------------------------------

cat > sources/icici/cards.js <<'EOF'
import * as cheerio
from "cheerio";

const PAGE_URL =
    "https://www.icici.bank.in/personal-banking/cards/credit-card";

const INVALID_IMAGE_PATTERNS = [
    "header",
    "logo",
    "banner",
    "icon",
    "newsletter",
    "service",
    "netbanking",
    "imobile",
    "Password.svg",
    "person.png"
];

const INVALID_CARD_NAMES = [
    "cclandingpage",
    "dual cards"
];

const ICICI_NAME_MAPPINGS = {
    sapphiro:
        "Sapphiro Credit Card",

    rubyx:
        "Rubyx Credit Card",

    emeralde:
        "Emeralde Credit Card",

    "emerald metal":
        "Emeralde Metal Credit Card",

    coral:
        "Coral Credit Card",

    "hpcl supersaver":
        "HPCL Super Saver Credit Card",

    "times black":
        "Times Black Credit Card",

    "adani one signature":
        "Adani One Signature Credit Card",

    "mmt signature":
        "MakeMyTrip Signature Credit Card",

    "mmt platinum":
        "MakeMyTrip Platinum Credit Card",

    parakram:
        "Parakram Credit Card",

    "parakram select":
        "Parakram Select Credit Card",

    "emirates sapphiro":
        "Emirates Sapphiro Credit Card",

    "emirates rubyx":
        "Emirates Rubyx Credit Card",

    expressions:
        "Expressions Credit Card",

    "manchester signature":
        "Manchester United Signature Credit Card",

    "manchester platinum":
        "Manchester United Platinum Credit Card",

    csk:
        "CSK Credit Card"
};

function isValidCardImage(
    image
) {
    if (!image) {
        return false;
    }

    const normalized =
        image.toLowerCase();

    if (
        !normalized.includes(
            "card"
        ) &&
        !normalized.includes(
            "cards"
        )
    ) {
        return false;
    }

    const invalid =
        INVALID_IMAGE_PATTERNS.some(
            pattern =>
                normalized.includes(
                    pattern
                )
        );

    return !invalid;
}

function extractRawCardName(
    image
) {
    return image
        .split("/")
        .pop()
        ?.replace(
            /\.webp$/g,
            ""
        )
        ?.replace(
            /\.png$/g,
            ""
        )
        ?.replace(
            /\.jpg$/g,
            ""
        )
        ?.replaceAll(
            "-",
            " "
        )
        ?.replaceAll(
            "_",
            " "
        )
        ?.trim();
}

function cleanICICIName(
    rawName
) {
    if (!rawName) {
        return null;
    }

    let normalized =
        rawName
            .toLowerCase()
            .replace(
                /desktop/g,
                ""
            )
            .replace(
                /desk/g,
                ""
            )
            .replace(
                /card d/g,
                ""
            )
            .replace(
                /crad d/g,
                ""
            )
            .replace(
                /-d$/g,
                ""
            )
            .replace(
                /02/g,
                ""
            )
            .replace(
                /\s+/g,
                " "
            )
            .trim();

    if (
        INVALID_CARD_NAMES.includes(
            normalized
        )
    ) {
        return null;
    }

    for (const [
        key,
        value
    ] of Object.entries(
        ICICI_NAME_MAPPINGS
    )) {
        if (
            normalized.includes(
                key
            )
        ) {
            return value;
        }
    }

    return normalized
        .split(" ")
        .map(
            word =>
                word.charAt(0)
                    .toUpperCase() +
                word.slice(1)
        )
        .join(" ");
}

export async function fetchICICICards() {
    console.log(
        "Fetching ICICI page..."
    );

    const response =
        await fetch(
            PAGE_URL,
            {
                headers: {
                    "User-Agent":
                        "Mozilla/5.0"
                }
            }
        );

    const html =
        await response.text();

    const $ =
        cheerio.load(
            html
        );

    const cards =
        [];

    $("img").each(
        (_, imageElement) => {
            const image =
                $(imageElement).attr(
                    "src"
                );

            if (
                !isValidCardImage(
                    image
                )
            ) {
                return;
            }

            const rawName =
                extractRawCardName(
                    image
                );

            const name =
                cleanICICIName(
                    rawName
                );

            if (
                !name
            ) {
                return;
            }

            const absoluteImage =
                image.startsWith(
                    "http"
                )
                    ? image
                    : `https://www.icici.bank.in${image}`;

            const container =
                $(imageElement)
                    .closest(
                        "section, div, article, li"
                    );

            const description =
                container
                    .text()
                    .replace(
                        /\s+/g,
                        " "
                    )
                    .trim()
                    .slice(
                        0,
                        400
                    );

            cards.push({
                name,

                image:
                    absoluteImage,

                description
            });
        }
    );

    const unique =
        Array.from(
            new Map(
                cards.map(
                    card => [
                        card.name,
                        card
                    ]
                )
            ).values()
        );

    return unique.sort(
        (
            a,
            b
        ) =>
            a.name.localeCompare(
                b.name
            )
    );
}
EOF

# ---------------------------------------------------
# HDFC RUNNER
# ---------------------------------------------------

cat > runners/run-hdfc.js <<EOF
import {
    fetchHDFCCards
} from "../sources/hdfc/cards.js";

import {
    normalizeCard
} from "../normalizers/creditCardNormalizer.js";

import {
    saveCards
} from "../storage/cardsRepository.js";

async function main() {
    const rawCards =
        await fetchHDFCCards();

    const normalized =
        rawCards.map(
            card =>
                normalizeCard(
                    card,
                    "HDFC"
                )
        );

    saveCards(
        "./output/normalized/hdfc_cards.json",
        normalized
    );

    saveCards(
        "./output/raw/hdfc_raw.json",
        rawCards
    );

    console.log(
        "Saved HDFC output"
    );
}

main().catch(
    console.error
);
EOF

# ---------------------------------------------------
# ICICI RUNNER
# ---------------------------------------------------

cat > runners/run-icici.js <<EOF
import {
    fetchICICICards
} from "../sources/icici/cards.js";

import {
    normalizeCard
} from "../normalizers/creditCardNormalizer.js";

import {
    saveCards
} from "../storage/cardsRepository.js";

async function main() {
    const rawCards =
        await fetchICICICards();

    const normalized =
        rawCards.map(
            card =>
                normalizeCard(
                    card,
                    "ICICI"
                )
        );

    saveCards(
        "./output/raw/icici_raw.json",
        rawCards
    );

    saveCards(
        "./output/normalized/icici_cards.json",
        normalized
    );

    console.log(
        "Saved ICICI output"
    );
}

main().catch(
    console.error
);
EOF

# ---------------------------------------------------
# CLEANUP SCRIPT
# ---------------------------------------------------

cat > scripts/cleanup.sh <<EOF
#!/bin/bash

set -e

find scratch -type f -delete || true
find . -name ".DS_Store" -delete

echo "Cleanup complete"
EOF

chmod +x scripts/cleanup.sh

echo ""
echo "======================================"
echo "Rebootstrap Complete"
echo "======================================"
echo ""

echo "Next:"
echo ""
echo "1. npm install"
echo "2. npm run hdfc"
echo "3. npm run icici"
echo ""