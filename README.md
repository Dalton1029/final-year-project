# BenefitLens

A working local card discovery and personal benefit ledger, with React, FastAPI and persistent SQLite storage. The active application starts empty: no sample members, artificial balances or automatic claims of redeemed benefits.

## Run

From `C:\finalyearproj`, run `powershell -ExecutionPolicy Bypass -File .\start.ps1` and open http://127.0.0.1:8090/. Keep the terminal running. The same server serves the built website and API; the old 5176 page is not the new application.

For a fresh setup:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
.\start.ps1
```

To develop React with live updates, run `npm run dev` in `frontend` while the backend runs on 8090. Do not start the old gateway. Port 5173 is strict: an occupied port is reported instead of silently changing the address.

## Working features

- Search/filter six reviewed Indian products from five issuers, expand terms and compare three cards side by side. Official issuer directories link to broader ranges. This is **not an exhaustive market catalogue**.
- A two-step needs questionnaire covers priorities, income, age, fee budget, first-card status, deposit-backed options and category spending. Rankings explain constraints; numeric reward projections are limited to modelled rules. Fit scores are not machine-learning probabilities or approval guarantees. No best-card recommendation is made for someone expecting to carry a balance.
- Account registration/login, salted password hashing, expiring HttpOnly sessions and user-owned data access checks.
- Add catalogue or custom cards, dated entitlement caps and source references. Record transactions manually or import CSV (up to 1,000 rows, 500 KB). Duplicate references reject the entire import, without partially saving it.
- Transaction matches flag possible credits for review; only separately confirmed usage reduces the allowance. Lounges are visits; insurance is coverage, never added to cash savings. Benefits expire according to their supplied period.
- In-app reminders, opt-out, seven-day reviewed/dismissed suppression, usage history, saved recommendation snapshots and benefit-ledger export.

## Where records live

`C:\finalyearproj\data\benefitlens.sqlite3` stores accounts, sessions, wallets, transactions, entitlements, confirmed usage and saved comparisons. Back up this file while the server is stopped. It is excluded from Git. Set `BENEFITLENS_DB` to use a different database (automated tests use isolated temporary databases). No previous in-memory demo history has been migrated. No full card number, CVV or banking password is requested or needed. The local database is not encrypted at rest; protect access to the computer and backups.

CSV columns: `merchant,category,amount,occurred,reference`. Dates are YYYY-MM-DD; use a unique reference per card. Categories: amazon, online, offline, swiggy, airtel, utilities, travel, fuel, rent, insurance, other. Transaction saving is not a bank payment or a bank import connection.

## Catalogue and calculations

`app/catalogue.py` contains source URLs, review date, conditions and explicit modelling limits. Reviewed 10 September 2026. SBI CASHBACK estimates reflect the April 2026 online/offline caps. Amazon estimates distinguish Prime membership. Airtel/Swiggy fee or variable-rule uncertainties and Atlas mileage valuation deliberately prevent numeric savings claims. IDFC FIRST WOW documents the secured-card path. Update and reverify issuer terms before relying on a recommendation; no live issuer feed is connected.

Recurring estimates use the same spending each month, standard fees plus an 18% tax assumption, exclude interest, joining charges, welcome offers and uncertain spend categories, and do not guarantee approval or actual rewards. Users must confirm current offer terms and eligibility with the issuer.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Tests cover restart persistence, account isolation, duplicate CSV rollback, over-cap usage, lounge units, insurance exclusion, reminder suppression and input-dependent recommendations. Four archived engine tests remain as regression checks.

## Project-paper scope and honest boundaries

The active site implements the paper's entitlement/usage mapping, unused-value tracking and explainable contextual reminders with persistent user records. It adds the non-cardholder discovery journey. User-supplied entitlements and confirmed usage are not independently verified by banks. Rule-based recommendations are explicitly labelled; no trained accuracy or uplift result is claimed.

`app/legacy_demo.py`, `frontend/src/legacy-demo.jsx` and other earlier analytics/gateway/integration files are archived or optional scaffolds, not active production integrations. Installing libraries is not a live Tableau, Snowflake, BigQuery, AWS/GCP or bank connection. Those require separately configured accounts, verified feeds and deployment work. A production multi-user internet release also requires HTTPS/secure cookies (`COOKIE_SECURE=1`), recovery and verification flows, operational monitoring, backups, privacy/retention controls and a security review. This delivery is a functioning local application, not a bank-connected or publicly hosted financial service.
