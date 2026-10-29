# Mess Management System — Working Prototype

A full-stack attendance-first food-waste reduction system for a hostel mess,
plus the extra features discussed: diet profiles, guest meal booking,
QR-style meal check-in, inventory linkage, a menu optimizer, keyword-based
complaint sentiment, and simple rule-based anomaly detection.

## Stack
- **Backend:** FastAPI + SQLAlchemy (sync) + SQLite by default (swap to
  Postgres by setting `DATABASE_URL`, e.g.
  `postgresql://user:pass@localhost/mess`). JWT auth.
- **Frontend:** React 18 + Vite + Tailwind CSS + Recharts.

## Quick start

### 1. Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Seed demo data (creates mess.db with sample students, menus, attendance, kitchen logs, rescues)
# NOTE: delete backend/mess.db first if you are upgrading from an earlier version (new tables are added)
python -m app.seed

# Run the API
uvicorn app.main:app --reload --port 8000
```
API docs (Swagger UI) will be at **http://127.0.0.1:8000/docs**.

### 2. Frontend
In a second terminal:
```bash
cd frontend
npm install
npm run dev
```
App will be at **http://127.0.0.1:5173**.

### Demo logins (from the seed script)
| Role    | Email                  | Password    |
|---------|------------------------|-------------|
| Admin   | admin@mess.local       | admin123    |
| Kitchen | kitchen@mess.local     | kitchen123  |
| Student | student1@mess.local ... student20@mess.local | student123 |

The seed script backfills 14 days of realistic history (menus, attendance,
feedback, some check-ins, a few complaints) so analytics, the menu
optimizer, and anomaly detection all have something to show immediately.


## New in v2: kitchen log, surplus rescue, automation

The first version measured waste as a proxy (*confirmed minus checked in*). The system never knew how much was
actually cooked. v2 closes that gap and then *does something* about leftovers.

### 1. Kitchen production log  (`/kitchen`)
- **Cooking sheet:** how much to cook = confirmed students (weighted by half/regular/large portions) + guest meals
  + an estimate for students who never answered + a safety buffer. Shows diet and allergy counts for the kitchen.
  It's a plain formula (not ML), so the kitchen can see why. Tune it in `config.py`.
- **Production log:** staff record portions cooked and served. Leftover is computed, with a reason
  (over-production, unpopular dish, low turnout, spoilage).
- **Real waste** = leftover - rescued. Shown on the Analytics page and in the weekly report.

### 2. Surplus rescue  (`/rescue` for students, `/surplus` for kitchen/admin)
```
leftover logged -> kitchen lists it (confirms food was held safely)
   -> last-call notification to all students (30 min window, 1 portion each, claim code)
   -> window ends: automatically offered to active NGO partners (email link, no login needed)
   -> first NGO to accept wins -> kitchen records the pickup
   -> anything not collected before the safe-until time expires. Nothing unsafe stays on offer.
