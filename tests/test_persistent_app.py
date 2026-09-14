"""Exercise the real HTTP contract against an isolated on-disk database."""
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import date,timedelta
import pytest

class Client:
    def __init__(self,base):
        self.base=base; self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def call(self,path,body=None,method=None):
        req=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'},method=method)
        try:
            with self.opener.open(req,timeout=10) as r:
                raw=r.read().decode(); return r.status,json.loads(raw) if 'json' in r.headers.get('Content-Type','') else raw
        except urllib.error.HTTPError as e: return e.code,json.loads(e.read())

@pytest.fixture(scope='module')
def server(tmp_path_factory):
    folder=tmp_path_factory.mktemp('benefitlens')
    with socket.socket() as sock: sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    class Server:
        base=f'http://127.0.0.1:{port}'
        def start(self):
            self.proc=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],cwd=Path(__file__).resolve().parents[1],env={**os.environ,'BENEFITLENS_DB':str(folder/'test.sqlite3')},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            for _ in range(100):
                try:
                    if Client(self.base).call('/health')[0]==200:return
                except OSError:pass
                time.sleep(.1)
            raise RuntimeError('Test server did not start')
        def stop(self):self.proc.terminate();self.proc.wait(timeout=10)
    s=Server();s.start();yield s;s.stop()

@pytest.fixture
def client(server):
    c=Client(server.base)
    status,_=c.call('/api/auth/register',{'name':'Test Member','email':secrets.token_hex(8)+'@example.test','password':'Test-only-pass-123'})
    assert status==201
    return c

def wallet(c):
    status,data=c.call('/api/wallet',{'product':'custom','name':'Test card'})
    assert status==201;return data['id']
def benefit(c,w,kind='credit',cap=75):
    status,_=c.call(f'/api/wallet/{w}/benefits',dict(title=kind,kind=kind,cap=cap,start=(date.today()-timedelta(days=10)).isoformat(),end=(date.today()+timedelta(days=5)).isoformat(),category='travel',source='Test issuer terms'))
    assert status==201
    return next(b for b in c.call('/api/dashboard')[1]['benefits'] if b['kind']==kind)['id']
def transaction(ref='tx-001',amount=40):return dict(merchant='Test Airline',category='travel',amount=amount,occurred=date.today().isoformat(),reference=ref)

def test_persistence_and_confirmed_vs_candidate(client,server):
    w=wallet(client);b=benefit(client,w)
    assert client.call(f'/api/wallet/{w}/transactions',transaction())[0]==201
    d=client.call('/api/dashboard')[1]
    assert d['summary']['remaining_credit']==75 and d['benefits'][0]['candidate_credit']==40
    assert client.call(f'/api/benefits/{b}/usage',dict(amount=40,occurred=date.today().isoformat(),evidence='Posted credit ref'))[0]==200
    server.stop();server.start()
    d=client.call('/api/dashboard')[1]
    assert d['summary']['remaining_credit']==35 and len(d['transactions'])==1

def test_account_isolation(client,server):
    w=wallet(client);b=benefit(client,w)
    stranger=Client(server.base)
    assert stranger.call('/api/dashboard')[0]==401
    stranger.call('/api/auth/register',dict(email=secrets.token_hex(8)+'@example.test',password='Another-test-pass'))
    assert stranger.call(f'/api/wallet/{w}/transactions',transaction())[0]==404
    assert stranger.call(f'/api/benefits/{b}/usage',dict(amount=10,occurred=date.today().isoformat(),evidence='Test'))[0]==404
    assert stranger.call('/api/dashboard')[1]['wallets']==[]

def test_duplicate_import_rolls_back(client):
    w=wallet(client)
    client.call(f'/api/wallet/{w}/transactions',transaction())
    text='merchant,category,amount,occurred,reference\nAirline,travel,10,'+date.today().isoformat()+',new-ref\nAirline,travel,10,'+date.today().isoformat()+',tx-001\n'
    assert client.call(f'/api/wallet/{w}/import',{'csv_text':text})[0]==409
    assert len(client.call('/api/dashboard')[1]['transactions'])==1

def test_usage_caps_lounge_and_insurance(client):
    w=wallet(client);b=benefit(client,w,'lounge',2);benefit(client,w,'protection',100000)
    p=dict(amount=1.5,occurred=date.today().isoformat(),evidence='Lounge log')
    assert client.call(f'/api/benefits/{b}/usage',p)[0]==400
    p['amount']=1;assert client.call(f'/api/benefits/{b}/usage',p)[0]==200
    p['amount']=2;assert client.call(f'/api/benefits/{b}/usage',p)[0]==400
    d=client.call('/api/dashboard')[1]
    assert d['summary']['lounge_visits']==1 and d['summary']['remaining_credit']==0

def test_nudge_dismissal_and_optout(client):
    w=wallet(client);b=benefit(client,w)
    assert client.call('/api/dashboard')[1]['nudges']
    client.call(f'/api/nudges/{b}',{'action':'dismissed'})
    assert client.call('/api/dashboard')[1]['nudges']==[]
    client.call('/api/preferences',{'nudges':False},'PUT')
    assert client.call('/api/auth/me')[1]['nudges']==0

def test_recommendations_change_with_needs(client):
    p=dict(age=25,income=50000,max_fee=2000,priorities=['shopping','cashback'],spending={'online':20000},prime=False)
    status,r=client.call('/api/recommendations',p)
    assert status==200 and r['best_id']=='sbi-cashback'
    p.update(priorities=['shopping','no_fee'],spending={'amazon':20000},prime=True,max_fee=0)
    r=client.call('/api/recommendations',p)[1];assert r['best_id']=='amazon-icici'
    p['pay_full']=False;assert client.call('/api/recommendations',p)[1]['best_id'] is None
    p.update(pay_full=True,age=18,income=0,allow_fd=True,fd_budget=20000,priorities=['first_card','no_fee'])
    assert client.call('/api/recommendations',p)[1]['best_id']=='idfc-wow'
    p.update(allow_fd=False,max_fee=0)
    assert client.call('/api/recommendations',p)[1]['best_id'] is None

def test_saved_comparisons_are_private(client,server):
    p=dict(age=25,income=50000,max_fee=2000,priorities=['shopping'],spending={'online':10000})
    assert client.call('/api/recommendations/save',p)[0]==200
    saved=client.call('/api/recommendations/saved')[1]
    assert len(saved)==1 and saved[0]['profile']['spending']=={'online':10000.0}
    stranger=Client(server.base)
    stranger.call('/api/auth/register',dict(email=secrets.token_hex(8)+'@example.test',password='Another-test-pass'))
    assert stranger.call('/api/recommendations/saved')[1]==[]

def test_negative_inputs_and_logout(client):
    w=wallet(client)
    assert client.call(f'/api/wallet/{w}/transactions',transaction(amount=-5))[0]==422
    assert client.call(f'/api/wallet/{w}/transactions',transaction(amount=0.001))[0]==400
    assert client.call(f'/api/wallet/{w}/transactions',{**transaction(),'merchant':'   '})[0]==422
    client.call('/api/auth/logout',{})
    assert client.call('/api/dashboard')[0]==401
