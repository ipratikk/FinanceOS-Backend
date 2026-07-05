import * as cheerio from "cheerio";
import { detectNetworkFromHTML } from "../../utils/networkDetector.js";

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
    "dual cards",
    "credit builder",
    "against fixed",
    "call service",
    "branches",
    "rewards",
    "fuel",
    "culinary",
    "personal loan",
    "pre approved"
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

async function fetchCardDetails(
    cardDetailUrl,
    cardName
) {
    try {
        const response =
            await fetch(
                cardDetailUrl,
                {
                    headers: {
                        "User-Agent":
                            "Mozilla/5.0"
                    }
                }
            );

        if (
            !response.ok
        ) {
            return {
                description:
                    "",
                image: null,
                rewards: [],
                benefits: [],
                applyLink:
                    null,
                detailsLink:
                    cardDetailUrl
            };
        }

        const html =
            await response.text();

        const $ =
            cheerio.load(
                html
            );

        let description =
            $('meta[property="og:description"]')
                .attr("content") ||
            "";

        if (
            description
        ) {
            description =
                description
                    .slice(0, 400);
        }

        // Extract card image from detail page
        let cardImage =
            null;

        const imgSelectors = [
            'img[src*="/cards/"][src*="-banner"]',
            'img[src*="/cards/"][src*="-desktop"]',
            'img[src*="/cards/"][src*="-desk-"]'
        ];

        for (const selector of imgSelectors) {
            const imgElement =
                $(selector).first();

            if (
                imgElement &&
                imgElement.length
            ) {
                let imageSrc =
                    imgElement.attr(
                        "src"
                    );

                if (imageSrc) {
                    cardImage =
                        imageSrc.startsWith(
                            "http"
                        )
                            ? imageSrc
                            : `https://www.icici.bank.in${imageSrc}`;
                    break;
                }
            }
        }

        const rewards =
            [];

        $(
            ".icon__benefit img[src*='reward'], " +
            ".icon__benefit img[src*='points']"
        )
            .closest(".icon__benefit")
            .find("p").each(
                (_, elem) => {
                    const text =
                        $(elem)
                            .text()
                            .trim()
                            .replace(
                                /\n/g,
                                " "
                            )
                            .replace(
                                /\s+/g,
                                " "
                            );

                    if (
                        text &&
                        text.length > 15
                    ) {
                        rewards.push(
                            text
                        );
                    }
                }
            );

        const benefits =
            [];

        $(
            ".benefits__lt .dis__badge p, " +
            ".product-maximum-benefits .dis__badge p"
        ).each(
            (_, elem) => {
                const text =
                    $(elem)
                        .text()
                        .trim();

                if (
                    text &&
                    benefits.length < 5
                ) {
                    benefits.push(
                        text
                    );
                }
            }
        );

        const applyLink =
            $('a[href*="buy.icici.bank"]')
                .first()
                .attr("href") || null;

        const network = detectNetworkFromHTML($);

        return {
            description,

            image:
                cardImage,

            rewards:
                rewards.slice(0, 5),

            benefits:
                benefits.slice(0, 5),

            applyLink,

            network,

            detailsLink:
                cardDetailUrl
        };
    } catch (error) {
        return {
            description:
                "",
            rewards: [],
            benefits: [],
            applyLink:
                null,
            detailsLink:
                cardDetailUrl
        };
    }
}

const CARD_PAGE_KEYWORDS = [
    "credit-card",
    "rupay",
    "signature",
    "platinum",
    "coral",
    "sapphiro",
    "rubyx",
    "emeralde",
    "hpcl",
    "adani",
    "manchester",
    "mmt",
    "makemytrip",
    "emirates",
    "expressions",
    "parakram",
    "times-black",
    "csk"
];

function isCardProductPage(
    url
) {
    const lower =
        url.toLowerCase();

    const hasCardKeyword =
        CARD_PAGE_KEYWORDS.some(
            keyword =>
                lower.includes(
                    keyword
                )
        );

    const isNotServicePage =
        !lower.includes(
            "faq"
        ) &&
        !lower.includes(
            "cancel"
        ) &&
        !lower.includes(
            "pin"
        ) &&
        !lower.includes(
            "limit"
        ) &&
        !lower.includes(
            "emi"
        ) &&
        !lower.includes(
            "terms"
        ) &&
        !lower.includes(
            "benefits-and-features"
        ) &&
        !lower.includes(
            "experience"
        ) &&
        !lower.includes(
            "generate"
        ) &&
        !lower.includes(
            "calculator"
        );

    return hasCardKeyword &&
        isNotServicePage;
}

function fuzzyMatch(
    str1,
    str2
) {
    const a =
        str1
            .toLowerCase()
            .replace(/\W/g, "");
    const b =
        str2
            .toLowerCase()
            .replace(/\W/g, "");

    return (
        a.includes(b) ||
        b.includes(a) ||
        a === b
    );
}

export async function fetchICICICards() {
    console.log(
        "Fetching ICICI listing page..."
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

    // Extract card URLs and images from listing
    const cardUrls =
        new Set();

    $('a[href*="/personal-banking/cards/credit-card/"]')
        .each(
            (_, elem) => {
                const href =
                    $(elem).attr(
                        "href"
                    );

                if (
                    href &&
                    isCardProductPage(
                        href
                    )
                ) {
                    cardUrls.add(
                        href
                    );
                }
            }
        );

    console.log(
        `Found ${cardUrls.size} card product pages`
    );

    // Extract images from listing
    const listingImages =
        {};

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
                !name ||
                listingImages[name]
            ) {
                return;
            }

            const absoluteImage =
                image.startsWith(
                    "http"
                )
                    ? image
                    : `https://www.icici.bank.in${image}`;

            listingImages[name] =
                absoluteImage;
        }
    );

    console.log(
        `Extracted ${Object.keys(listingImages).length} card images`
    );

    // Fetch details and metadata for each card
    const cards =
        [];

    for (const url of cardUrls) {
        const fullUrl =
            url.startsWith(
                "http"
            )
                ? url
                : `https://www.icici.bank.in${url}`;

        console.log(
            `Fetching: ${fullUrl}`
        );

        const details =
            await fetchCardDetails(
                fullUrl
            );

        if (
            !details.applyLink
        ) {
            continue;
        }

        // Extract name from URL
        const urlParts =
            url.split("/");

        const slug =
            urlParts[
                urlParts.length - 1
            ];

        const rawName =
            slug
                .replace(
                    /-/g,
                    " "
                )
                .trim();

        const name =
            cleanICICIName(
                rawName
            );

        if (
            !name
        ) {
            continue;
        }

        // Skip invalid card names
        const nameLower =
            name.toLowerCase();

        if (
            INVALID_CARD_NAMES.some(
                invalid =>
                    nameLower.includes(
                        invalid
                    )
            )
        ) {
            continue;
        }

        // Prefer detail page image, fallback to listing images
        let image =
            details.image;

        if (
            !image
        ) {
            image =
                listingImages[name];
        }

        if (
            !image
        ) {
            for (const [
                imgName,
                imgUrl
            ] of Object.entries(
                listingImages
            )) {
                if (
                    fuzzyMatch(
                        name,
                        imgName
                    )
                ) {
                    image =
                        imgUrl;
                    break;
                }
            }
        }

        cards.push({
            name,

            image,

            network:
                details.network ?? null,

            description:
                details.description,

            rewards:
                details.rewards,

            benefits:
                details.benefits,

            applyLink:
                details.applyLink,

            detailsLink:
                details.detailsLink
        });
    }

    // Deduplicate by name
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
