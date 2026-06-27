import pytest
from datetime import datetime, timezone, timedelta
from analytics.spending import compute_summary

IST = timezone(timedelta(hours=5, minutes=30))

SAMPLE_ROWS = [
    # (date, amount_rupees, category)  positive=debit/spend, negative=credit/income
    (datetime(2026, 1, 15, tzinfo=IST), 500.0, "Food"),
    (datetime(2026, 1, 20, tzinfo=IST), 1200.0, "Shopping"),
    (datetime(2026, 2, 5, tzinfo=IST), -50000.0, None),    # salary credit
    (datetime(2026, 2, 10, tzinfo=IST), 300.0, "Food"),
    (datetime(2026, 2, 15, tzinfo=IST), 800.0, "Shopping"),
]


def test_total_spend():
    summary = compute_summary(SAMPLE_ROWS)
    assert summary["totalSpend"] == pytest.approx(2800.0)


def test_total_income():
    summary = compute_summary(SAMPLE_ROWS)
    assert summary["totalIncome"] == pytest.approx(50000.0)


def test_net_flow():
    summary = compute_summary(SAMPLE_ROWS)
    assert summary["netFlow"] == pytest.approx(50000.0 - 2800.0)


def test_by_category():
    summary = compute_summary(SAMPLE_ROWS)
    cats = {c["category"]: c for c in summary["byCategory"]}
    assert cats["Food"]["amount"] == pytest.approx(800.0)
    assert cats["Food"]["count"] == 2
    assert cats["Shopping"]["amount"] == pytest.approx(2000.0)


def test_by_month():
    summary = compute_summary(SAMPLE_ROWS)
    months = {m["month"]: m for m in summary["byMonth"]}
    assert "2026-01" in months
    assert "2026-02" in months
    assert months["2026-01"]["spend"] == pytest.approx(1700.0)
    assert months["2026-02"]["income"] == pytest.approx(50000.0)
