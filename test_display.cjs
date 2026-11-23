// Run: node test_display.cjs
// Renders every tab in Event display mode and fails if any payment info shows.
// Uses your private seed.js when present, otherwise the made-up demo snapshot in demo-data/.
const fs = require('fs'), assert = require('assert');
const mem = new Map(); globalThis.localStorage = { getItem: k => mem.get(k) ?? null, setItem: (k, v) => mem.set(k, v), removeItem: k => mem.delete(k) };
const els = {}; globalThis.document = { getElementById: id => els[id] ??= { innerHTML: '', style: {}, classList: { toggle() {} }, addEventListener() {}, set textContent(v) { this.innerHTML = v; } }, addEventListener() {}, querySelectorAll: () => [] };
const seedFile = __dirname + '/seed.js';
globalThis.SEED = fs.existsSync(seedFile) ? new Function(fs.readFileSync(seedFile, 'utf8') + ';return SEED')()
  : JSON.parse(fs.readFileSync(__dirname + '/demo-data/demo-seed.json', 'utf8'));
const h = fs.readFileSync(__dirname + '/app.html', 'utf8');
const app = new Function([...h.matchAll(/<script(?: id="core")?>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n') + ';return { ui, render, S: () => S }')();
const TABS = { pre: ['info', 'onboard', 'people', 'logistics', 'budget', 'rooms'], during: ['sessions', 'food', 'stay', 'health'], post: ['payments', 'followups', 'feedback', 'checklist', 'wrapup'], media: ['photos', 'videos', 'testimonials', 'assets'] };
const BAD = /₹|Collected ₹|Amount collected|Yet to pay|Fully paid|Full ticket|Energy X|354000|Refund|Balance payment|Missing: payment|\(free\)|>Budget<|Vendor settlement/;
assert(app.S().people.length > 20, 'seed loaded');
for (const [ph, subs] of Object.entries(TABS)) for (const sub of subs) {
  Object.assign(app.ui, { phase: ph, reveal: false }); app.ui.sub[ph] = sub; app.render();
  const m = els.app.innerHTML.match(BAD);
  assert(!m, `payment info visible in ${ph} › ${sub}: ${m && els.app.innerHTML.slice(m.index - 60, m.index + 40)}`);
}
Object.assign(app.ui, { phase: 'pre', reveal: false }); app.ui.sub.pre = 'onboard'; app.render();
const n = app.S().people.filter(p => p.role === 'Participant').length;
assert.equal((els.app.innerHTML.match(/class="tickbox"[^>]*aria-label="Payment completed"/g) || []).length, n, 'everyone shows as paid, not editable');
assert(!/data-f="paymentDone"/.test(els.app.innerHTML), 'no payment checkbox to untick on screen');
app.ui.reveal = true; app.render();
assert(/₹/.test(els.app.innerHTML), 'admin view still shows amounts');
console.log('display mode OK: no payment info on any tab, all', n, 'participants shown as paid');
