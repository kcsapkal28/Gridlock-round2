# Deploying GridLock to Render (UI guide)

Two services: **`gridlock-api`** (FastAPI backend) and **`gridlock-web`** (static Vite frontend).
A `render.yaml` Blueprint is included, so the one-click Blueprint flow (Path A) is easiest.

> Render deploys from a Git host. **First push this repo to GitHub** (it has no remote yet):
> ```
> git remote add origin https://github.com/<you>/gridlock.git
> git push -u origin main
> ```
> The committed `srv_data/` (model + scores) and `web/public/data/` (map bundle) ship with the repo.

---

## Path A — Blueprint (recommended, ~2 clicks)

1. Render Dashboard → **New +** (top right) → **Blueprint**.
2. **Connect** your GitHub account if prompted, then pick the **gridlock** repo. Render reads `render.yaml`.
3. Render shows two services to create (`gridlock-api`, `gridlock-web`). Click **Apply**.
4. Wait for **gridlock-api** to go **Live** (first build ~3–5 min; installs pandas/lightgbm). Open its URL +
   `/api/v1/health` → should return `{"status":"ok", ...}`. Copy the service URL (e.g.
   `https://gridlock-api.onrender.com`).
5. If that URL differs from what's in `render.yaml`: open **gridlock-web → Environment**, set
   **`VITE_API_BASE`** to the exact API URL, **Save**, then **Manual Deploy → Deploy latest commit**
   (the frontend bakes this URL at build time).
6. Open the **gridlock-web** URL → the dashboard loads. Done.

---

## Path B — Manual (two services, no Blueprint)

**Backend (`gridlock-api`):**
1. **New + → Web Service** → connect the repo.
2. Settings: **Runtime** Python · **Region** Singapore · **Branch** main · **Plan** Free.
3. **Build command:** `pip install -r requirements-api.txt`
4. **Start command:** `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
5. **Health check path:** `/api/v1/health`
6. **Environment** → add:
   - `PYTHON_VERSION = 3.12.6`
   - `SCORES_PARQUET = srv_data/cell_scores.parquet`
   - `IMPACT_MODEL = srv_data/model_impact.txt`
   - `RCP_CSV = srv_data/rcp.csv`
   - `CORS_ORIGINS = *`
   - `AI_ENABLED = 0`
   - *(optional)* `MAPPLS_KEY = <your Mappls REST key>` — enables real drive-times/detours;
     without it, patrol times and detours fall back to estimates.
7. **Create Web Service**. When Live, verify `…/api/v1/health`. Copy the URL.

**Frontend (`gridlock-web`):**
1. **New + → Static Site** → same repo.
2. **Root directory:** `web`
3. **Build command:** `npm install && npm run build`
4. **Publish directory:** `dist`  (i.e. `web/dist`)
5. **Environment** → `VITE_API_BASE = https://gridlock-api.onrender.com` (the backend URL from above).
6. *(SPA fallback)* **Redirects/Rewrites** → add: Source `/*` → Destination `/index.html` → **Rewrite**.
7. **Create Static Site**. Open its URL.

---

## Notes
- **Free tier cold start:** the API sleeps after ~15 min idle; the first request then takes ~50 s while it
  wakes. The frontend still loads instantly (static bundle); live scoring/patrol just waits on that first call.
- **MapMyIndia key (optional):** set `MAPPLS_KEY` on the backend for real Distance-Matrix/Routing. Compliant
  (mapping-infra only, ADR-007). Omit it and the app runs with haversine/straight-line fallbacks.
- **AI copilot:** stays off in cloud (`AI_ENABLED=0`) — it needs the local Claude proxy. The UI hides AI
  surfaces automatically when unavailable.
- **CORS:** `*` is set for a public demo. To lock down, set `CORS_ORIGINS` to the exact frontend URL.
- **Updating data:** regenerate `srv_data/*` + `web/public/data/*`, commit, push → Render auto-redeploys.
