from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .demo_data import ENTITLEMENTS, MEMBERS, TRANSACTIONS
from .engine import member_summary
from .models import Transaction
from .analytics import transaction_features
import csv
import io

app = FastAPI(title="Archived BenefitLens demo", version="0.1.0")
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


class TransactionInput(BaseModel):
    merchant: str = Field(min_length=2, max_length=80)
    category: Literal["dining", "airfare", "electronics", "home", "other"]
    amount: float = Field(gt=0, le=100_000)


class RedemptionInput(BaseModel):
    amount: float = Field(gt=0, le=10_000)


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(static_dir / "index.html")


@app.get("/api/members")
def members():
    return [{"id": m.id, "name": m.name, "card_name": m.card_name} for m in MEMBERS]


@app.get("/api/members/{member_id}/insights")
def insights(member_id: str):
    member = next((m for m in MEMBERS if m.id == member_id), None)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    result = member_summary(member_id, ENTITLEMENTS, TRANSACTIONS)
    result["member"] = {"id": member.id, "name": member.name, "card_name": member.card_name, "annual_fee": member.annual_fee}
    result["analytics_features"] = transaction_features(TRANSACTIONS, member_id)
    return result


@app.get("/api/portfolio/insights")
def portfolio_insights():
    """Issuer-facing aggregate ROI view. Only aggregated figures are returned."""
    summaries = [member_summary(member.id, ENTITLEMENTS, TRANSACTIONS) for member in MEMBERS]
    rows = [benefit for summary in summaries for benefit in summary["benefits"]]
    total_entitled = sum(e.period_value for e in ENTITLEMENTS)
    total_unclaimed = round(sum(row["available_value"] for row in rows), 2)
    by_type = []
    for kind in ("travel_credit", "lounge", "protection"):
        subset = [row for row in rows if row["type"] == kind]
        if subset:
            by_type.append({"benefit_type": kind, "unclaimed_value": round(sum(row["available_value"] for row in subset), 2), "members_affected": sum(1 for row in subset if row["available_value"] > 0), "average_relevance": round(sum(row["relevance_score"] for row in subset) / len(subset), 1)})
    priority_queue = sorted((row for row in rows if row["available_value"] > 0), key=lambda row: row["available_value"] * row["relevance_score"], reverse=True)[:5]
    return {"active_members": len(MEMBERS), "total_entitled_value": round(total_entitled, 2), "total_unclaimed_value": total_unclaimed, "realized_value": round(total_entitled - total_unclaimed, 2), "utilization_rate": round((total_entitled - total_unclaimed) / total_entitled * 100, 1), "by_benefit": by_type, "priority_nudges": priority_queue}


@app.get("/api/entitlement-schema")
def entitlement_schema():
    """Structured product terms used by the entitlement-mapping layer."""
    return [{"member_id": e.member_id, "benefit_type": e.kind, "title": e.title, "maximum_value": e.period_value, "cadence": e.cadence, "expiry": e.expires_on.isoformat(), "eligible_merchants": e.eligible_merchants, "usage_signal": "direct redemption / transaction / partner network"} for e in ENTITLEMENTS]


@app.post("/api/members/{member_id}/transactions", status_code=201)
def add_transaction(member_id: str, payload: TransactionInput):
    if not any(m.id == member_id for m in MEMBERS):
        raise HTTPException(status_code=404, detail="Member not found")
    transaction = Transaction(member_id, payload.merchant.strip(), payload.category, payload.amount, date.today())
    TRANSACTIONS.append(transaction)
    reconciled = None
    # Direct transaction-derived usage is high-confidence for statement credits.
    # Lounge visits and protection claims remain separate partner/claims signals.
    for index, entitlement in enumerate(ENTITLEMENTS):
        if (entitlement.member_id == member_id
                and entitlement.kind in {"dining_credit", "travel_credit"}
                and transaction.merchant in entitlement.eligible_merchants
                and entitlement.expires_on >= date.today()):
            remaining = entitlement.period_value - entitlement.used_value
            credit_applied = round(min(transaction.amount, remaining), 2)
            if credit_applied > 0:
                ENTITLEMENTS[index] = replace(entitlement, used_value=entitlement.used_value + credit_applied)
                reconciled = {"benefit": entitlement.title, "credit_applied": credit_applied}
            break
    message = "Transaction recorded"
    if reconciled:
        message = f"Transaction recorded; ${reconciled['credit_applied']:.2f} applied to {reconciled['benefit']}"
    return {"message": message, "merchant": transaction.merchant, "reconciled": reconciled}


@app.get("/api/members/{member_id}/transactions")
def member_transactions(member_id: str):
    if not any(member.id == member_id for member in MEMBERS):
        raise HTTPException(status_code=404, detail="Member not found")
    rows = [transaction for transaction in TRANSACTIONS if transaction.member_id == member_id]
    rows.sort(key=lambda transaction: transaction.occurred_on, reverse=True)
    return [{"merchant": transaction.merchant, "category": transaction.category, "amount": transaction.amount, "occurred_on": transaction.occurred_on.isoformat()} for transaction in rows]


@app.post("/api/members/{member_id}/benefits/{entitlement_id}/redeem")
def redeem_benefit(member_id: str, entitlement_id: str, payload: RedemptionInput):
    for index, entitlement in enumerate(ENTITLEMENTS):
        if entitlement.id == entitlement_id and entitlement.member_id == member_id:
            remaining = entitlement.period_value - entitlement.used_value
            if payload.amount > remaining:
                raise HTTPException(status_code=400, detail=f"Only ${remaining:.2f} is available for this benefit")
            ENTITLEMENTS[index] = replace(entitlement, used_value=entitlement.used_value + payload.amount)
            return {"message": "Benefit redemption recorded"}
    raise HTTPException(status_code=404, detail="Benefit not found")


@app.get("/api/tableau/export")
def tableau_export():
    """Download a denormalised Tableau-ready benefit opportunity extract."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["member_id", "member_name", "card_name", "benefit_type", "benefit_title", "available_value", "used_value", "relevance_score", "urgency", "days_left", "expires_on", "recommended_action"])
    for member in MEMBERS:
        summary = member_summary(member.id, ENTITLEMENTS, TRANSACTIONS)
        for benefit in summary["benefits"]:
            writer.writerow([member.id, member.name, member.card_name, benefit["type"], benefit["title"], benefit["available_value"], benefit["used_value"], benefit["relevance_score"], benefit["urgency"], benefit["days_left"], benefit["expires_on"], benefit["recommended_action"]])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=benefitlens_tableau_data.csv"})


@app.get("/health")
def health():
    return {"status": "ok"}
