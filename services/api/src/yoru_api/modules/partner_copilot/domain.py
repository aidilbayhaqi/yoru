from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class GeneratedInsight:
    category: str
    severity: str
    title: str
    summary: str
    recommendation: str
    evidence: dict[str, Any]


def percentage_change(current: int | float, previous: int | float) -> float | None:
    if previous == 0:
        return None if current == 0 else 100.0
    return round(((current - previous) / abs(previous)) * 100, 2)


def ratio_percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def detect_intent(question: str) -> str:
    normalized = question.casefold()
    intent_terms = {
        "revenue": ("revenue", "omzet", "pendapatan", "penjualan", "uang masuk"),
        "booking": ("booking", "pesanan jasa", "jadwal", "cancel", "batal"),
        "inventory": ("stok", "inventory", "persediaan", "habis", "reorder"),
        "finance": ("saldo", "payout", "refund", "dispute", "komisi", "settlement"),
        "operations": ("operasional", "completion", "no show", "kinerja", "performa"),
    }
    for intent, terms in intent_terms.items():
        if any(term in normalized for term in terms):
            return intent
    return "overview"


def generate_insights(current: dict[str, Any], previous: dict[str, Any]) -> list[GeneratedInsight]:
    insights: list[GeneratedInsight] = []
    revenue_change = percentage_change(current.get("gross_revenue", 0), previous.get("gross_revenue", 0))
    if revenue_change is not None and revenue_change <= -20:
        severity = "critical" if revenue_change <= -40 else "warning"
        insights.append(GeneratedInsight(
            category="revenue",
            severity=severity,
            title=f"Revenue turun {abs(revenue_change):.1f}%",
            summary="Pendapatan periode ini lebih rendah dibanding periode pembanding.",
            recommendation="Periksa produk terlaris, availability layanan, dan sumber pembatalan sebelum menambah promosi.",
            evidence={"current": current.get("gross_revenue", 0), "previous": previous.get("gross_revenue", 0), "change_percent": revenue_change},
        ))
    elif revenue_change is not None and revenue_change >= 20:
        insights.append(GeneratedInsight(
            category="revenue", severity="info", title=f"Revenue tumbuh {revenue_change:.1f}%",
            summary="Pendapatan meningkat dibanding periode pembanding.",
            recommendation="Pertahankan availability dan stok pada item yang menyumbang pertumbuhan.",
            evidence={"current": current.get("gross_revenue", 0), "previous": previous.get("gross_revenue", 0), "change_percent": revenue_change},
        ))

    bookings = int(current.get("bookings_total", 0))
    booking_cancelled = int(current.get("bookings_cancelled", 0)) + int(current.get("bookings_no_show", 0))
    cancellation_rate = ratio_percent(booking_cancelled, bookings)
    if cancellation_rate >= 20:
        insights.append(GeneratedInsight(
            category="booking", severity="critical" if cancellation_rate >= 40 else "warning",
            title=f"Risiko pembatalan booking {cancellation_rate:.1f}%",
            summary="Proporsi booking cancelled dan no-show berada di atas ambang operasional.",
            recommendation="Audit lead time, reminder, jam layanan, dan alasan pembatalan sebelum membuka slot tambahan.",
            evidence={"total": bookings, "cancelled_or_no_show": booking_cancelled, "rate_percent": cancellation_rate},
        ))

    inventory_total = int(current.get("inventory_total", 0))
    low_stock = int(current.get("inventory_low_stock", 0))
    out_of_stock = int(current.get("inventory_out_of_stock", 0))
    if low_stock or out_of_stock:
        risk_rate = ratio_percent(low_stock + out_of_stock, inventory_total)
        insights.append(GeneratedInsight(
            category="inventory", severity="critical" if out_of_stock > 0 and risk_rate >= 30 else "warning",
            title=f"{low_stock + out_of_stock} item berisiko stok",
            summary="Ada item pada atau di bawah reorder level, termasuk stok kosong.",
            recommendation="Prioritaskan replenishment item kosong dan naikkan safety stock untuk item yang sering terjual.",
            evidence={"total_items": inventory_total, "low_stock": low_stock, "out_of_stock": out_of_stock, "risk_percent": risk_rate},
        ))

    open_disputes = int(current.get("open_disputes", 0))
    if open_disputes:
        insights.append(GeneratedInsight(
            category="finance", severity="warning", title=f"{open_disputes} dispute masih terbuka",
            summary="Dispute terbuka dapat menahan saldo partner dan memperlambat payout.",
            recommendation="Lengkapi evidence dan selesaikan kasus dengan nilai terbesar lebih dulu.",
            evidence={"open_disputes": open_disputes, "held_amount": current.get("held_amount", 0)},
        ))

    if not insights:
        insights.append(GeneratedInsight(
            category="operations", severity="info", title="Tidak ada anomali utama",
            summary="Metrik utama masih berada dalam ambang yang dipantau oleh Copilot lokal.",
            recommendation="Pertahankan availability, kualitas fulfillment, dan disiplin pembaruan stok.",
            evidence={"period_start": current.get("period_start"), "period_end": current.get("period_end")},
        ))
    return insights[:8]


