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
