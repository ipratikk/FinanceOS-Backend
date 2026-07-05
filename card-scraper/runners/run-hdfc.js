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