def grounded_answer(question: str, metrics: dict[str, Any], insights: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
    intent = detect_intent(question)
    evidence: dict[str, Any]
    if intent == "revenue":
        evidence = {k: metrics.get(k, 0) for k in ("gross_revenue", "net_revenue", "orders_total", "orders_completed", "average_order_value")}
        answer = (
            f"Revenue kotor periode ini {evidence['gross_revenue']} {metrics.get('currency', 'IDR')} "
            f"dari {evidence['orders_total']} order; {evidence['orders_completed']} selesai. "
            "Nilai ini berasal dari snapshot transaksi Yoru, bukan estimasi pasar."
        )
    elif intent == "booking":
        evidence = {k: metrics.get(k, 0) for k in ("bookings_total", "bookings_completed", "bookings_cancelled", "bookings_no_show")}
        answer = (
            f"Terdapat {evidence['bookings_total']} booking: {evidence['bookings_completed']} selesai, "
            f"{evidence['bookings_cancelled']} dibatalkan, dan {evidence['bookings_no_show']} no-show."
        )
    elif intent == "inventory":
        evidence = {k: metrics.get(k, 0) for k in ("inventory_total", "inventory_low_stock", "inventory_out_of_stock")}
        answer = (
            f"Dari {evidence['inventory_total']} item stok, {evidence['inventory_low_stock']} berada pada reorder level "
            f"dan {evidence['inventory_out_of_stock']} kosong."
        )
    elif intent == "finance":
        evidence = {k: metrics.get(k, 0) for k in ("net_revenue", "commission_amount", "refund_amount", "held_amount", "open_disputes")}
        answer = (
            f"Net revenue tercatat {evidence['net_revenue']} {metrics.get('currency', 'IDR')}, komisi "
            f"{evidence['commission_amount']}, refund {evidence['refund_amount']}, dan saldo tertahan {evidence['held_amount']}."
        )
    else:
        evidence = {k: metrics.get(k, 0) for k in ("gross_revenue", "orders_total", "bookings_total", "inventory_low_stock", "open_disputes")}
        top = insights[0]["title"] if insights else "Tidak ada insight aktif"
        answer = (
            f"Ringkasan partner: revenue {evidence['gross_revenue']} {metrics.get('currency', 'IDR')}, "
            f"{evidence['orders_total']} order, {evidence['bookings_total']} booking. Insight utama: {top}."
        )
    return intent, answer, evidence


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def next_weekly_run(now: datetime, *, weekday: int, hour: int, timezone: str) -> datetime:
    zone = ZoneInfo(timezone)
    local = now.astimezone(zone)
    days = (weekday - local.weekday()) % 7
    candidate = (local + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)
    if candidate <= local:
        candidate += timedelta(days=7)
    return candidate.astimezone(UTC)
