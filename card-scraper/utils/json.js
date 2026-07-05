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
