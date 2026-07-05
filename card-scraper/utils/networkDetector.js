/**
 * Detects the card payment network from a bank detail page.
 * Checks: image src/alt attributes, then full body text.
 * Returns one of: "Visa" | "Mastercard" | "RuPay" | "Amex" | "Diners" | null
 */

import * as cheerio from "cheerio";

const NETWORK_PATTERNS = [
    // Order matters — check more specific patterns first
    { pattern: /diners/i,             value: "Diners" },
    { pattern: /rupay/i,              value: "RuPay" },
    { pattern: /amex|american.express/i, value: "Amex" },
    { pattern: /mastercard/i,         value: "Mastercard" },
    { pattern: /visa/i,               value: "Visa" },
];

/**
 * Detect network from already-loaded cheerio HTML.
 * Pass $ from cheerio.load(html).
 */
export function detectNetworkFromHTML($) {
    // 1. Check image src and alt attributes (most reliable — logos are explicit)
    let found = null;

    $("img").each((_, el) => {
        if (found) return false;
        const src = ($(el).attr("src") || "").toLowerCase();
        const alt = ($(el).attr("alt") || "").toLowerCase();
        for (const { pattern, value } of NETWORK_PATTERNS) {
            if (pattern.test(src) || pattern.test(alt)) {
                found = value;
                return false;
            }
        }
    });

    if (found) return found;

    // 2. Check text nodes in known network-mention areas
    const targetSelectors = [
        ".card-network",
        ".network-type",
        '[class*="network"]',
        '[class*="visa"]',
        '[class*="mastercard"]',
        '[class*="rupay"]',
        ".card-type",
        ".card__type",
        ".card-variant",
        "h1",
        "h2",
        ".card-title",
    ];

    for (const sel of targetSelectors) {
        const text = $(sel).text();
        for (const { pattern, value } of NETWORK_PATTERNS) {
            if (pattern.test(text)) {
                return value;
            }
        }
    }

    // 3. Last resort — full body text (noisy, may false-positive on page links)
    const bodyText = $("body").text();
    for (const { pattern, value } of NETWORK_PATTERNS) {
        if (pattern.test(bodyText)) {
            return value;
        }
    }

    return null;
}

/**
 * Fetch a card detail URL and extract the payment network.
 * Returns null on fetch error or if network cannot be determined.
 */
export async function fetchNetworkFromURL(detailUrl) {
    try {
        const response = await fetch(detailUrl, {
            headers: { "User-Agent": "Mozilla/5.0" },
            signal: AbortSignal.timeout(15000),
        });

        if (!response.ok) return null;

        const html = await response.text();
        const $ = cheerio.load(html);
        return detectNetworkFromHTML($);
    } catch {
        return null;
    }
}
