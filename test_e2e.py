# End-to-end test: drives app.html in headless Chrome the way a person would (clicks, typing, uploads, downloads, dialogs).
# Uses only the made-up files in demo-data/ and a throwaway browser profile, so your real data is never touched.
# Needs: pip install playwright openpyxl, and Google Chrome installed.
# Run: python3 test_e2e.py [output_dir]
import json, shutil, struct, sys, tempfile, zlib
from pathlib import Path
from playwright.sync_api import sync_playwright
import openpyxl

HERE = Path(__file__).parent
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix='event-e2e-'))
(OUT / 'shots').mkdir(parents=True, exist_ok=True)
DEMO = sorted((HERE / 'demo-data').glob('DEMO-*.xlsx'))
DOCX = HERE / 'demo-data' / 'DEMO-Things-to-carry.docx'
# Run a copy of the app with an empty seed so the test always starts from a blank event
SITE = OUT / 'site'; SITE.mkdir(exist_ok=True)
shutil.copy(HERE / 'app.html', SITE / 'app.html'); (SITE / 'seed.js').write_text('')
results, errors, dialogs, prompts = [], [], [], []


def png(path, w=900, h=300):  # plain test logo, wider than 400px so the resize path runs
    raw = b''.join(b'\x00' + bytes([91, 14, 20]) * w for _ in range(h))
    ch = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + ch(b'IDAT', zlib.compress(raw)) + ch(b'IEND', b''))


class Step:
    def __init__(self, name): self.name = name
    def __enter__(self): return self
    def __exit__(self, et, ev, tb):
        msg = '' if et is None else f'{et.__name__}: {(str(ev).splitlines() or [""])[0][:220]}'
        results.append((self.name, et is None, msg))
        print(('  PASS  ' if et is None else '  FAIL  ') + self.name + (f'  ->  {msg}' if msg else ''))
        return True  # keep going after a failure


