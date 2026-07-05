import { chromium } from "playwright";
import { fetchNetworkFromURL } from "../../utils/networkDetector.js";

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

        if (!apiResponse) {
            throw new Error(
                "Failed to capture HDFC API response"
            );
        }

        const rawCards = apiResponse.response ?? [];

        // API response doesn't include network — fetch from each card's detail page
        const HDFC_BASE = "https://www.hdfc.bank.in";

        for (const card of rawCards) {
            const detailPath =
                card.secondaryButtonLink ??
                card.detailsLink ??
                null;

            if (!detailPath) {
                card.network = null;
                continue;
            }

            const detailUrl = detailPath.startsWith("http")
                ? detailPath
                : `${HDFC_BASE}${detailPath}`;

            card.network = await fetchNetworkFromURL(detailUrl);
        }

        return rawCards;
    } finally {
        await browser.close();
    }
}
