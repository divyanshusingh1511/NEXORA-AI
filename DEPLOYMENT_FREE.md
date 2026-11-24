# NEXORA AI — free deployment guide

This project can be deployed as two free services on Render:

- Backend: Render Web Service (FastAPI, free plan)
- Frontend: Render Static Site (Vite build, free)

## Important limits

The free Render backend sleeps after 15 minutes without traffic and may take about a minute to wake. Its filesystem is ephemeral, so the SQLite database can be reset after a restart/redeploy/spin-down. This is suitable for a demo, not durable production storage. The project currently uses SQLite by design; do not assume chat history is permanent on the free host.

## 1. Push this project to GitHub

Create a new GitHub repository and upload the contents of this folder (not the ZIP file itself). Do not upload `.env`, API keys, `node_modules`, `.venv`, or `dist`.

## 2. Deploy backend first

1. In Render, choose **New → Blueprint** and connect the GitHub repository.
2. Render detects `render.yaml`; create the `nexora-ai-api` service on the **Free** plan.
3. In the backend service's Environment settings, add `LLM_API_KEYS` with at least two valid provider API keys separated by commas. Keep these secret; never put them in the frontend or GitHub.
4. After the service deploys, copy its URL, e.g. `https://nexora-ai-api.onrender.com`.
5. Test `https://YOUR-BACKEND-URL/health`. It should return status `ok` and show at least two configured keys. If it reports fewer than two keys, correct `LLM_API_KEYS`.

## 3. Deploy frontend

1. In Render, choose **New → Static Site** and connect the same GitHub repository.
2. Set **Root Directory** to `frontend`.
3. Set **Build Command** to `npm install && npm run build`.
4. Set **Publish Directory** to `dist`.
5. Add build-time environment variable `VITE_API_URL` with the backend URL from step 2 (no trailing slash).
6. Deploy. Copy the frontend URL, e.g. `https://nexora-ai.onrender.com`.

## 4. Allow frontend requests on backend

In the backend Render service → Environment, set `ALLOWED_ORIGINS` to the exact frontend origin, e.g. `https://nexora-ai.onrender.com` (no trailing slash). Save and redeploy.

## 5. Verify

- Open the frontend URL.
- Confirm the health status is connected.
- Send a real prompt. This uses your configured provider keys and may incur provider charges under their own terms/quotas.
- In Developer Playground, test primary-key 429/500 fallback and all-keys 429 (503). `ENABLE_FAILURE_SIMULATION=true` is enabled by the Render blueprint. The simulation only injects failures; successful fallback still calls the real provider.

## Secrets and costs

- Never share provider keys in chat, source code, screenshots, or GitHub.
- Put at least two valid provider keys only in the backend's `LLM_API_KEYS` environment variable.
- Hosting is configured for Render's free tier. AI provider API usage is separate and may not be free.
- The free backend can sleep, restart, and lose its local SQLite history. Render documents these free-tier limitations.
