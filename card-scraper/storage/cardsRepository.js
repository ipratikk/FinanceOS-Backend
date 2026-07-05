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
