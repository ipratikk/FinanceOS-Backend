const BANK_IMAGE_BASES = {
    HDFC:
        "https://www.hdfc.bank.in",

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

    return `${base}${imagePath}`;
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
                ?.replaceAll(" ", "-") ??
            null,

        name:
            rawCard.cardTitle ??
            rawCard.name ??
            rawCard.title ??
            null,

        network:
            rawCard.network ?? null,

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
