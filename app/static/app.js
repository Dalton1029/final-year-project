const money = new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', maximumFractionDigits: 0});
const typeText = {dining_credit: 'Dining', lounge: 'Travel', protection: 'Protection'};
const select = document.querySelector('#member');

async function loadMembers() {
  const members = await fetch('/api/members').then(r => r.json());
  select.innerHTML = members.map(m => `<option value="${m.id}">${m.name}</option>`).join('');
  select.addEventListener('change', () => loadInsights(select.value));
  loadInsights(members[0].id);
}

async function loadInsights(id) {
  const data = await fetch(`/api/members/${id}/insights`).then(r => r.json());
  document.querySelector('#total').textContent = money.format(data.unclaimed_value);
  document.querySelector('#fee-note').textContent = `${money.format(data.unclaimed_value)} of ${money.format(data.member.annual_fee)} annual fee can be recovered`;
  document.querySelector('#value-bar').style.width = `${Math.min(100, data.unclaimed_value / data.member.annual_fee * 100)}%`;
  const top = data.top_nudge;
  document.querySelector('#nudge-title').textContent = `${top.title} is ready to use`;
  document.querySelector('#nudge-message').textContent = top.recommended_action;
  document.querySelector('#signals').innerHTML = top.signals.length ? top.signals.map(s => `<span>${s}</span>`).join('') : '<span>No recent signal — value and expiry ranked this benefit.</span>';
  document.querySelector('#count').textContent = `${data.benefits.length} benefits`;
  const template = document.querySelector('#benefit-template');
  const grid = document.querySelector('#benefits');
  grid.innerHTML = '';
  data.benefits.forEach(b => {
    const card = template.content.cloneNode(true);
    card.querySelector('h3').textContent = b.title;
    card.querySelector('.description').textContent = `${typeText[b.type]} benefit • relevance score ${b.relevance_score}`;
    card.querySelector('.money strong').textContent = money.format(b.available_value);
    const urgency = card.querySelector('.urgency');
    urgency.textContent = `${b.urgency} urgency`;
    urgency.classList.add(b.urgency);
    card.querySelector('.meter b').style.width = `${Math.min(100, b.relevance_score)}%`;
    card.querySelector('.expiry').textContent = `Expires in ${b.days_left} days`;
    const redeem = card.querySelector('.redeem');
    if (!b.available_value) { redeem.textContent = 'Fully used'; redeem.disabled = true; }
    else redeem.addEventListener('click', () => redeemBenefit(data.member.id, b));
    grid.appendChild(card);
  });
}

async function redeemBenefit(memberId, benefit) {
  const amount = prompt(`How much of ${benefit.title} did the member use? (Maximum ${money.format(benefit.available_value)})`);
  if (!amount) return;
  const response = await fetch(`/api/members/${memberId}/benefits/${benefit.id}/redeem`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({amount: Number(amount)})});
  if (!response.ok) { alert((await response.json()).detail); return; }
  loadInsights(memberId);
}

document.querySelector('#transaction-form').addEventListener('submit', async event => {
  event.preventDefault();
  const status = document.querySelector('#form-status');
  const response = await fetch(`/api/members/${select.value}/transactions`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({merchant: document.querySelector('#merchant').value, category: document.querySelector('#category').value, amount: Number(document.querySelector('#amount').value)})});
  if (!response.ok) { status.textContent = 'Could not record transaction.'; return; }
  status.textContent = 'Recorded — recommendations refreshed.';
  event.target.reset();
  loadInsights(select.value);
});

loadMembers();
