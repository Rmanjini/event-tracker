// Run: node test_import.mjs   — checks the sheet parser in app.html against rows shaped like the real sheets.
import { readFileSync } from 'fs';
import assert from 'assert';

const html = readFileSync(new URL('./app.html', import.meta.url), 'utf8');
const core = html.match(/<script id="core">([\s\S]*?)<\/script>/)[1];
const app = new Function(core + '; return { S: () => S, setS: x => (S = x), blank, importRows, TEMPLATES, DEFAULT_POST, num, hydrate, duplicateEvent };')();
const c = {};

// Payments ledger tab
app.importRows([
  ['#', 'Name', 'Goal', 'Phone', 'Total paid', 'Form Sent', 'Form Filled', 'Agreement Sent', 'Agreement Filled', 'Added to Whatsapp Group'],
  [1, 'Asha K', 'bakery', 919000000001, 354000, 'Yes', 'Yes', 'No', 'No', 'Yes'],
], 'Fully paid', c);
app.importRows([['#', 'Name', 'Goal', 'Phone', 'Paid so far', 'Notes'], [1, 'Bala R', null, 919000000002, 200000, 'Called, will pay by 7 Dec']], 'Yet to pay', c);
// Side-by-side team blocks with colour titles
app.importRows([
  ['Blue', null, null, null, null, null, 'Red'],
  ['Serial Number', 'Name', 'Phone Number', 'Size', 'Team', null, 'Serial Number', 'Name', 'Phone Number', 'Size', 'Team'],
  [1, 'Asha K', 919000000001, 'xl', 'Team 1', null, 1, 'Bala R', 919000000002, 'M', 'Team 2'],
], 'TEAMS', c);
// Room blocks; crew row without phone shares a name with nobody
app.importRows([
  ['HILL TOP', null, null, null, null, 'JUNGLE LOG'],
  ['Sl.Nos', 'Name', 'Phone Number', 'Room Nos', null, 'Sl.Nos', 'Name', 'Phone Number', 'Room Nos'],
  [1, 'Asha K', 919000000001, 101, null, 2, 'Crew Ravi', null, 201],
], 'Rooms', c);
// Minute-by-minute agenda
app.importRows([
  ['BEFORE THE EVENT'], ['Task', 'Who', 'Ready when'], ['Kit bags ready', 'Team', 'Pen, diary'],
  ['DAY 1, WED 18 NOV'], ['Time', 'What happens', 'Who', 'Things needed'],
  ['3:00 to 3:10 PM', 'Welcome', 'Host', 'Mic, music'], ['7:00 to 9:00 PM', 'Dinner'],
], 'Event Flow', c);

const S = app.S(), asha = S.people.find(p => p.name === 'Asha K'), bala = S.people.find(p => p.name === 'Bala R');
assert.equal(S.people.length, 3);
assert.deepEqual([asha.paid, asha.formFilled, asha.agreementFilled, asha.whatsapp, asha.list], [354000, true, false, true, 'Fully paid']);
assert.deepEqual([asha.team, asha.teamColor, asha.size, asha.room, asha.block], ['Team 1', 'Blue', 'XL', '101', 'HILL TOP']);
assert.deepEqual([bala.list, bala.teamColor, bala.notes], ['Yet to pay', 'Red', 'Called, will pay by 7 Dec']);
assert.deepEqual([asha.paymentDone, bala.paymentDone], [true, false]); // 'Yet to pay' tab = not completed
assert.equal(S.people.find(p => p.name === 'Crew Ravi').block, 'JUNGLE LOG');
assert.deepEqual(S.logistics.map(x => [x.group, x.text, x.who, x.side]), [['BEFORE THE EVENT', 'Kit bags ready', 'Team', 'Organiser']]);
assert.deepEqual(S.agenda.map(s => [s.day, s.what, s.needs.map(n => n.t)]), [['DAY 1, WED 18 NOV', 'Welcome', ['Mic', 'music']], ['DAY 1, WED 18 NOV', 'Dinner', []]]);

// Every downloadable template must import into the right section (example markers stripped, as a user would fill it).
app.setS(app.blank());
for (const t of app.TEMPLATES) for (const [name, rows] of t.sheets)
  app.importRows(rows.map(r => r.map(v => typeof v === 'string' ? v.replace(' (example)', '') : v)), name, {}, t.file);
