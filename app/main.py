"""Persistent local BenefitLens service; no sample accounts or financial records."""
import csv, hashlib, hmac, io, json, os, secrets, sqlite3, time
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field, field_validator
from .catalogue import CARDS, BY_ID, DIRECTORIES, CATEGORIES, REVIEWED, recommend

ROOT=Path(__file__).resolve().parent.parent
class BaseModel(PydanticBaseModel):
    model_config=ConfigDict(str_strip_whitespace=True)
DB_PATH=Path(os.environ.get('BENEFITLENS_DB',ROOT/'data'/'benefitlens.sqlite3'))
@contextmanager
def database():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(DB_PATH,timeout=20); con.row_factory=sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        with con: yield con
    finally: con.close()

def initialize():
    with database() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT,nudges INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),expires REAL);
        CREATE TABLE IF NOT EXISTS wallets(id TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),product TEXT,name TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS benefits(id TEXT PRIMARY KEY,wallet_id TEXT REFERENCES wallets(id),title TEXT,kind TEXT,cap INTEGER,start TEXT,end TEXT,category TEXT,source TEXT);
        CREATE TABLE IF NOT EXISTS transactions(id TEXT PRIMARY KEY,wallet_id TEXT REFERENCES wallets(id),merchant TEXT,category TEXT,amount INTEGER,occurred TEXT,reference TEXT,created TEXT,UNIQUE(wallet_id,reference));
        CREATE TABLE IF NOT EXISTS usage(id TEXT PRIMARY KEY,benefit_id TEXT REFERENCES benefits(id),amount INTEGER,evidence TEXT,occurred TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),benefit_id TEXT,action TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS matches(id TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),profile TEXT,results TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS login_attempts(key TEXT PRIMARY KEY,count INTEGER,first REAL);
        ''')
initialize()
app=FastAPI(title='BenefitLens',version='2.0.0')
@app.middleware('http')
async def security(request:Request,call_next):
    origin=request.headers.get('origin')
    if request.method not in ('GET','HEAD','OPTIONS') and origin and urlparse(origin).netloc!=request.headers.get('host'):
        return Response('Cross-origin writes are not allowed',status_code=403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'; response.headers['Referrer-Policy']='same-origin'; response.headers['X-Frame-Options']='DENY'
    if request.url.path.startswith('/api/'): response.headers['Cache-Control']='no-store'
    return response
def uid(): return secrets.token_hex(16)
def stamp(): return date.today().isoformat()
def pennies(v):
    from decimal import Decimal
    scaled=Decimal(str(v))*100
    if scaled!=scaled.to_integral_value() or scaled<=0: raise HTTPException(400,'Use a positive amount with at most two decimal places')
    return int(scaled)
def password_hash(password,salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+':'+hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
def current_user(request:Request):
    token=hashlib.sha256(request.cookies.get('benefitlens_session','').encode()).hexdigest()
    with database() as db: user=db.execute('SELECT users.* FROM users JOIN sessions ON users.id=sessions.user_id WHERE sessions.token=? AND sessions.expires>?',(token,time.time())).fetchone()
    if not user: raise HTTPException(401,'Sign in to access your saved wallet')
    return dict(user)
def own_wallet(db,wallet_id,user):
    row=db.execute('SELECT * FROM wallets WHERE id=? AND user_id=?',(wallet_id,user['id'])).fetchone()
    if not row: raise HTTPException(404,'Card not found')
    return row

class Credentials(BaseModel):
    name:str=Field(default='Member',min_length=1,max_length=80)
    email:str=Field(min_length=5,max_length=150)
    password:str=Field(min_length=10,max_length=128)
    @field_validator('email')
    @classmethod
    def valid_email(cls,v):
        v=v.strip().lower()
        if '@' not in v or '.' not in v.split('@')[-1]: raise ValueError('Enter a valid email')
        return v
def session_for(db,user,response):
    token=secrets.token_urlsafe(32)
    db.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user['id'],time.time()+604800))
    response.set_cookie('benefitlens_session',token,httponly=True,samesite='strict',max_age=604800,secure=os.getenv('COOKIE_SECURE')=='1')
    return {k:user[k] for k in ('id','name','email','nudges')}
@app.post('/api/auth/register',status_code=201)
def register(p:Credentials,response:Response):
    with database() as db:
        user=dict(id=uid(),name=p.name.strip(),email=p.email,nudges=1)
        try: db.execute('INSERT INTO users(id,name,email,password) VALUES(?,?,?,?)',(user['id'],user['name'],user['email'],password_hash(p.password)))
        except sqlite3.IntegrityError: raise HTTPException(409,'Email already registered; sign in instead')
        return session_for(db,user,response)
@app.post('/api/auth/login')
def login(p:Credentials,response:Response,request:Request):
    key=hashlib.sha256((p.email+(request.client.host if request.client else '')).encode()).hexdigest()
    with database() as db:
        a=db.execute('SELECT * FROM login_attempts WHERE key=?',(key,)).fetchone()
        if a and a['first']>time.time()-900 and a['count']>=10: raise HTTPException(429,'Too many attempts. Try again in 15 minutes.')
        user=db.execute('SELECT * FROM users WHERE email=?',(p.email,)).fetchone()
        valid=user and hmac.compare_digest(password_hash(p.password,user['password'].split(':')[0]),user['password'])
        if valid:
            db.execute('DELETE FROM login_attempts WHERE key=?',(key,)); return session_for(db,user,response)
        if not a or a['first']<time.time()-900: db.execute('INSERT OR REPLACE INTO login_attempts VALUES(?,?,?)',(key,1,time.time()))
        else: db.execute('UPDATE login_attempts SET count=count+1 WHERE key=?',(key,))
    raise HTTPException(401,'Email or password is incorrect')
@app.get('/api/auth/me')
def me(user=Depends(current_user)): return {k:user[k] for k in ('id','name','email','nudges')}
@app.post('/api/auth/logout')
def logout(request:Request,response:Response):
    with database() as db: db.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(request.cookies.get('benefitlens_session','').encode()).hexdigest(),))
    response.delete_cookie('benefitlens_session'); return {'message':'Signed out'}
@app.get('/api/catalogue')
def catalogue(): return dict(country='India',reviewed=REVIEWED,cards=CARDS,directories=DIRECTORIES,coverage='Six reviewed products from five issuers; not an exhaustive market list. Use issuer directories for their complete current ranges.')

class Needs(BaseModel):
    age:int=Field(ge=18,le=100)
    income:float=Field(ge=0,le=10000000,allow_inf_nan=False)
    max_fee:float=Field(ge=0,le=100000,allow_inf_nan=False)
    priorities:list[Literal['shopping','cashback','bills','dining','travel','lounge','first_card','no_fee']]=Field(min_length=1,max_length=8)
    spending:dict[str,float]
    prime:bool=False
    first_card:bool=True
    allow_fd:bool=False
    fd_budget:float=Field(default=0,ge=0,le=10000000,allow_inf_nan=False)
    pay_full:bool=True
    @field_validator('spending')
    @classmethod
    def valid_spending(cls,v):
        import math
        if any(k not in CATEGORIES or not math.isfinite(n) or n<0 or n>1000000 for k,n in v.items()): raise ValueError('Invalid spending category or amount')
        return v
@app.post('/api/recommendations')
def recommendations(p:Needs):
    rows=recommend(p)
    return dict(results=rows,best_id=next((r['card']['id'] for r in rows if not r['blockers'] and r['card']['fee'] is not None and r['score']>0),None) if p.pay_full else None,
      message='Ranked by your priorities and modelled value. Fit score is not approval probability.' if p.pay_full else 'If you expect to carry a balance, interest may outweigh rewards. No best-card recommendation is made; compare borrowing costs first.')
@app.post('/api/recommendations/save')
def save_match(p:Needs,user=Depends(current_user)):
    with database() as db: db.execute('INSERT INTO matches VALUES(?,?,?,?,?)',(uid(),user['id'],p.model_dump_json(),json.dumps(recommendations(p)),stamp()))
    return {'message':'Comparison saved to your account'}
@app.get('/api/recommendations/saved')
def saved(user=Depends(current_user)):
    with database() as db: return [dict(id=r['id'],created=r['created'],profile=json.loads(r['profile']),results=json.loads(r['results'])) for r in db.execute('SELECT * FROM matches WHERE user_id=? ORDER BY rowid DESC LIMIT 20',(user['id'],))]
class WalletInput(BaseModel):
    product:str=Field(max_length=80)
    name:str=Field(default='',max_length=80)
@app.post('/api/wallet',status_code=201)
def add_wallet(p:WalletInput,user=Depends(current_user)):
    if p.product not in BY_ID and p.product!='custom': raise HTTPException(400,'Choose a catalogue product or custom card')
    name=p.name.strip() or (BY_ID[p.product]['name'] if p.product in BY_ID else '')
    if not name: raise HTTPException(400,'Enter a card name')
    with database() as db:
        wallet_id=uid(); db.execute('INSERT INTO wallets VALUES(?,?,?,?,?)',(wallet_id,user['id'],p.product,name,stamp()))
    return {'id':wallet_id,'message':'Card added. Add your exact period entitlements to track benefits.'}
class BenefitInput(BaseModel):
    title:str=Field(min_length=2,max_length=100)
    kind:Literal['credit','lounge','protection']
    cap:float=Field(gt=0,le=10000000,allow_inf_nan=False)
    start:date
    end:date
    category:str=Field(default='other',max_length=40)
    source:str=Field(min_length=3,max_length=500)
@app.post('/api/wallet/{wallet_id}/benefits',status_code=201)
def add_benefit(wallet_id:str,p:BenefitInput,user=Depends(current_user)):
    if p.end<p.start: raise HTTPException(400,'End date must follow start date')
    if p.kind=='lounge' and p.cap!=int(p.cap): raise HTTPException(400,'Lounge allowance must be whole visits')
    if p.category not in CATEGORIES: raise HTTPException(400,'Unknown category')
    with database() as db:
        own_wallet(db,wallet_id,user)
        if db.execute('SELECT id FROM benefits WHERE wallet_id=? AND title=? AND NOT(end<? OR start>?)',(wallet_id,p.title,p.start.isoformat(),p.end.isoformat())).fetchone(): raise HTTPException(409,'Overlapping period for this benefit already exists')
        db.execute('INSERT INTO benefits VALUES(?,?,?,?,?,?,?,?,?)',(uid(),wallet_id,p.title,p.kind,pennies(p.cap),p.start.isoformat(),p.end.isoformat(),p.category,p.source))
    return {'message':'Entitlement saved with your supplied terms'}
class TxInput(BaseModel):
    merchant:str=Field(min_length=2,max_length=100)
    category:Literal['amazon','online','offline','swiggy','airtel','utilities','travel','fuel','rent','insurance','other']
    amount:float=Field(gt=0,le=10000000,allow_inf_nan=False)
    occurred:date
    reference:str=Field(min_length=2,max_length=100)
def insert_tx(db,wallet_id,p):
    if p.occurred>date.today(): raise HTTPException(400,'Transaction cannot be in the future')
    try: db.execute('INSERT INTO transactions VALUES(?,?,?,?,?,?,?,?)',(uid(),wallet_id,p.merchant.strip(),p.category,pennies(p.amount),p.occurred.isoformat(),p.reference.strip(),stamp()))
    except sqlite3.IntegrityError: raise HTTPException(409,'This reference is already recorded for this card')
@app.post('/api/wallet/{wallet_id}/transactions',status_code=201)
def add_tx(wallet_id:str,p:TxInput,user=Depends(current_user)):
    with database() as db: own_wallet(db,wallet_id,user); insert_tx(db,wallet_id,p)
    return {'message':'Transaction saved. Credit opportunities recalculated; confirm posted credits separately.'}
class ImportInput(BaseModel): csv_text:str=Field(min_length=10,max_length=500000)
@app.post('/api/wallet/{wallet_id}/import')
def import_tx(wallet_id:str,p:ImportInput,user=Depends(current_user)):
    reader=csv.DictReader(io.StringIO(p.csv_text.lstrip('\ufeff')))
    if set(reader.fieldnames or [])!={'merchant','category','amount','occurred','reference'}: raise HTTPException(400,'Required columns: merchant,category,amount,occurred,reference')
    rows=[]
    try:
        for i,r in enumerate(reader):
            if i>=1000: raise ValueError('Maximum 1000 transactions per import')
            rows.append(TxInput(**r))
    except Exception as e: raise HTTPException(400,f'Invalid CSV row {len(rows)+2}: {str(e)[:180]}')
    with database() as db:
        own_wallet(db,wallet_id,user)
        for row in rows: insert_tx(db,wallet_id,row)
    return {'message':f'{len(rows)} transactions saved. Duplicate references rejected.'}
class UsageInput(BaseModel):
    amount:float=Field(gt=0,le=10000000,allow_inf_nan=False)
    occurred:date
    evidence:str=Field(min_length=3,max_length=200)
@app.post('/api/benefits/{benefit_id}/usage')
def record_usage(benefit_id:str,p:UsageInput,user=Depends(current_user)):
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        b=db.execute('SELECT b.* FROM benefits b JOIN wallets w ON b.wallet_id=w.id WHERE b.id=? AND w.user_id=?',(benefit_id,user['id'])).fetchone()
        if not b: raise HTTPException(404,'Benefit not found')
        if not b['start']<=p.occurred.isoformat()<=min(b['end'],stamp()): raise HTTPException(400,'Usage must be inside the period and not in the future')
        used=db.execute('SELECT COALESCE(SUM(amount),0) FROM usage WHERE benefit_id=?',(benefit_id,)).fetchone()[0]
        if used+pennies(p.amount)>b['cap']: raise HTTPException(400,'Amount exceeds remaining allowance')
        if b['kind']=='lounge' and p.amount!=int(p.amount): raise HTTPException(400,'Enter whole lounge visits')
        db.execute('INSERT INTO usage VALUES(?,?,?,?,?,?)',(uid(),benefit_id,pennies(p.amount),p.evidence,p.occurred.isoformat(),stamp()))
    return {'message':'Confirmed usage saved; remaining allowance updated'}
@app.get('/api/dashboard')
def dashboard(user=Depends(current_user)):
    with database() as db:
        wallets=[dict(r) for r in db.execute('SELECT * FROM wallets WHERE user_id=? ORDER BY rowid',(user['id'],))]
        benefits=[]; transactions=[]; usage=[]
        for w in wallets:
            tx=[dict(r) for r in db.execute('SELECT * FROM transactions WHERE wallet_id=? ORDER BY occurred DESC,rowid DESC',(w['id'],))]
            for t in tx: t['amount']/=100; t['card_name']=w['name']
            transactions.extend(tx)
            for row in db.execute('SELECT * FROM benefits WHERE wallet_id=? ORDER BY end',(w['id'],)):
                b=dict(row); b['cap']/=100
                records=[dict(r) for r in db.execute('SELECT * FROM usage WHERE benefit_id=? ORDER BY rowid DESC',(b['id'],))]
                for u in records: u['amount']/=100; u['title']=b['title']; usage.append(u)
                b['used']=round(sum(u['amount'] for u in records),2); b['remaining']=round(b['cap']-b['used'],2)
                b['active']=b['start']<=stamp()<=b['end']; b['days_left']=(date.fromisoformat(b['end'])-date.today()).days
                matching=[t for t in tx if t['category']==b['category'] and b['start']<=t['occurred']<=b['end']]
                b['candidate_credit']=round(min(b['remaining'],max(0,sum(t['amount'] for t in matching)-b['used'])),2) if b['kind']=='credit' and b['active'] else 0
                b['card_name']=w['name']; b['signals']=len(matching); benefits.append(b)
        candidates=[]
        if user['nudges']:
            for b in benefits:
                if not b['active'] or b['remaining']<=0 or b['kind']=='protection': continue
                latest=db.execute('SELECT MAX(created) FROM events WHERE user_id=? AND benefit_id=?',(user['id'],b['id'])).fetchone()[0]
                if latest and latest>time.time()-604800: continue
                if b['signals'] or b['days_left']<=14:
                    candidates.append(dict(id=b['id'],title=b['title'],message=f"{b['remaining']:g} {'visits' if b['kind']=='lounge' else 'INR credit'} remaining on {b['card_name']}. "+('Review matching transactions against your terms.' if b['signals'] else 'Your period ends soon.'),days_left=b['days_left'],priority=(100 if b['days_left']<=14 else 0)+min(50,b['signals']*10)))
        candidates.sort(key=lambda n:(-n['priority'],n['days_left']))
        active=[b for b in benefits if b['active']]
        return dict(wallets=wallets,benefits=benefits,transactions=sorted(transactions,key=lambda t:t['occurred'],reverse=True),usage=usage,nudges=candidates[:3],summary=dict(
          remaining_credit=round(sum(b['remaining'] for b in active if b['kind']=='credit'),2),used_credit=round(sum(b['used'] for b in active if b['kind']=='credit'),2),lounge_visits=sum(b['remaining'] for b in active if b['kind']=='lounge'),spend=round(sum(t['amount'] for t in transactions),2)))
class EventInput(BaseModel): action:Literal['reviewed','dismissed']
@app.post('/api/nudges/{benefit_id}')
def event(benefit_id:str,p:EventInput,user=Depends(current_user)):
    with database() as db:
        if not db.execute('SELECT b.id FROM benefits b JOIN wallets w ON w.id=b.wallet_id WHERE b.id=? AND w.user_id=?',(benefit_id,user['id'])).fetchone(): raise HTTPException(404,'Nudge not found')
        db.execute('INSERT INTO events VALUES(?,?,?,?,?)',(uid(),user['id'],benefit_id,p.action,time.time()))
    return {'message':'Reminder suppressed for seven days'}
class Preference(BaseModel): nudges:bool
@app.put('/api/preferences')
def preferences(p:Preference,user=Depends(current_user)):
    with database() as db: db.execute('UPDATE users SET nudges=? WHERE id=?',(int(p.nudges),user['id']))
    return {'message':'Reminder preference saved'}
@app.get('/api/export')
def export(user=Depends(current_user)):
    data=dashboard(user); out=io.StringIO(); writer=csv.writer(out)
    writer.writerow(['card','benefit','kind','cap','used','remaining','start','end','active'])
    for b in data['benefits']:
        safe=lambda s: "'"+s if isinstance(s,str) and s.startswith(('=','+','-','@')) else s
        writer.writerow([safe(b[k]) for k in ['card_name','title','kind','cap','used','remaining','start','end','active']])
    return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=benefitlens-benefits.csv'})
@app.get('/health')
def health(): return {'status':'ok','version':'2.0.0','storage':'sqlite'}
DIST=ROOT/'frontend'/'dist'
if (DIST/'assets').exists(): app.mount('/assets',StaticFiles(directory=DIST/'assets'),name='assets')
@app.get('/',include_in_schema=False)
def index():
    if not (DIST/'index.html').exists(): raise HTTPException(503,'Build the React frontend first')
    return FileResponse(DIST/'index.html',headers={'Cache-Control':'no-cache'})
