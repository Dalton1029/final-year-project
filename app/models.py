from dataclasses import dataclass
from datetime import date
from typing import Literal


BenefitType = Literal["dining_credit", "travel_credit", "lounge", "protection"]


@dataclass(frozen=True)
class Member:
    id: str
    name: str
    card_name: str
    annual_fee: float


@dataclass(frozen=True)
class Entitlement:
    id: str
    member_id: str
    kind: BenefitType
    title: str
    period_value: float
    used_value: float
    expires_on: date
    cadence: str
    eligible_merchants: tuple[str, ...] = ()
    visits_allowed: int = 0
    visits_used: int = 0


@dataclass(frozen=True)
class Transaction:
    member_id: str
    merchant: str
    category: str
    amount: float
    occurred_on: date
