// Archived demo interface. Not served by the current application.
import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import '@tableau/embedding-api';
import './styles.css';

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });

function IssuerDashboard({ portfolio }) {
  if (!portfolio) return <section className="issuer"><p>Loading portfolio metrics...</p></section>;
  return <section className="issuer"><div className="issuer-intro"><div><small>ISSUER PORTFOLIO ROI</small><h2>Unrealized benefit value</h2><p>Aggregated, privacy-preserving performance across the active portfolio.</p></div><span>Statement-cycle view</span></div><div className="issuer-kpis"><article><small>ACTIVE MEMBERS</small><b>{portfolio.active_members}</b></article><article><small>TOTAL ENTITLED</small><b>{money.format(portfolio.total_entitled_value)}</b></article><article><small>UNCLAIMED VALUE</small><b>{money.format(portfolio.total_unclaimed_value)}</b></article><article><small>UTILIZATION</small><b>{portfolio.utilization_rate}%</b></article></div><div className="issuer-grid"><article><h3>Unclaimed value by benefit</h3>{portfolio.by_benefit.map(row => <div className="bar" key={row.benefit_type}><span>{row.benefit_type.replace('_', ' ')}</span><i><b style={{width: `${row.unclaimed_value / portfolio.total_unclaimed_value * 100}%`}} /></i><strong>{money.format(row.unclaimed_value)}</strong><small>{row.members_affected} members affected</small></div>)}</article><article><h3>Priority nudge queue</h3>{portfolio.priority_nudges.map(row => <div className="queue" key={row.id}><span>{row.title}</span><b>{money.format(row.available_value)}</b><small>{row.relevance_score}/100 relevance · {row.confidence} confidence</small></div>)}</article></div></section>;
}

function App() {
  const [members, setMembers] = useState([]);
  const [memberId, setMemberId] = useState('');
  const [insight, setInsight] = useState(null);
  const [form, setForm] = useState({ merchant: '', category: 'dining', amount: '' });
  const [notice, setNotice] = useState('');
  const [view, setView] = useState('member');
  const [portfolio, setPortfolio] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const tableauUrl = import.meta.env.VITE_TABLEAU_VIEW_URL;

  const load = async (id) => { const [memberInsight, history] = await Promise.all([fetch(`/api/members/${id}/insights`).then(r => r.json()), fetch(`/api/members/${id}/transactions`).then(r => r.json())]); setInsight(memberInsight); setTransactions(history); };
  useEffect(() => { fetch('/api/members').then(r => r.json()).then(data => { setMembers(data); setMemberId(data[0].id); load(data[0].id); }); }, []);
  useEffect(() => { fetch('/api/portfolio/insights').then(r => r.json()).then(setPortfolio); }, []);
  const addTransaction = async (event) => {
    event.preventDefault();
    const response = await fetch(`/api/members/${memberId}/transactions`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...form, amount: Number(form.amount) }) });
    const result = await response.json();
    setNotice(response.ok ? result.message : 'Could not save transaction.');
    if (response.ok) { setForm({ merchant: '', category: 'dining', amount: '' }); load(memberId); }
  };
  const redeem = async (benefit) => {
    const amount = window.prompt(`Amount used (up to ${money.format(benefit.available_value)})`);
    if (!amount) return;
    const response = await fetch(`/api/members/${memberId}/benefits/${benefit.id}/redeem`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ amount: Number(amount) }) });
    setNotice(response.ok ? 'Benefit redemption saved.' : 'Redemption could not be saved.');
    if (response.ok) load(memberId);
  };
  if (!insight) return <main>Loading BenefitLens...</main>;
  const top = insight.top_nudge;
  const features = insight.analytics_features;
  return <main className="app">
    <nav><b>BenefitLens</b><div className="view-toggle"><button className={view === 'member' ? 'selected' : ''} onClick={() => setView('member')}>Cardholder view</button><button className={view === 'issuer' ? 'selected' : ''} onClick={() => setView('issuer')}>Issuer portfolio</button></div></nav>
    <header><div><small>MEMBER VALUE INTELLIGENCE</small><h1>Benefits should<br /><i>feel valuable.</i></h1></div><select value={memberId} onChange={e => { setMemberId(e.target.value); load(e.target.value); }}>{members.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}</select></header>
    {view === 'issuer' ? <IssuerDashboard portfolio={portfolio} /> : <><section className="hero"><article><small>UNCLAIMED VALUE</small><strong>{money.format(insight.unclaimed_value)}</strong><p>of {money.format(insight.member.annual_fee)} annual fee</p></article><article className="nudge"><small>NEXT BEST NUDGE</small><h2>{top.title}</h2><p>{top.recommended_action}</p>{top.signals.map(s => <em key={s}>{s}</em>)}</article></section>
    <section className="live-stack"><div><span>●</span><small>FASTAPI + PANDAS</small><b>{features.transaction_count}</b><p>transactions analysed</p></div><div><span>●</span><small>NUMPY FEATURES</small><b>{money.format(features.average_spend)}</b><p>average member spend</p></div><div><span>●</span><small>ML READINESS</small><b>{features.category_diversity}</b><p>behaviour categories</p></div><div className="tableau-status"><small>TABLEAU EMBEDDED</small><b>{tableauUrl ? 'Connected' : 'Ready'}</b><p>{tableauUrl ? 'Live dashboard linked' : 'Add view URL in .env'}</p><a href="/api/tableau/export">Download Tableau CSV</a></div></section>
    <h2>Opportunity queue</h2><section className="cards">{insight.benefits.map(b => <article key={b.id}><span className={b.urgency}>{b.urgency} urgency</span><h3>{b.title}</h3><p>{b.type.replace('_', ' ')} · relevance {b.relevance_score}/100</p><strong>{money.format(b.available_value)}</strong><small> still available · expires in {b.days_left} days</small><button disabled={!b.available_value} onClick={() => redeem(b)}>Mark redeemed</button></article>)}</section>
    <section className="form"><div><small>LIVE DATA INPUT</small><h2>Record a transaction</h2><p>Transactions pass through Node.js, FastAPI, and pandas/NumPy analytics before the nudge ranking refreshes.</p></div><form onSubmit={addTransaction}><input required placeholder="Merchant" value={form.merchant} onChange={e => setForm({ ...form, merchant: e.target.value })} /><select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}><option value="dining">Dining</option><option value="airfare">Airfare</option><option value="electronics">Electronics</option><option value="home">Home</option><option value="other">Other</option></select><input required min="1" type="number" placeholder="Amount" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} /><button>Save transaction</button><small>{notice}</small></form></section><section className="history"><div><small>FASTAPI TRANSACTION LEDGER</small><h2>Recorded transactions</h2></div><div className="history-table"><div className="history-head"><span>Date</span><span>Merchant</span><span>Category</span><span>Amount</span></div>{transactions.map((transaction, index) => <div className="history-row" key={`${transaction.merchant}-${index}`}><span>{transaction.occurred_on}</span><span>{transaction.merchant}</span><span>{transaction.category}</span><b>{money.format(transaction.amount)}</b></div>)}</div></section>
    {tableauUrl && <section className="tableau"><small>TABLEAU ANALYTICS</small><tableau-viz src={tableauUrl} toolbar="bottom" hide-tabs="true" /></section>}</>}
  </main>;
}
createRoot(document.getElementById('root')).render(<App />);
