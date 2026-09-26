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

# Seed demo data (creates mess.db with sample students/menus/attendance)
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

## What's implemented

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
- Email notifications, push reminders, and file storage for PDF reports
  (mentioned as optional in the original architecture) are not implemented.
