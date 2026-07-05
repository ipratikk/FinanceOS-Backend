#!/usr/bin/env node

import * as fs from "fs";

const VALID_BENEFITS = [
    "Travel",
    "Dining",
    "Shopping",
    "Lifestyle",
    "Fuel",
    "Entertainment",
    "Insurance",
    "Lounge Access"
];

function normalizeImageUrl(
    imagePath,
    bank
) {
    if (
        !imagePath
    ) {
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
        bank === "HDFC"
            ? "https://www.hdfcbank.com"
            : "https://www.icici.bank.in";

    return `${base}${imagePath}`;
}

function extractRewards(
    card,
    bank
) {
    const rewards = [];

    if (bank === "HDFC") {
        if (
            Array.isArray(
                card.featureList
            )
        ) {
            rewards.push(
                ...card.featureList
                    .filter(
                        f =>
                            f &&
                            f.length > 10
                    )
                    .slice(0, 5)
            );
        }
    } else {
        if (
            Array.isArray(
                card.rewards
            ) &&
            card.rewards.length > 0
        ) {
            rewards.push(
                ...card.rewards.slice(
                    0,
                    5
                )
            );
        }
        // Extract from description as fallback
        if (
            rewards.length === 0 &&
            card.description
        ) {
            const desc =
                card.description;
            const patterns = [
                /(\d+%\s+[^,;.]*)/g,
                /(₹[\d,]+[^,;.]*)/g,
                /([Gg]et\s+[^,;.]{10,})/g
            ];

            for (const pattern of patterns) {
                const matches =
                    desc.match(
                        pattern
                    );
                if (matches) {
                    rewards.push(
                        ...matches
                            .slice(0, 5 - rewards.length)
                    );
                }
                if (
                    rewards.length >= 3
                ) {
                    break;
                }
            }
        }
    }

    return rewards.slice(0, 5);
}

function extractBenefits(
    card,
    bank
) {
    const benefits =
        new Set();

    // Collect benefit data
    let benefitText =
        "";

    if (bank === "HDFC") {
        if (
            Array.isArray(
                card.benefitList
            )
        ) {
            benefitText =
                card.benefitList
                    .join(" ")
                    .toLowerCase();
        }
    } else {
        if (
            Array.isArray(
                card.benefits
            )
        ) {
            benefitText =
                card.benefits
                    .join(" ")
                    .toLowerCase();
        }
        if (
            card.description
        ) {
            benefitText +=
                " " +
                card.description
                    .toLowerCase();
        }
    }

    // Map keywords to categories
    const keywordMap = {
        travel: "Travel",
        flight: "Travel",
        airport: "Lounge Access",
        lounge: "Lounge Access",
        dining: "Dining",
        restaurant: "Dining",
        food: "Dining",
        shopping: "Shopping",
        shop: "Shopping",
        cashback: "Shopping",
        fuel: "Fuel",
        entertainment: "Entertainment",
        movie: "Entertainment",
        insurance: "Insurance",
        lifestyle: "Lifestyle"
    };

    for (const [
        keyword,
        category
    ] of Object.entries(
        keywordMap
    )) {
        if (
            benefitText.includes(
                keyword
            )
        ) {
            benefits.add(
                category
            );
        }
    }

    if (benefits.size === 0) {
        benefits.add(
            "Lifestyle"
        );
    }

    return Array.from(
        benefits
    ).slice(0, 4);
}

function validateCard(card) {
    const required = [
        "name",
        "image",
        "applyLink",
        "detailsLink"
    ];

    for (const field of required) {
        if (!card[field]) {
            return false;
        }
    }

    // Allow empty rewards (might not be extractable from page)
    if (
        !Array.isArray(
            card.rewards
        )
    ) {
        return false;
    }

    // Must have benefits
    if (
        !Array.isArray(
            card.benefits
        ) ||
        card.benefits.length === 0
    ) {
        return false;
    }

    return true;
}

function processBank(
    bank,
    inputFile
) {
    console.log(
        `\nProcessing ${bank}...`
    );

    const raw = JSON.parse(
        fs.readFileSync(
            inputFile,
            "utf-8"
        )
    );

    const processed = [];
    let dropped = 0;

    for (const card of raw) {
        const normalized =
            {
                name:
                    bank ===
                    "HDFC"
                        ? card.cardTitle
                        : card.name,

                description:
                    bank ===
                    "HDFC"
                        ? card.cardDescription ||
                          ""
                        : card.description ||
                          "",

                image:
                    normalizeImageUrl(
                        bank ===
                        "HDFC"
                            ? card.cardImage
                            : card.image,
                        bank
                    ),

                applyLink:
                    bank ===
                    "HDFC"
                        ? card.primaryButtonLink
                        : card.applyLink,

                detailsLink:
                    bank ===
                    "HDFC"
                        ? card.secondaryButtonLink
                        : card.detailsLink,

                rewards:
                    extractRewards(
                        card,
                        bank
                    ),

                benefits:
                    extractBenefits(
                        card,
                        bank
                    )
            };

        if (
            validateCard(
                normalized
            )
        ) {
            processed.push(
                normalized
            );
        } else {
            dropped++;
        }
    }

    console.log(
        `Valid: ${processed.length}, Dropped: ${dropped}`
    );

    return processed;
}

async function main() {
    const outputDir =
        "./output/normalized";

    if (
        !fs.existsSync(
            outputDir
        )
    ) {
        fs.mkdirSync(
            outputDir,
            { recursive: true }
        );
    }

    const hdfcCards =
        processBank(
            "HDFC",
            "./output/raw/hdfc_raw.json"
        );

    const iciciCards =
        processBank(
            "ICICI",
            "./output/raw/icici_raw.json"
        );

    // Save normalized outputs
    fs.writeFileSync(
        `${outputDir}/hdfc_cards.json`,
        JSON.stringify(
            hdfcCards,
            null,
            2
        )
    );

    fs.writeFileSync(
        `${outputDir}/icici_cards.json`,
        JSON.stringify(
            iciciCards,
            null,
            2
        )
    );

    // Combined
    const allCards = [
        ...hdfcCards,
        ...iciciCards
    ];

    fs.writeFileSync(
        `${outputDir}/all_cards.json`,
        JSON.stringify(
            allCards,
            null,
            2
        )
    );

    console.log(
        `\n=== SUMMARY ===`
    );
    console.log(
        `HDFC: ${hdfcCards.length}`
    );
    console.log(
        `ICICI: ${iciciCards.length}`
    );
    console.log(
        `Total: ${allCards.length}`
    );

    console.log(
        `\n✅ Output saved to ${outputDir}`
    );

    // Show sample
    if (
        hdfcCards.length > 0
    ) {
        console.log(
            "\n📋 Sample HDFC:"
        );
        console.log(
            JSON.stringify(
                hdfcCards[0],
                null,
                2
            )
        );
    }

    if (
        iciciCards.length > 0
    ) {
        console.log(
            "\n📋 Sample ICICI:"
        );
        console.log(
            JSON.stringify(
                iciciCards[0],
                null,
                2
            )
        );
    }
}

main().catch(
    console.error
);