const T = app.S(), n = k => T[k].length;
assert.deepEqual([n('people'), n('logistics'), n('budget'), n('agenda'), n('meals'), n('incidents'), n('followups'), n('feedback'), n('photos'), n('videos'), n('testimonials'), n('assets'), n('checklist')],
  [2, 4, 2, 3, 2, 1, 2, 2, 1, 1, 1, 1, app.DEFAULT_POST.length + 1]);
assert.deepEqual(T.logistics.map(x => x.side), ['Organiser', 'Organiser', 'Organiser', 'Participant']);
const arun = T.people.find(p => p.name === 'Arun Kumar'), priya = T.people.find(p => p.name === 'Priya Raman');
assert.deepEqual([arun.paid, arun.pending, arun.paymentDone, arun.food, arun.list], [20000, 30000, false, 'Non-veg', 'Early bird']);
assert.deepEqual([priya.formFilled, priya.agreementFilled, priya.medical, priya.emergency, priya.block, priya.room, priya.size], [true, true, 'Peanut allergy', 'Raman K 919800000009', 'Hill Top', '101', 'M']);
assert.deepEqual([T.agenda[0].day, T.agenda[0].needs.length, T.meals[0].veg, T.meals[0].count], ['Day 1', 3, true, 45]);
assert.equal(T.feedback[0].source, 'Google Form'); assert.match(T.feedback[1].text, /photos/);
assert.deepEqual([T.followups[1].reason, T.followups[1].due], ['Balance payment 30,000', '2027-01-25']);
assert.equal(T.incidents[0].what, 'Twisted ankle on trek');
// Example rows left in a template are skipped
app.setS(app.blank());
for (const t of app.TEMPLATES) for (const [name, rows] of t.sheets) app.importRows(rows, name, {}, t.file);
assert.deepEqual([app.S().people.length, app.S().feedback.length, app.S().agenda.length], [0, 0, 0]);
assert.deepEqual([app.num('255000 + PDC 99000'), app.num('₹3,54,000'), app.num('None')], [255000, 354000, null]);
// Event info dates land as YYYY-MM-DD for the calendar picker, whatever the sheet holds
app.setS(app.blank());
app.importRows([['Field', 'Value'], ['Event name', 'TNDS'], ['From (start date)', (Date.UTC(2027, 0, 10) - Date.UTC(1899, 11, 30)) / 864e5], ['End date', '14 Jan 2027'], ['Venue', 'Hall A']], 'Event info', {});
assert.deepEqual([app.S().event, app.S().info.start, app.S().info.end, app.S().info.venue], ['TNDS', '2027-01-10', '2027-01-14', 'Hall A']);
assert.equal(app.hydrate({ info: { dates: '10-14 Jan' } }).info.notes, 'Dates: 10-14 Jan'); // old free-text dates kept, not lost
// Duplicate: keeps structure unticked, drops people/payments/feedback, never touches the source
const src = app.blank(); Object.assign(src, { event: 'Next Level', logo: 'L', info: { venue: 'Resort', start: '2026-11-18', end: '2026-11-22' },
  people: [{ id: 'p', name: 'A', paid: 1 }], feedback: [{ id: 'f' }], logistics: [{ id: 'x', text: 'Mic', done: true, side: 'Organiser' }],
  agenda: [{ id: 'a', what: 'Welcome', status: 'Done', needs: [{ t: 'Mic', done: true }] }] });
const dup = app.duplicateEvent(src, 'Next Level 2', true), empty = app.duplicateEvent(src, 'NL 3', false);
assert.deepEqual([dup.event, dup.logo, dup.info.venue, dup.info.start, dup.people.length, dup.feedback.length], ['Next Level 2', 'L', 'Resort', '', 0, 0]);
assert.deepEqual([dup.logistics[0].text, dup.logistics[0].done, dup.logistics[0].side, dup.agenda[0].status, dup.agenda[0].needs[0].done], ['Mic', false, 'Organiser', 'Upcoming', false]);
assert.deepEqual([src.logistics[0].done, src.agenda[0].needs[0].done, empty.logistics.length, empty.agenda.length], [true, true, 0, 0]);
console.log('import parser + templates OK');