```
Rules worth knowing: food has a safe window (`SURPLUS_SAFE_HOURS`, default 3h), unclaimed holds return to the
shelf after 30 minutes, and `wasted = listed portions - collected` is derived, never stored, so it can't drift.
Check your college's policy and FSSAI's food-recovery guidance before using this with real food.

### 3. Automation  (admin: `/automation`)
A small background thread checks the clock every 60 seconds. Each job runs at most once per meal/day because the
`automation_runs` table has a unique `(job, run_key)`; a restart can't send a reminder twice.

| Job | When | What it does |
|---|---|---|
| deadline_reminder | 60 min before the deadline | In-app reminder to students who haven't answered |
| cooking_sheet | When the deadline passes | Sends the kitchen + admin the cooking sheet |
| anomaly_alert | After the deadline | Warns the admin about unusually high or low skip rates |
| low_stock | After 17:00 | Checks tomorrow's menu against stock and lists shortages |
| weekly_report | Monday 08:00 | Builds and sends last week's report |
| surplus_maintenance | Every tick | Expires holds, offers leftovers to NGOs, expires unsafe food |

The Automation page has "Run now" buttons (ignore the time rules, good for demos), a run log, and an **outbox**
showing every message, including the NGO emails with their response links. If you set the `SMTP_*` environment
variables the same messages are also emailed; without them they only appear in the outbox.



## New in v3: nutrition details and a calorie intake log

- **Nutrition per meal:** every dish has approximate calories, protein, carbs, fat and fibre for one regular
  portion, plus whether it is veg, egg or non-veg and which allergens it contains. Students see the calories
  for each meal on **Today** and **Weekly menu**.
- **Personal warnings:** a meal is flagged ("Check before eating: Upma: contains gluten") when a dish clashes
  with the student's *own* allergy or diet profile (set on the Profile page). Nothing is inferred.
- **Food log** (`/nutrition`, students): one click logs a mess meal ("I ate this"). The server works out the
  food and numbers from the menu x the portion size (half 0.5, regular 1, large 1.5). Students can add
  outside food with their own numbers, see daily totals, a 7-day chart, and set an optional target.
- **Nutrition data** (`/nutrition-data`, kitchen and admin): edit any dish's values; dishes on the menu with
  no data yet are flagged.

Design decisions worth knowing for a viva:
- Log entries **copy** the numbers at logging time, so correcting a dish later never rewrites history.
- A mess meal can be logged once per day per meal; dates in the future or more than 30 days back are refused.
- A student can only see or delete their own entries (the delete query filters by owner, so another
  student's entry ID just returns 404).
- Targets are optional and limited to 1200-5000 kcal. The UI shows progress neutrally.
- The starting values for the 12 seeded dishes are **rough estimates**, not lab data. The mess should check
  and correct them. This is not medical or dietetic advice.
- No database reset is needed to upgrade from v2: the new tables are created on start-up and the starting
  values are filled in for known dishes (existing edits are never overwritten).

### Bug fixes (v2.1)
Found by auditing the code and probing it; each one has an automated regression test (57 checks in total).
- **Privilege escalation:** public sign-up used to accept `role=admin`. Now it always creates a student; only a
  logged-in admin can create admin/kitchen accounts (`POST /auth/staff`, use the Authorize button on `/docs`).
- **Overselling surplus:** many students claiming the last portion at once could all win it. Claiming is now a
  single atomic database update, so exactly one wins.
- **Portion dropdown** on the student page saved the previous value instead of the new one.
- **Weekly report:** viewing the Analytics page wrote a new report row every time, and its top cards covered the
  wrong dates. Viewing is now read-only and the cards show the last 7 days up to the selected end date.
- **Counter check-in** now only accepts today's meals (an old meal could be checked in and skew waste figures).
- **Validation:** unknown severity, portion size or status values now return a clear 422 instead of being stored.

### Settings (environment variables, all optional)
`LOCAL_TZ_OFFSET_MINUTES` (330 = IST), `SURPLUS_SAFE_HOURS`, `SURPLUS_STUDENT_WINDOW_MINUTES`, `CLAIM_HOLD_MINUTES`,
`MAX_PORTIONS_PER_STUDENT`, `NON_RESPONDER_EAT_RATE`, `COOKING_BUFFER_PCT`, `AUTOMATION_ENABLED`,
`AUTOMATION_TICK_SECONDS`, `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM`, `FRONTEND_BASE_URL`.

### Other changes
- **Timezone fix:** deadlines and schedules now use the mess's local time (`timeutil.py`) instead of server UTC.
- Meal types are validated strictly (`breakfast|lunch|dinner`); bad values get a clear 422.
- `requirements.txt` is unpinned so it installs on new Python versions without needing a Rust compiler.
- No new dependencies were added.

### Run the automated test
```bash
pip install -r requirements-dev.txt
python -m tests.smoke_test      # uses a throwaway database; simulates time passing, no waiting
```

### 5-minute demo script
1. Log in as **kitchen@mess.local** > Kitchen log > Lunch. Read the cooking sheet, then enter cooked 24, served 18.
2. Tick the safe-food box > **Offer to students**.
3. In another browser window, log in as **student1@mess.local** > Rescue meals > **Claim a portion** (note the code).
4. Back as kitchen > Rescue & donations > enter the code > **Hand over**. Then **Offer to NGOs now**.
5. As **admin@mess.local** > Automation > open the outbox, click the NGO's response link, accept it.
6. Kitchen > Record pickup. Admin > Analytics > the **Real food waste** panel now shows what was rescued.

## What's implemented (v1 features, still included)

**Student app**
- Confirm "Will eat" / "Skip" per meal with a mandatory skip reason, portion
  size, and a deadline (2h before meal service — configurable in `config.py`)
- Weekly menu view
- Dish feedback (rating + tags + comment)
- Complaints & suggestions form
- Guest meal booking
- Diet restriction / allergy profile
- "My Impact" page (meals skipped, estimated cost/CO₂/water saved, streak)

**Admin dashboard**
- Today's per-meal predicted vs. confirmed vs. actual-checked-in counts,
  skip-reason breakdown
- Rule-based anomaly alerts (unusual skip-rate spikes vs. trailing average)
- Menu planner (create/edit daily menus)
- Analytics: attendance by meal/hostel (charts), dish ratings, weekly waste
  report
- Menu optimizer: advisory-only suggestions to rotate out dishes with low
  ratings + high "don't like menu" skip correlation
- Inventory: item catalog, dish→ingredient linking, and a per-meal
  ingredient-requirement calculator (from confirmed attendance)
- Complaints inbox with status workflow and a lightweight sentiment tag
  (keyword-based — good enough for a mini-project; swap for a real
  NLP model/API if you want to take it further)

## Notes on scope / things you may want to extend
- **Auth storage:** the frontend keeps the JWT in `localStorage` for
  simplicity. The original architecture called for httpOnly cookies —
  swap this in for anything beyond a local demo.
- **Meal check-in** is simulated in the admin dashboard by typing an
  attendance ID (representing a QR scan at the counter). Wiring up an
  actual QR code (e.g. with a library like `qrcode.react` + a scanner) is a
  natural next step and the `/attendance/checkin` endpoint already supports it.
- **Anomaly detection & menu optimizer** are transparent rule/stats-based
  heuristics, not ML models — intentional for a mini-project (explainable,
  no training data needed) but noted as a possible upgrade path.
- **Postgres:** switch `DATABASE_URL` and install `psycopg2-binary`; no
  code changes needed since SQLAlchemy abstracts the dialect.
- Push notifications and PDF report generation are still not implemented. Emails need SMTP settings.
- Notifications are in-app (polled every 30 s), not push. Real-time would need WebSockets or a push service.
- NGOs respond through an emailed link; they have no accounts or login.
- Anyone can still choose the admin role on the register page. Restrict that before real use.