with sync_playwright() as pw:
    browser = pw.chromium.launch(channel='chrome', headless=True)
    ctx = browser.new_context(accept_downloads=True, viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()
    page.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
    page.on('console', lambda m: m.type == 'error' and errors.append(f'console: {m.text}'))
    page.on('dialog', lambda d: (dialogs.append((d.type, d.message[:60])), d.accept(prompts.pop(0) if d.type == 'prompt' and prompts else None)))
    ev = page.evaluate
    app = lambda: page.inner_text('#app')
    toast = lambda t, ms=30000: page.wait_for_function("t => document.getElementById('toast').textContent.includes(t)", arg=t, timeout=ms)
    clear_toast = lambda: ev("document.getElementById('toast').textContent = ''")
    def go(phase, sub=None):
        page.click(f'[data-phase="{phase}"]')
        if sub: page.click(f'[data-sub="{phase}:{sub}"]')
    def manage(act): page.click('details.menu summary:has-text("Manage")'); page.click(f'.pop button[data-act="{act}"]')
    def more(act): page.click('details.menu.right summary'); page.click(f'.pop button[data-act="{act}"]')
    def shot(name): page.screenshot(path=str(OUT / 'shots' / f'{name}.png'))
    def reveal(on):
        if ev('!!ui.reveal') != on: page.click('#reveal')
    def duplicate(name, mode):
        manage('dupevent'); page.wait_for_selector('dialog#dupdlg[open]')
        page.check(f'input[name=dupmode][value={mode}]'); page.fill('#dupname', name); page.click('dialog button[value=ok]')
        page.wait_for_function('n => S.event === n', arg=name)

    page.goto((SITE / 'app.html').as_uri())
    page.wait_for_selector('#app')

    print('\n== Start-up and import ==')
    with Step('Blank app shows the setup card and the header'):
        assert 'Set up New event' in app() and page.inner_text('#reveal') == '🔒 Display mode'
        assert page.locator('.ph').count() == 5 and page.is_hidden('.pop button[data-act="delevent"]')
    with Step('Import the 5 demo sheets: every section fills'):
        page.set_input_files('#file', [str(p) for p in DEMO]); toast('DEMO-Feedback')
        got = ev('["people","agenda","logistics","meals","feedback","followups","assets","testimonials","photos","videos","budget","incidents"].map(k => S[k].length)')
        assert got == [34, 52, 92, 14, 19, 10, 19, 8, 5, 7, 9, 3], got
        assert ev('[S.info.venue, S.info.start, S.info.end]') == ['Wild Planet Resort', '2027-02-17', '2027-02-21']
    with Step('Rename the event from the Manage menu'):
        prompts.append('Demo Event'); manage('rename'); assert 'Demo Event' in page.inner_text('#evsel')
    P = ev("S.people.filter(p => p.role === 'Participant').length")
    shot('01-start')

    print('\n== Display mode (projecting) ==')
    with Step('No payment info on any tab in Display mode'):
        for ph in ['pre', 'during', 'post', 'media']:
            go(ph)
            for sub in page.eval_on_selector_all('nav.sub button[data-sub]', 'b => b.map(x => x.dataset.sub)'):
                page.click(f'[data-sub="{sub}"]'); t = app()
                for bad in ['₹', 'Full ticket', 'Energy X', 'Balance payment', 'Missing: payment']: assert bad not in t, f'{bad!r} visible on {sub}'
        go('pre'); assert not page.is_visible('[data-sub="pre:budget"]'); go('post'); assert not page.is_visible('[data-sub="post:payments"]')
    with Step('Everyone shows Payment completed (solid tick, not editable)'):
        go('pre', 'onboard'); assert page.locator('.onb .tickbox').count() == P and page.locator('input[data-f="paymentDone"]').count() == 0
    with Step('"Payments visible" asks to confirm, shows amounts, turns red; toggles back'):
        n = len(dialogs); page.click('#reveal')
        assert dialogs[n][0] == 'confirm' and '₹' in app() and 'warn' in page.get_attribute('#reveal', 'class')
        page.click('#reveal'); assert '₹' not in app() and page.inner_text('#reveal') == '🔒 Display mode'
    shot('02-display-mode')

    print('\n== Pre-event ==')
    reveal(True)
    with Step('Participant checklist: tick Contact info'):
        go('pre', 'onboard'); pid = ev("S.people.find(p => p.role === 'Participant' && !p.formFilled).id")
        page.click(f'input[data-id="{pid}"][data-f="formFilled"]'); assert ev(f"S.people.find(p => p.id === '{pid}').formFilled") is True
    with Step('Type a pending amount'):
        pid = ev("S.people.find(p => p.pending > 0).id"); sel = f'input[data-id="{pid}"][data-f="pending"]'
        page.fill(sel, '5000'); page.press(sel, 'Tab'); assert ev(f"S.people.find(p => p.id === '{pid}').pending") == 5000
    with Step('Tick Payment completed moves pending into collected'):
        pid = ev("S.people.find(p => p.pending > 5000).id"); paid, pend = ev(f"(p => [p.paid, p.pending])(S.people.find(p => p.id === '{pid}'))")
        page.click(f'input[data-id="{pid}"][data-f="paymentDone"]'); toast('Moved')
        assert ev(f"(p => [p.paid, p.pending])(S.people.find(p => p.id === '{pid}'))") == [paid + pend, 0]
    with Step('Show only pending filter'):
        allrows = page.locator('table.onb tbody tr').count(); page.click('[data-act="pendingonly"]')
        assert 0 < page.locator('table.onb tbody tr').count() < allrows; page.click('[data-act="pendingonly"]')
    with Step('People: search, add, edit, delete'):
        go('pre', 'people'); page.fill('#q', 'Akshaya'); assert page.locator('#app table tbody tr').count() == 1
        page.fill('#q', ''); n = ev('S.people.length'); page.click('[data-add="people"]'); assert ev('S.people.length') == n + 1
        last = ev('S.people.at(-1).id'); sel = f'input[data-id="{last}"][data-f="name"]'; page.fill(sel, 'Test Person'); page.press(sel, 'Tab')
        assert ev('S.people.at(-1).name') == 'Test Person'
        page.click(f'button[data-del="people"][data-id="{last}"]'); assert ev('S.people.length') == n and dialogs[-1][0] == 'confirm'
    with Step('Logistics: Organiser 64 / Participant 28 split'):
        go('pre', 'logistics'); assert '0/64' in page.inner_text('[data-side="Organiser"]') and '0/28' in page.inner_text('[data-side="Participant"]')
    with Step('Logistics: tick item, add group, move a group across and back'):
        first = ev("S.logistics.find(x => x.side === 'Organiser').id"); page.click(f'input[data-id="{first}"][data-f="done"]')
        assert ev(f"S.logistics.find(x => x.id === '{first}').done") is True
        page.click('[data-side="Participant"]'); page.fill('#newgroup', 'Documents to bring'); page.click('[data-act="newgroup"]')
        assert ev('S.logistics.at(-1).side') == 'Participant'
        g = 'Things to be shared in the Call'; page.click(f'button[data-move="{g}"]')
        assert ev(f"S.logistics.filter(x => x.group === '{g}').every(x => x.side === 'Organiser')")
        page.click('[data-side="Organiser"]'); page.click(f'button[data-move="{g}"]')
        assert ev(f"S.logistics.filter(x => x.group === '{g}').every(x => x.side === 'Participant')")
    shot('03-logistics')
    with Step('Budget: add an expense'):
        go('pre', 'budget'); n = ev('S.budget.length'); page.click('[data-add="budget"]'); assert ev('S.budget.length') == n + 1
    with Step('Rooms, teams and T-shirt sizes'):
        go('pre', 'rooms'); t = app(); assert 'Room 101' in t and 'Team 1' in t and 'Hill Top' in t
    with Step('Event info: calendar dates, day count, end date cannot be before start'):
        go('pre', 'info'); page.fill('input[data-info="start"]', '2027-02-18'); assert '4 days' in app()
        assert page.get_attribute('input[data-info="end"]', 'min') == '2027-02-18'
        page.fill('input[data-info="start"]', '2027-02-17'); assert '5 days' in app()
        page.fill('input[data-info="hospital"]', 'Test Hospital 5 km'); page.press('input[data-info="hospital"]', 'Tab'); assert ev('S.info.hospital') == 'Test Hospital 5 km'
    with Step('Save button: typing shows "Not saved yet", Save confirms'):
        page.click('input[data-info="lead"]'); page.keyboard.type(' (on site)')
        assert 'Not saved yet' in page.inner_text('.saved') and 'dirty' in page.get_attribute('.saved', 'class')
        page.click('[data-act="save"]'); toast('Saved'); assert 'All changes saved' in page.inner_text('.saved') and ev('S.info.lead').endswith('(on site)')
    with Step('Rename from the Event name field'):
        page.fill('input[data-evname]', 'Demo Event (renamed)'); page.press('input[data-evname]', 'Tab'); assert 'Demo Event (renamed)' in page.inner_text('#evsel')

    print('\n== During ==')
    with Step('Sessions: 5 day tabs, numbered sessions open as dropdowns'):
        go('during', 'sessions'); assert page.locator('[data-day]').count() == 5
        sid = ev('S.agenda[0].id'); page.click(f'details[data-sid="{sid}"] > summary'); assert page.get_attribute(f'details[data-sid="{sid}"]', 'open') is not None
    with Step('Tick a requirement (dropdown stays open), add one with Enter'):
        page.click(f'input[data-need="{sid}:0"]'); assert ev('S.agenda[0].needs[0].done') is True
        assert page.get_attribute(f'details[data-sid="{sid}"]', 'open') is not None
        n = ev('S.agenda[0].needs.length'); page.fill(f'input[data-addneed="{sid}"]', 'Clicker'); page.press(f'input[data-addneed="{sid}"]', 'Enter')
        assert ev('S.agenda[0].needs.length') == n + 1
    with Step('Half-typed requirement is kept when Save is clicked'):
        page.fill(f'input[data-addneed="{sid}"]', 'Spare batteries'); page.click(f'details[data-sid="{sid}"] [data-act="save"]')
        assert ev('S.agenda[0].needs.at(-1).t') == 'Spare batteries'
    with Step('Every-session checks, Live highlight, Mark session done'):
        page.click(f'input[data-std="{sid}"][data-t="Photos taken"]'); assert ev("S.agenda[0].std['Photos taken']") is True
        page.select_option(f'details[data-sid="{sid}"] select[data-f="status"]', 'Live'); assert 'live' in page.get_attribute(f'details[data-sid="{sid}"]', 'class')
        page.click(f'button[data-sdone="{sid}"]'); assert ev('S.agenda[0].status') == 'Done'
    with Step('Add a session'):
        n = ev('S.agenda.length'); page.click('[data-act="addsession"]'); assert ev('S.agenda.length') == n + 1
    with Step('Quick log: request, testimonial, incident each land in their section'):
        who = ev("S.people.find(p => p.role === 'Participant').name"); before = ev('[S.followups.length, S.testimonials.length, S.incidents.length]')
        page.fill('#rq-p', who); page.fill('#rq-t', 'Wants slides'); page.click('[data-act="logreq"]')
        page.fill('#ts-p', who); page.click('[data-act="logtest"]')
        page.fill('#md-p', who); page.fill('#md-t', 'Headache'); page.click('[data-act="logmed"]')
        assert ev('[S.followups.length, S.testimonials.length, S.incidents.length]') == [x + 1 for x in before]
    shot('04-sessions')
    with Step('Food: meals by day, mark one served, set a food preference'):
        go('during', 'food'); assert 'Buffet' in app()
        mid = ev('S.meals.find(m => !m.served).id'); page.click(f'input[data-id="{mid}"][data-f="served"]'); assert ev(f"S.meals.find(m => m.id === '{mid}').served") is True
        p0 = ev('S.people[0].id'); page.select_option(f'select[data-id="{p0}"][data-f="food"]', 'Jain'); assert ev('S.people[0].food') == 'Jain'
    with Step('Accommodation: check someone in'):
        go('during', 'stay'); p0 = ev('S.people.find(p => !p.checkedIn).id'); page.click(f'input[data-id="{p0}"][data-f="checkedIn"]')
        assert ev(f"S.people.find(p => p.id === '{p0}').checkedIn") is True
    with Step('Medical & safety: change an incident status; emergency contact shown'):
        go('during', 'health'); iid = ev('S.incidents[0].id'); page.select_option(f'select[data-id="{iid}"][data-f="status"]', 'Under care')
        assert ev('S.incidents[0].status') == 'Under care' and page.input_value('input[data-info="hospital"]') == 'Test Hospital 5 km'

    print('\n== Post-event ==')
    with Step('Payments: log a follow-up, set Cleared (syncs Payment completed)'):
        go('post', 'payments'); pid = ev('S.people.find(p => p.pending > 0 && !p.paymentDone).id')
        page.fill(f'input[data-followup="{pid}"]', 'Called, will pay Friday'); page.press(f'input[data-followup="{pid}"]', 'Enter')
        assert ev(f"S.people.find(p => p.id === '{pid}').followups[0].t") == 'Called, will pay Friday'
        page.select_option(f'select[data-id="{pid}"][data-f="payStatus"]', 'Cleared'); assert ev(f"S.people.find(p => p.id === '{pid}').paymentDone") is True
    with Step('Follow-ups: add one; payment follow-ups hidden in Display mode'):
        go('post', 'followups'); n = ev('S.followups.length'); page.click('[data-add="followups"]'); assert ev('S.followups.length') == n + 1
        reveal(False); go('post', 'followups'); assert 'Balance payment' not in app(); reveal(True)
    with Step('Queries & feedback: add one, summary counts, sources listed'):
        go('post', 'feedback'); n = ev('S.feedback.length'); page.click('[data-add="feedback"]'); fid = ev('S.feedback.at(-1).id')
        sel = f'textarea[data-id="{fid}"][data-f="text"]'; page.fill(sel, 'Great event'); page.press(sel, 'Tab')
        t = app(); assert f'Total {n + 1}' in t and 'DEMO-Feedback-Form-Responses.xlsx' in t and ev('S.feedback.at(-1).source') == 'Typed in'
    with Step('Post-production checklist: tick a task'):
        go('post', 'checklist'); cid = ev('S.checklist[0].id'); page.click(f'input[data-id="{cid}"][data-f="done"]'); assert ev('S.checklist[0].done') is True
    with Step('Logistics wrap-up: ready organiser items to pack back'):
        go('post', 'wrapup'); assert page.locator('input[data-f="returned"][data-coll="logistics"]').count() == 1
        page.click('input[data-f="returned"][data-coll="logistics"]'); assert ev('S.logistics.find(x => x.done).returned') is True
    shot('05-post')

    print('\n== Media & assets ==')
    with Step('Photos: batch per day adds no duplicates; tick, add Drive link'):
        go('media', 'photos'); page.click('[data-act="mediabatches"]'); assert ev('S.photos.length') == 5
        links = page.locator('a:has-text("open ↗")').count(); ph = ev('S.photos.find(p => !p.link).id')
        page.click(f'input[data-id="{ph}"][data-f="scaled"]'); sel = f'input[data-id="{ph}"][data-f="link"]'
        page.fill(sel, 'https://drive.google.com/test'); page.press(sel, 'Tab'); page.click(f'input[data-id="{ph}"][data-f="uploaded"]')
        assert page.locator('a:has-text("open ↗")').count() == links + 1
    with Step('Videos list; testimonials summary (taken? how many? edited?)'):
        go('media', 'videos'); assert ev('S.videos.length') == 7, ev('S.videos.map(v => v.label)')
        go('media', 'testimonials'); t = app(); assert 'Taken any? Yes' in t and f"How many? {ev('S.testimonials.length')}" in t
    with Step('Asset register: mark returned'):
        go('media', 'assets'); a = ev('S.assets.find(x => !x.returned).id'); page.click(f'input[data-id="{a}"][data-f="returned"]')
        assert ev(f"S.assets.find(x => x.id === '{a}').returned") is True

    print('\n== Templates ==')
    with Step('Download each template workbook and the all-in-one'):
        go('templates'); want = [['How to use', 'Event info', 'Participants', 'Logistics', 'Budget'], ['How to use', 'Agenda', 'Meals', 'Incidents'],
                                 ['How to use', 'Follow-ups', 'Feedback', 'Post checklist'], ['How to use', 'Photos', 'Videos', 'Testimonials', 'Assets']]
        for i, sheets in enumerate(want + [None]):
            with page.expect_download() as dl: page.click(f'[data-tpl="{i if sheets else "all"}"]')
            path = OUT / dl.value.suggested_filename; dl.value.save_as(path); names = openpyxl.load_workbook(path).sheetnames
            assert names == sheets if sheets else len(names) == 15, (path.name, names)

    print('\n== Backup, reload, persistence ==')
    with Step('Backup downloads the event as JSON'):
        with page.expect_download() as dl: more('export')
        backup = OUT / 'backup.json'; dl.value.save_as(backup); assert len(json.loads(backup.read_text())['people']) == 34
    with Step('Reload keeps every change and reopens in Display mode'):
        page.reload(); page.wait_for_selector('#app .stats')
        assert ev('[S.info.hospital, S.agenda[0].status, S.event]') == ['Test Hospital 5 km', 'Done', 'Demo Event (renamed)']
        assert page.inner_text('#reveal') == '🔒 Display mode'
    with Step('Menus close when clicking elsewhere'):
        page.click('details.menu summary:has-text("Manage")'); assert page.is_visible('.pop button[data-act="addevent"]')
        page.click('#app'); assert page.is_hidden('.pop button[data-act="addevent"]')

    print('\n== Multiple events ==')
    reveal(True); home = ev('index.current')
    with Step('New event from the Manage menu'):
        prompts.append('TNDS'); manage('addevent'); assert ev('S.event') == 'TNDS' and ev('index.events.length') == 2 and 'Set up TNDS' in app()
    with Step('Logo upload: resized to 400px, shown in header and watermark'):
        png(OUT / 'logo.png'); page.set_input_files('#logofile', str(OUT / 'logo.png')); toast('Logo saved')
        assert page.is_visible('#logo') and 'url(' in ev("document.getElementById('wm').style.backgroundImage")
        assert ev('new Promise(r => { const i = new Image(); i.onload = () => r(i.width); i.src = S.logo; })') == 400
    with Step('Word import: bold headings become groups, "SE ..." groups go to Organiser'):
        page.set_input_files('#file', str(DOCX)); toast('DEMO-Things-to-carry.docx')
        assert ev('S.logistics.length') > 80 and ev("S.logistics.some(x => x.group.startsWith('SE things') && x.side === 'Organiser')")
        assert ev("S.logistics.some(x => x.group === 'Things to Carry' && x.side === 'Participant')")
    with Step('Switching events keeps data separate'):
        page.select_option('#evsel', home); assert ev('[S.event, S.people.length, S.logo]') == ['Demo Event (renamed)', 34, '']
    with Step('Duplicate (Empty): new name, no people, venue kept, dates cleared'):
        duplicate('Demo Event · Batch 2', 'empty')
        assert ev('[S.people.length, S.agenda.length, S.info.venue, S.info.start]') == [0, 0, 'Wild Planet Resort', '']
    with Step('Import demo sheets into the duplicate; re-import says "already imported"'):
        page.set_input_files('#file', [str(p) for p in DEMO]); toast('DEMO-Feedback'); assert ev('[S.people.length, S.agenda.length]') == [34, 52]
        clear_toast(); page.set_input_files('#file', [str(p) for p in DEMO]); toast('DEMO-Feedback')
        t = page.inner_text('#toast'); assert ev('S.people.length') == 34 and 'already imported' in t and 'nothing recognised' not in t, t
    with Step('Duplicate (Structure): checklists copied and unticked, no people'):
        page.select_option('#evsel', home); n = ev('S.logistics.length'); duplicate('Structure copy', 'structure')
        assert ev('[S.people.length, S.logistics.length, S.logistics.filter(x => x.done).length, S.agenda.filter(a => a.status !== "Upcoming").length]') == [0, n, 0, 0]
    with Step('Cancel in the duplicate dialog creates nothing'):
        n = ev('index.events.length'); manage('dupevent'); page.click('dialog button[value=cancel]'); page.wait_for_timeout(300); assert ev('index.events.length') == n
    with Step('Delete event asks to confirm'):
        n = ev('index.events.length'); manage('delevent'); assert ev('index.events.length') == n - 1 and dialogs[-1][0] == 'confirm'
    with Step('Reset clears an event but keeps its name'):
        page.select_option('#evsel', home); more('reset'); got = ev('[S.event, S.people.length, ui.phase, index.events.map(e => e.name)]'); assert got[:2] == ['Demo Event (renamed)', 0], got
    with Step('Restore the backup JSON'):
        page.set_input_files('#file', str(OUT / 'backup.json')); toast('backup restored'); assert ev('S.people.length') == 34

    print('\n== Layout ==')
    with Step('Phone width: header wraps, no sideways scrolling'):
        page.set_viewport_size({'width': 390, 'height': 844}); go('pre', 'onboard')
        assert ev('document.documentElement.scrollWidth') <= 392; shot('06-phone'); page.set_viewport_size({'width': 1440, 'height': 900})
    with Step('No JavaScript errors during the whole run'):
        assert not errors, errors[:5]
    browser.close()

ok = sum(r[1] for r in results)
print(f'\n{ok}/{len(results)} checks passed · screenshots and downloads in {OUT}')
for n, good, msg in results:
    if not good: print('  FAILED:', n, '->', msg)
sys.exit(0 if ok == len(results) else 1)
