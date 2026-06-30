from collections import defaultdict
from datetime import datetime


def _money(value: int, currency: str = "INR") -> dict:
    return {"value": value, "currencyCode": currency}


def compute_summary(
    rows: list[tuple[datetime, int, str | None]],
) -> dict:
    """
    Compute SpendingSummary from (date, amount_minor_units, category) tuples.
    amount > 0 = debit (spend), amount < 0 = credit (income). All values in minor units.
    """
    total_spend = 0
    total_income = 0
    category_spend: dict[str, int] = defaultdict(int)
    category_count: dict[str, int] = defaultdict(int)
    monthly_spend: dict[str, int] = defaultdict(int)
    monthly_income: dict[str, int] = defaultdict(int)

    for date, amount, category in rows:
        month_key = date.strftime("%Y-%m")
        if amount > 0:
            total_spend += amount
            monthly_spend[month_key] += amount
            cat = category or "Uncategorised"
            category_spend[cat] += amount
            category_count[cat] += 1
        else:
            income = abs(amount)
            total_income += income
            monthly_income[month_key] += income

    all_months = sorted(set(list(monthly_spend.keys()) + list(monthly_income.keys())))

    return {
        "totalSpend": _money(total_spend),
        "totalIncome": _money(total_income),
        "netFlow": _money(total_income - total_spend),
        "byCategory": [
            {"category": cat, "amount": _money(amt), "count": category_count[cat]}
            for cat, amt in sorted(category_spend.items(), key=lambda x: -x[1])
        ],
        "byMonth": [
            {
                "month": m,
                "spend": _money(monthly_spend.get(m, 0)),
                "income": _money(monthly_income.get(m, 0)),
            }
            for m in all_months
        ],
    }


async def fetch_and_compute(
    pool,
    ledger_id: str | None,
    from_date: str | None,
    to_date: str | None,
) -> dict:
    """Fetch transactions from Postgres and compute summary."""
    conditions = []
    args: list = []
    arg_idx = 1

    if ledger_id:
        conditions.append(f'"ledgerId" = ${arg_idx}')
        args.append(ledger_id)
        arg_idx += 1
    if from_date:
        conditions.append(f'"date" >= ${arg_idx}')
        args.append(from_date)
        arg_idx += 1
    if to_date:
        conditions.append(f'"date" <= ${arg_idx}')
        args.append(to_date)
        arg_idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    query = f'SELECT date, "amountMinorUnits", category FROM "Transaction" {where}'

    rows_db = await pool.fetch(query, *args)
    rows = [(r["date"], r["amountMinorUnits"], r["category"]) for r in rows_db]
    return compute_summary(rows)
