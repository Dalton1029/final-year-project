from datetime import date, timedelta

from app.engine import analyse_benefit, benefit_value
from app.models import Entitlement, Transaction
from app.legacy_demo import add_transaction, TransactionInput
from app.demo_data import ENTITLEMENTS, TRANSACTIONS


def test_lounge_value_uses_remaining_visits():
    benefit = Entitlement("1", "m", "lounge", "Lounge", 120, 0, date.today() + timedelta(days=10), "annual", visits_allowed=4, visits_used=1)
    assert benefit_value(benefit) == 90


def test_dining_signal_produces_relevant_nudge():
    benefit = Entitlement("1", "m", "dining_credit", "Dining", 25, 0, date.today() + timedelta(days=3), "monthly", ("DoorDash",))
    tx = Transaction("m", "DoorDash", "dining", 30, date.today())
    insight = analyse_benefit(benefit, [tx])
    assert insight["urgency"] == "high"
    assert insight["relevance_score"] >= 90
    assert insight["available_value"] == 25


def test_protection_has_conservative_confidence():
    benefit = Entitlement("1", "m", "protection", "Protection", 80, 0, date.today() + timedelta(days=30), "annual")
    assert analyse_benefit(benefit, [])["confidence"] == "medium"


def test_eligible_transaction_reconciles_a_travel_credit():
    entitlement = next(e for e in ENTITLEMENTS if e.id == "e-1")
    original_used = entitlement.used_value
    result = add_transaction("m-1001", TransactionInput(merchant="Skyline Airlines", category="airfare", amount=10))
    updated = next(e for e in ENTITLEMENTS if e.id == "e-1")
    assert result["reconciled"]["credit_applied"] == 10
    assert updated.used_value == original_used + 10
    ENTITLEMENTS[ENTITLEMENTS.index(updated)] = entitlement
    TRANSACTIONS.pop()
