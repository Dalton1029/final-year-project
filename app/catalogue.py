"""Versioned, source-linked Indian product catalogue. No live market completeness claim."""
REVIEWED = '2026-09-10'
CARDS = [
    dict(id='amazon-icici', name='Amazon Pay ICICI', bank='ICICI Bank', fee=0, joining=0, tags=['shopping','cashback','no_fee'], color='#24363d',
         benefits=['Amazon purchases: 5% for Prime members, 3% otherwise, subject to eligible categories.', '2% at eligible Amazon Pay partner merchants; 1% on other eligible spends.', 'Rewards arrive as Amazon Pay balance; no joining or annual fee.', '1.99% forex markup and 1% fuel surcharge waiver, subject to terms.'],
         conditions='Invite-only. Published minimum age 21 and monthly income ₹30,000. Approval remains with ICICI. Exclusions and transaction-level rounding apply.',
         source='https://www.icici.bank.in/personal-banking/cards/credit-card/amazon-pay-credit-card', min_age=21, min_income=30000, secured=False, model='amazon'),
    dict(id='sbi-cashback', name='CASHBACK SBI Card', bank='SBI Card', fee=999, joining=999, tags=['shopping','cashback'], color='#373472',
         benefits=['5% cashback on eligible online spends and 1% on eligible offline spends.', 'From April 2026: separate ₹2,000 online and ₹2,000 offline caps per statement cycle.', 'Joining and renewal fee ₹999 plus taxes; renewal waiver depends on qualifying annual spend.'],
         conditions='Excludes utilities, insurance, fuel, rent, wallets, education, jewellery, railway, gaming, tolls, government and EMI transactions. Check issuer terms for the complete MCC list and fee waiver.',
         source='https://www.sbicard.com/en/personal/credit-cards/cashback-sbi-card.html', terms='https://www.sbicard.com/sbi-card-en/assets/docs/pdf/cashback-revised.pdf', min_age=21, min_income=None, secured=False, model='sbi'),
    dict(id='airtel-axis', name='Airtel Axis Bank', bank='Axis Bank', fee=None, joining=None, tags=['bills','cashback'], color='#87363d',
         benefits=['25% on eligible Airtel payments via Airtel Thanks; monthly cap linked to twice the base cashback.', '10% on eligible utility payments via Airtel Thanks; cap linked to base cashback.', '1% base cashback on other eligible spends; selected partner value-back offers.'],
         conditions='Terms revised during 2026, including August. Benefits depend on base spends, channel, MCC and partner conditions. Fee and complete eligibility require issuer verification; excluded from numeric savings rankings.',
         source='https://www.axis.bank.in/cards/credit-card/airtel-axis-bank-credit-card', min_age=None, min_income=None, secured=False, model=None),
    dict(id='swiggy-hdfc', name='Swiggy HDFC Bank', bank='HDFC Bank', fee=None, joining=None, tags=['dining','shopping'], color='#ab562a',
         benefits=['Issuer product page lists cashback on Swiggy and eligible online categories.', 'Published product page includes a Swiggy One introductory membership.', 'Benefits differ by Swiggy variant and offer; check the exact variant before applying.'],
         conditions='Classic, newer variants and offer-specific terms must not be mixed. Fee, rates, order thresholds and caps require variant verification. Excluded from numeric savings rankings until verified.',
         source='https://www.hdfc.bank.in/credit-cards/swiggy-hdfc-bank-credit-card', min_age=None, min_income=None, secured=False, model=None),
    dict(id='axis-atlas', name='Axis Bank ATLAS', bank='Axis Bank', fee=5000, joining=None, tags=['travel','lounge'], color='#315653',
         benefits=['Travel-focused EDGE Miles programme with tier and milestone benefits.', 'Annual benefits depend on tier and annual-fee payment.', 'Airport lounge entitlements and transfer/redemption options depend on current product terms.'],
         conditions='₹5,000 annual fee plus GST. Miles are not treated as guaranteed cash savings here. Excluded categories and tier requirements apply; verify current lounge and reward rules.',
         source='https://www.axis.bank.in/cards/credit-card/axis-bank-atlas-credit-card', min_age=None, min_income=None, secured=False, model=None),
    dict(id='idfc-wow', name='IDFC FIRST WOW!', bank='IDFC FIRST Bank', fee=0, joining=0, tags=['first_card','no_fee','travel'], color='#6e3b52',
         benefits=['Fixed-deposit-backed card; no income proof or prior credit history required under published criteria.', 'Zero forex markup and lifetime-free standard WOW! variant.', 'Published minimum resident FD ₹20,000; credit limit linked to deposit.'],
         conditions='Resident age 18–80 and bank KYC apply. FD is held as security, not an annual fee. WOW! Black is a separate variant. No cash reward estimate is modelled.',
         source='https://www.idfcfirst.bank.in/credit-card/wow', min_age=18, min_income=0, secured=True, model=None),
]
DIRECTORIES = [
    {'bank':'SBI Card','url':'https://www.sbicard.com/en/personal/sbi-credit-card.page'},
    {'bank':'ICICI Bank','url':'https://www.icicibank.com/personal-banking/cards/credit-card'},
    {'bank':'HDFC Bank','url':'https://www.hdfc.bank.in/ps/credit-cards-in-india'},
    {'bank':'Axis Bank','url':'https://www.axis.bank.in/cards/credit-card'},
    {'bank':'IDFC FIRST Bank','url':'https://www.idfcfirstbank.com/credit-card'},
]
BY_ID = {c['id']: c for c in CARDS}
CATEGORIES = ['amazon','online','offline','swiggy','airtel','utilities','travel','fuel','rent','insurance','other']

