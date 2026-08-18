# Installing holec_trading

This is a real Frappe app skeleton — doctypes, controllers, and hooks —
not a mockup. It needs to be placed into a working bench and installed
on your site. Hand this file to your developer directly.

---

## 0. What's already built vs what he still needs to do

**Built here (ready to drop in):**
- Charge Master — full doctype + 9-row seed data
- Lot — full doctype, six-state enforcement, moisture band logic, landed
  cost calculation, commingling check, Advance State button
- Cost Ledger Entry — child table, append-only enforcement, reason-code
  requirement
- Buy Ticket — doctype + margin calculation + ticket-to-lot conversion
  (including split-into-multiple-lots)
- Rail Routing Band, Lot Event Log, Origin County, Origin Area, Storage
  Stack — supporting doctypes

**Still needed from him:**
- Supplier/Customer custom fields (rail preference, quality profile,
  etc.) — these attach to ERPNext's *native* doctypes via Customize
  Form, not something to hand-code
- The Quality Inspection template configuration (native doctype, just
  needs your parameters entered through the UI)
- Navari eTIMS and Mpesa app installation
- Payment Entry rail-suggestion script (reads Rail Routing Band —
  structure is there, the lookup script itself is a short addition)
- Real GL Accounts matching the account names referenced in the Charge
  Master fixture (e.g. "Moisture Deductions - H") — these need to exist
  in your Chart of Accounts before the fixture will import cleanly
- Testing against your actual site, and fixing whatever breaks when
  this code meets his specific Frappe version

---

## 1. Prerequisites

He needs an existing bench with ERPNext already installed. If that's
not set up yet, that's a separate, larger task — this assumes it's done.

```bash
cd frappe-bench
```

## 2. Get the app into the bench

Two options, tell him which is easier given how you're sharing files:

**Option A — copy the folder directly (simplest for a first pass)**
Place this entire `holec_trading` folder (the one containing
`pyproject.toml` and `README.md`) into `frappe-bench/apps/holec_trading`.

Then register it:
```bash
bench setup requirements
```

**Option B — proper git repo (recommended before this touches production)**
He should `git init` inside this folder, push it to a private repo, then:
```bash
bench get-app https://github.com/your-org/holec_trading.git
```
This is the right long-term approach — lets him version it, branch it,
and roll back if something breaks.

## 3. Install the app on the site

```bash
bench --site your-site-name install-app holec_trading
```

This creates all the doctypes (Lot, Buy Ticket, Charge Master, etc.) in
the database and loads the Charge Master fixture data — but only after
the GL accounts it references exist (see step 4).

## 4. Before installing: create the GL accounts

The Charge Master fixture references these account names. He needs to
create them in Chart of Accounts first (or rename the fixture to match
accounts that already exist):

- Moisture Deductions - H
- Foreign Matter Deductions - H
- Bagging Expense - H
- Lab Testing Expense - H
- Bank Charges - H
- Transport Cost - H
- Offloading Expense - H
- Transport Loss Recovery - H

If these don't exist yet, install the app first, skip fixture import,
create the accounts, then re-import fixtures:
```bash
bench --site your-site-name migrate
```

## 5. Test on a throwaway site first — not the real one

```bash
bench new-site test.local
bench --site test.local install-app erpnext
bench --site test.local install-app holec_trading
```
Create a test Supplier, a test Buy Ticket, convert it to a Lot, click
"Advance State" a few times, watch the Cost Ledger entries populate.
Try to break the enforcement — edit a posted cost line directly and
confirm it's rejected. This is the cheapest place to find problems.

## 6. Only once that works, install on the real site

```bash
bench --site your-real-site install-app holec_trading
bench --site your-real-site migrate
```

## 7. What to sanity-check together before go-live

- Create one real Buy Ticket end to end, through Settled — watch the
  Advance State button work at each step, confirm the toast/error
  messages make sense to Minal
- Try to skip a state directly by editing the field — confirm it's
  blocked (this is the core rule; if it's not enforced, that's the one
  thing to fix before anything else)
- Try to edit an already-posted Cost Ledger line's amount — confirm
  it's rejected
- Enter moisture at 22% — confirm the orange "requires approval" banner
  shows on the Lot
