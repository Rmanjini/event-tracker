# Event Tracker

One page to run an event from planning to wrap up. I built it for our immersion retreats, where the team was juggling a payments ledger, a room sheet, a minute by minute agenda and a Word checklist. Now it all lives in one place and every step has a tick box.

It is a single HTML file. No server, no login, no install. Open `app.html` in Chrome and start.

## What it tracks

**Pre-event**
- Event info: venue, dates (calendar), food service, check in and out, nearest hospital, venue contact
- Participant checklist: contact info collected, payment completed, agreement signed, amount collected and pending
- People: role, team, room, T-shirt size, food preference, medical notes, emergency contact
- Logistics in two lists: Organiser (what the team sets up and carries) and Participant (what people bring)
- Budget: estimated vs actual, paid out
- Rooms, teams and T-shirt size counts

**During the event**
- Session checklist: each day's sessions numbered and opening like a dropdown, with the requirements to tick and a "mark session done" button
- Food: meal timings, buffet, veg and non-veg, menu, headcount, served
- Accommodation: check in and check out
- Medical and safety: incident log and each person's medical info
- Quick log for requests, testimonials and incidents as they happen

**Post-event**
- Payments: pending amounts with a follow-up log per person
- Follow-ups: who, why, owner, due date, status
- Queries and feedback: type them in or upload a Google Form export. Each item keeps the file it came from.
- Post-production checklist and logistics wrap-up (pack back, returns, vendor settlement)

**Media and assets**
- Photos: collected, scaled, uploaded to Drive
- Videos: footage collected, edited, uploaded to Drive
- Testimonials: taken, how many, edited, uploaded
- Asset register: who has what and whether it came back

## Bring your own sheets

Click **Import** and pick Excel, CSV or Word files, several at once. The app reads the column headers and fills the right section. Re-importing the same rows does not create duplicates.

The **Templates** tab has a download for each stage. Fill them in Excel or Google Sheets (File, Import to open; File, Download, .xlsx to bring back) and import. Rows marked "(example)" are skipped.

A Word doc with bold headings and bullet lists becomes checklist groups. Groups starting with "SE" go to the Organiser list.

## Display mode

The app opens in Display mode so it is safe to put on a projector. Everyone shows as paid and no amounts, payment lists or payment follow-ups appear anywhere. Click **Display mode** and confirm to see the real numbers.

## Several events

Use **Manage** to add, duplicate, rename or delete events. Duplicate can copy just the logo and venue (Empty) or also the checklists, agenda and meal times with every tick cleared (Structure). Each event can have its own logo, shown in the header and as a watermark.

## Try it with demo data

`demo-data/` has made-up sheets for a February batch: 30 participants, the full agenda, meals, feedback form responses, media and assets. Every name, phone number and amount in them is fake.

1. Open `app.html`
2. Click **Import** and select all files in `demo-data/`

## Your data

Everything is saved in your browser (localStorage) on your own computer. Nothing is uploaded anywhere. Use **Backup** in the ⋯ menu to download a copy, and import that file to restore it.

To preload your own event, put a `seed.js` next to `app.html` with `const SEED = {...}`. It is in `.gitignore` so real participant data never gets committed.

## Tests

```
node test_import.mjs      # sheet import and template round trip
node test_display.cjs     # no payment info shows in Display mode
python3 test_e2e.py       # full browser run in headless Chrome (needs: pip install playwright openpyxl)
```

## Built with

Plain HTML, CSS and JavaScript. [SheetJS](https://sheetjs.com) reads and writes Excel, [Mammoth](https://github.com/mwilliamson/mammoth.js) reads Word.
