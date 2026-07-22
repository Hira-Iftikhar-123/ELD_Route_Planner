# ELD Route Planner

Full-stack trip planner for property-carrying CMV drivers (FMCSA 70 hrs / 8 days).

## HOS assumptions

- Property-carrying, **70 hrs / 8 days**, no adverse driving conditions
- Fuel at least every **1,000 miles** (~30 min on-duty)
- **1 hour** on-duty for pickup and dropoff
- **11h** driving / **14h** window / **30-min** break after 8h driving
- **10h** off (sleeper) resets 11/14; **34h** restart when cycle is exhausted
- Home terminal timezone: `America/Chicago`

## Structure

- `frontend/` — React + Vite → **deploy on Vercel**
- `backend/` — Django API → **deploy on Render** (or Railway/Fly)
- `vercel.json` — builds the frontend from the repo root

> Django cannot run as a normal long-lived app on Vercel. Frontend goes to Vercel; API goes to Render. Both are free-tier friendly.

## Local setup

### 1. Environment

Copy `.env.example` → `.env` and set `GEOLOCATION_API_KEY`.

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Health: http://127.0.0.1:8000/api/health/

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://127.0.0.1:5173/  
Locally, Vite proxies `/api` to Django (no `VITE_API_URL` needed).

---

## Deploy (recommended)

### A. Backend on Render

1. Push this repo to GitHub.
2. [Render](https://render.com) → **New** → **Blueprint** (uses `render.yaml`), or **Web Service** with:
   - **Root Directory:** `backend`
   - **Build:** `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput`
   - **Start:** `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
3. Set env vars:
   - `GEOLOCATION_API_KEY`
   - `DJANGO_SECRET_KEY` (random)
   - `DJANGO_DEBUG=false`
   - `DJANGO_ALLOWED_HOSTS` = your Render host, e.g. `eld-api.onrender.com`
   - `CORS_ALLOWED_ORIGINS` = your Vercel URL, e.g. `https://eld-route-planner.vercel.app`  
     (`*.vercel.app` previews are already allowed via regex in settings)
4. Note the API URL, e.g. `https://eld-api.onrender.com`

### B. Frontend on Vercel

1. [Vercel](https://vercel.com) → **Add New Project** → import this GitHub repo.
2. Leave root as the repo root (uses root `vercel.json`), **or** set Root Directory to `frontend`.
3. Environment variable:
   - `VITE_API_URL` = `https://eld-api.onrender.com` (no trailing slash)
4. Deploy. Your live app URL is the assessment deliverable.

### After deploy checklist

- Open Vercel URL → Plan trip → health/API calls succeed (no CORS errors).
- `GET https://your-api.onrender.com/api/health/` returns `{ "status": "ok", ... }`.