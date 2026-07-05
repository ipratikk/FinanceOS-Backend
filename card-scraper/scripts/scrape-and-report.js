#!/usr/bin/env node

import { execSync } from "child_process";
import * as fs from "fs";

console.log("🔄 Running scrapers...\n");

try {
    console.log("→ HDFC scraper...");
    execSync("npm run hdfc", {
        stdio: "inherit"
    });

    console.log("\n→ ICICI scraper...");
    execSync("npm run icici", {
        stdio: "inherit"
    });
} catch (error) {
    console.error(
        "❌ Scraper failed:",
        error.message
    );
    process.exit(1);
}

console.log(
    "\n✓ Scrapers complete\n"
);

// Report outputs
const hdfcRaw = JSON.parse(
    fs.readFileSync(
        "./output/raw/hdfc_raw.json",
        "utf-8"
    )
);

const iciciRaw = JSON.parse(
    fs.readFileSync(
        "./output/raw/icici_raw.json",
        "utf-8"
    )
);

console.log(
    "📊 RAW OUTPUT SUMMARY:"
);
console.log(
    `HDFC: ${hdfcRaw.length} cards`
);
console.log(
    `ICICI: ${iciciRaw.length} cards`
);

// Show sample card
console.log(
    "\n📋 Sample HDFC card:"
);
console.log(
    JSON.stringify(
        hdfcRaw[0],
        null,
        2
    ).slice(0, 300) + "..."
);

console.log(
    "\n📋 Sample ICICI card:"
);
console.log(
    JSON.stringify(
        iciciRaw[0],
        null,
        2
    ).slice(0, 300) + "..."
);

console.log(
    "\n✅ Ready for Claude enrichment"
);
