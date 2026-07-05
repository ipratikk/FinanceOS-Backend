export function log(
    ...args
) {
    console.log(
        "[FinanceOS]",
        ...args
    );
}

export function error(
    ...args
) {
    console.error(
        "[FinanceOS ERROR]",
        ...args
    );
}
