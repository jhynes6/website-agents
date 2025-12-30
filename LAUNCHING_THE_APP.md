### Local dev quickstart

### 1) Start the Python backend

```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2) Start the Next.js frontend

```bash
cd ..
npm run dev
```

Notes:
- `npm run dev` sets `NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000`, so the UI will call the backend directly.
- If port 8000 is already in use, either stop the old process or change both the backend port and `NEXT_PUBLIC_BACKEND_URL`.