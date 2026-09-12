# Repo Sense

Repo Sense turns a public GitHub repository URL into a concise, structured report grounded in the repository evidence it collected.

## Local setup

Use Python 3.11+ and Node.js 18+.

1. Install the API dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

2. Create `secrets/.env` from `.env.example` and set `GROQ_API_KEY`. `GITHUB_TOKEN` is optional for higher GitHub API limits. The existing CLI also reads `secrets/.env`.

3. Start the API from the repository root:

   ```powershell
   uvicorn api.app:app --reload --port 8000
   ```

   Check `http://localhost:8000/health`.

4. Start the web client in a second terminal:

   ```powershell
   cd web
   npm install
   npm run dev
   ```

   Open the URL Vite prints, normally `http://localhost:5173`.

The web client uses `VITE_API_BASE_URL` when present and otherwise calls `http://localhost:8000`:

```powershell
$env:VITE_API_BASE_URL="https://your-api.example.com"
npm run build
```

## API

`POST /api/analyze`

```json
{ "repo_url": "https://github.com/owner/repo" }
```

The response is the report schema produced by the existing GitHub packing and LLM pipeline. Weak evidence returns HTTP 200 with `status` set to `low_confidence` or `refuse`. Invalid repository input returns 400. Missing server configuration returns a sanitized 500 response, and rate limiting returns 429.

`GET /health` returns `{ "status": "ok" }`.

The API accepts GitHub URLs and the existing short `owner/repo` form. `CORS_ORIGINS` is a comma-separated list of allowed browser origins. `GITHUB_TIMEOUT_SECONDS`, `LLM_TIMEOUT_SECONDS`, `RATE_LIMIT_REQUESTS`, and `RATE_LIMIT_WINDOW_SECONDS` can be adjusted through environment variables.

## Deployment notes

Deploy the Python API separately on Render, Fly.io, Railway, Cloud Run, or another Python-capable host. Set `GROQ_API_KEY`, optional `GITHUB_TOKEN`, and `CORS_ORIGINS` to the deployed static site's origin. Start it with:

```text
uvicorn api.app:app --host 0.0.0.0 --port $PORT
```

Build `web` with `npm run build` and deploy the generated `web/dist` directory to GitHub Pages or another static host. Set `VITE_API_BASE_URL` at build time to the hosted API URL. Never put either API key in the `web` directory or any `VITE_*` variable.

## Existing CLI

The original one-shot CLI remains available:

```powershell
python main.py https://github.com/owner/repo
```
