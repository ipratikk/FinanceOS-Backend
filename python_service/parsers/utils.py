from datetime import datetime, timezone, timedelta

# All Indian bank dates are in IST (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))


def parse_amount(s: str) -> int | None:
    """Convert bank amount string to paise (amount × 100). Returns None if unparseable."""
    cleaned = s.strip().replace("₹", "").replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return int(round(float(cleaned) * 100))
    except ValueError:
        return None


def parse_date(s: str, *fmts: str) -> datetime | None:
    """Try each format in order; return first successful parse in IST, or None."""
    stripped = s.strip()
    for fmt in fmts:
        try:
            return datetime.strptime(stripped, fmt).replace(tzinfo=IST)
        except ValueError:
            continue
    return None
