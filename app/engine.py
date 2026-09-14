from dataclasses import asdict
from datetime import date
from typing import Iterable

from .models import Entitlement, Transaction


def _round(value: float) -> float:
    return round(max(value, 0), 2)


def benefit_value(entitlement: Entitlement) -> float:
    """Return the dollar value still available for one entitlement."""
    if entitlement.kind == "lounge" and entitlement.visits_allowed:
        value_per_visit = entitlement.period_value / entitlement.visits_allowed
        return _round((entitlement.visits_allowed - entitlement.visits_used) * value_per_visit)
    return _round(entitlement.period_value - entitlement.used_value)


def _signals(entitlement: Entitlement, transactions: Iterable[Transaction]) -> list[str]:
    signals = []
    for tx in transactions:
        if entitlement.kind in {"dining_credit", "travel_credit"} and tx.merchant in entitlement.eligible_merchants:
            signals.append(f"Spent ${tx.amount:.0f} at {tx.merchant} {((date.today() - tx.occurred_on).days)} days ago")
        elif entitlement.kind == "lounge" and tx.category == "airfare":
            signals.append(f"Booked airfare (${tx.amount:.0f}) {((date.today() - tx.occurred_on).days)} days ago")
        elif entitlement.kind == "protection" and tx.category in {"electronics", "home"}:
            signals.append(f"Bought an eligible {tx.category} item (${tx.amount:.0f})")
    return signals


def analyse_benefit(entitlement: Entitlement, transactions: Iterable[Transaction]) -> dict:
    available = benefit_value(entitlement)
    days_left = (entitlement.expires_on - date.today()).days
    signals = _signals(entitlement, transactions)
    urgency = "high" if days_left <= 10 else "medium" if days_left <= 45 else "low"
    relevance = min(95, 45 + (25 if signals else 0) + (20 if urgency == "high" else 8 if urgency == "medium" else 0))
    action = {
        "dining_credit": "Use it on your next eligible food order.",
        "travel_credit": "Apply it to an eligible flight or hotel booking.",
        "lounge": "Add lounge access to your next airport itinerary.",
        "protection": "Review eligible recent purchases and activate coverage if needed.",
    }[entitlement.kind]
    return {
        "id": entitlement.id, "type": entitlement.kind, "title": entitlement.title,
        "available_value": available, "used_value": entitlement.used_value,
        "expires_on": entitlement.expires_on.isoformat(), "days_left": days_left,
        "urgency": urgency, "relevance_score": relevance, "signals": signals,
        "recommended_action": action,
        "confidence": "high" if entitlement.kind in {"travel_credit", "lounge"} else "medium",
    }


def member_summary(member_id: str, entitlements: Iterable[Entitlement], transactions: Iterable[Transaction]) -> dict:
    items = [analyse_benefit(e, transactions) for e in entitlements if e.member_id == member_id]
    items.sort(key=lambda x: (x["available_value"] * x["relevance_score"]), reverse=True)
    return {
        "member_id": member_id,
        "unclaimed_value": _round(sum(item["available_value"] for item in items)),
        "benefits": items,
        "top_nudge": items[0] if items else None,
    }
