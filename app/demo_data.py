from datetime import date, timedelta

from .models import Entitlement, Member, Transaction

TODAY = date.today()
MONTH_END = TODAY + timedelta(days=8)

MEMBERS = [
    Member("m-1001", "Maya Patel", "Apex Reserve", 550),
    Member("m-1002", "Arjun Mehta", "Apex Reserve", 550),
    Member("m-1003", "Sara Khan", "Apex Gold", 250),
]

ENTITLEMENTS = [
    Entitlement("e-1", "m-1001", "travel_credit", "$75 quarterly travel credit", 75, 40, TODAY + timedelta(days=35), "quarterly", ("Skyline Airlines", "Urban Hotel")),
    Entitlement("e-2", "m-1001", "lounge", "Airport lounge visits", 180, 45, TODAY + timedelta(days=130), "annual", visits_allowed=4, visits_used=1),
    Entitlement("e-3", "m-1001", "protection", "Purchase protection", 120, 0, TODAY + timedelta(days=130), "annual"),
    Entitlement("e-4", "m-1002", "travel_credit", "$75 quarterly travel credit", 75, 0, TODAY + timedelta(days=45), "quarterly", ("Skyline Airlines", "Urban Hotel")),
    Entitlement("e-5", "m-1002", "lounge", "Airport lounge visits", 180, 0, TODAY + timedelta(days=45), "annual", visits_allowed=4, visits_used=0),
    Entitlement("e-6", "m-1002", "protection", "Purchase protection", 120, 0, TODAY + timedelta(days=45), "annual"),
    Entitlement("e-7", "m-1003", "travel_credit", "$30 quarterly travel credit", 30, 0, TODAY + timedelta(days=28), "quarterly", ("Skyline Airlines",)),
    Entitlement("e-8", "m-1003", "lounge", "Airport lounge visits", 70, 70, TODAY + timedelta(days=90), "annual", visits_allowed=2, visits_used=2),
    Entitlement("e-9", "m-1003", "protection", "Purchase protection", 60, 0, TODAY + timedelta(days=90), "annual"),
]

TRANSACTIONS = [
    Transaction("m-1001", "Uber Eats", "dining", 32.80, TODAY - timedelta(days=2)),
    Transaction("m-1001", "Skyline Airlines", "airfare", 415.00, TODAY - timedelta(days=6)),
    Transaction("m-1001", "TechTown", "electronics", 284.99, TODAY - timedelta(days=11)),
    Transaction("m-1002", "Skyline Airlines", "airfare", 640.00, TODAY - timedelta(days=3)),
    Transaction("m-1002", "World Market", "home", 160.00, TODAY - timedelta(days=12)),
    Transaction("m-1003", "DoorDash", "dining", 23.40, TODAY - timedelta(days=1)),
    Transaction("m-1003", "PhoneHub", "electronics", 89.00, TODAY - timedelta(days=9)),
]