def estimate(card, spending, prime=False):
    """Annual projection, stable monthly spending; buckets are mutually exclusive."""
    s = lambda k: spending.get(k, 0)
    if card['model'] == 'amazon':
        parts = {'Eligible Amazon': s('amazon') * (.05 if prime else .03),
                 'Other eligible spending': sum(s(k) for k in ['online','offline','swiggy','travel']) * .01}
    elif card['model'] == 'sbi':
        parts = {'Eligible online (capped)': min(2000, sum(s(k) for k in ['amazon','online','swiggy']) * .05),
                 'Eligible offline (capped)': min(2000, s('offline') * .01)}
    else:
        return None
    gross = round(sum(parts.values()) * 12, 2)
    fee = round(card['fee'] * 1.18, 2)
    return {'gross': gross, 'fee_with_tax': fee, 'net': round(gross - fee, 2),
            'breakdown': {k: round(v * 12, 2) for k, v in parts.items()},
            'assumptions': 'Recurring-year projection: 12 similar statement cycles, fee plus 18% GST. No welcome offers, fee waivers, interest, repayment charges or unmodelled categories. Assumes eligible purchases and full on-time repayment; actual statement rounding may differ.'}

def recommend(profile):
    results = []
    for card in CARDS:
        reasons, blockers = [], []
        if profile.age < (card['min_age'] or 18): blockers.append('Below published or baseline adult age requirement')
        if card['secured'] and (not profile.allow_fd or profile.fd_budget < 20000): blockers.append('Requires a fixed deposit of at least ₹20,000')
        if card['id'] == 'idfc-wow' and profile.age > 80: blockers.append('Above published maximum age')
        if card['min_income'] and profile.income < card['min_income']: blockers.append('Below published monthly income requirement')
        if card['fee'] is not None and card['fee'] * 1.18 > profile.max_fee: blockers.append('Annual fee including tax exceeds your budget')
        overlap = set(card['tags']) & set(profile.priorities)
        reasons.extend('Matches your ' + x.replace('_', ' ') + ' priority' for x in sorted(overlap))
        projection = estimate(card, profile.spending, profile.prime)
        score = len(overlap) * 20
        if projection: score += max(-20, min(40, projection['net'] / 500))
        if card['secured'] and profile.first_card: score += 20; reasons.append('FD-backed route supports first-time applicants')
        if card['fee'] == 0: reasons.append('No recurring card fee for this variant')
        if card['fee'] is None: reasons.append('Fee requires verification before deciding')
        if not reasons: reasons.append('Alternative product; limited match to selected priorities')
        results.append(dict(card=card, score=round(max(0, min(100, score)),1), reasons=reasons,
                            blockers=blockers, projection=projection,
                            eligibility='Does not meet supplied constraints' if blockers else 'Potential fit; bank eligibility and approval still required'))
    return sorted(results, key=lambda r:(not r['blockers'], r['score']), reverse=True)
