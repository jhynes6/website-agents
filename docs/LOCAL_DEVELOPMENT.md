### Local development (Mac)

### Prereqs
- Node.js + npm
- Python venv in `backend/venv/`

### 1) Start the Python backend
From repo root:

```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

If you see “address already in use”, either kill the existing process or pick a different port.

### 2) Start the Next.js frontend
From repo root:

```bash
npm run dev
```

This repo’s `npm run dev` pins:
- `NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000`

So the UI will call the Python backend directly in dev.

### 3) Quick health checks
- Backend: `GET http://127.0.0.1:8000/healthz`
- Frontend: `http://localhost:3000`


