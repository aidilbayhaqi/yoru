from datetime import UTC, datetime

from yoru_api.modules.partner_copilot.domain import detect_intent, generate_insights, grounded_answer, next_weekly_run, percentage_change


def test_percentage_change_handles_zero_baseline() -> None:
    assert percentage_change(0, 0) is None
    assert percentage_change(10, 0) == 100.0
    assert percentage_change(80, 100) == -20.0


def test_detect_intent_uses_indonesian_terms() -> None:
    assert detect_intent("Kenapa omzet turun?") == "revenue"
    assert detect_intent("Stok mana yang habis?") == "inventory"
    assert detect_intent("Berapa saldo payout?") == "finance"


def test_generate_revenue_drop_insight() -> None:
    insights = generate_insights(
        {"gross_revenue": 50, "bookings_total": 0, "inventory_total": 0, "open_disputes": 0},
        {"gross_revenue": 100},
    )
    assert insights[0].category == "revenue"
    assert insights[0].severity == "critical"


def test_generate_inventory_risk_insight() -> None:
    insights = generate_insights(
        {"gross_revenue": 100, "bookings_total": 0, "inventory_total": 10, "inventory_low_stock": 2, "inventory_out_of_stock": 2, "open_disputes": 0},
        {"gross_revenue": 100},
    )
    assert any(item.category == "inventory" for item in insights)


def test_grounded_answer_contains_snapshot_values() -> None:
    intent, answer, evidence = grounded_answer(
        "Berapa omzet saya?",
        {"gross_revenue": 250000, "net_revenue": 225000, "orders_total": 4, "orders_completed": 3, "average_order_value": 62500, "currency": "IDR"},
        [],
    )
    assert intent == "revenue"
    assert "250000" in answer
    assert evidence["orders_total"] == 4


def test_next_weekly_run_is_future_utc() -> None:
    now = datetime(2026, 8, 1, 4, 0, tzinfo=UTC)
    result = next_weekly_run(now, weekday=0, hour=8, timezone="Asia/Jakarta")
    assert result > now
    assert result.tzinfo is UTC
