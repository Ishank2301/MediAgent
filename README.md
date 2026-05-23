# MediAgent

Full-stack AI medical assistant with persistent chat, symptom triage, drug interaction checks, appointment reminders, medication adherence tracking, PDF export, and file analysis.

<<<<<<< HEAD
> Disclaimer: MediAgent is for informational and educational use only. It does not provide medical advice, diagnosis, or treatment. Always consult a qualified healthcare professional.
=======
>>>>>>> 82b3e2ae31d851bacf2297cc50268510f869a118

## Project Structure

```text
MediAgent/
  backend/                  FastAPI app and service layer
    agents/                 Chat and medical orchestration
    api/                    REST endpoints
    services/               Gemini, search, OCR, PDF, email, Twilio, DB helpers
    triage/                 Rule-based symptom triage
    main.py                 FastAPI entrypoint
    scheduler.py            Background reminder jobs
  frontend/                 React + Vite + Tailwind app
    src/App.jsx             Main UI
    src/api/client.js       Axios API client
  mediagent.db              Local SQLite database
  requirements.txt          Python dependencies
  .env.example              Environment variable template
```

## Local Setup

```bash
pip install -r requirements.txt
copy .env.example .env
```

Add your Gemini key to `.env`:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Start the backend:

```bash
uvicorn backend.main:app --reload --port 8000
```

Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Free Deployment

Recommended free split:

1. Deploy `frontend/` to Vercel or Netlify.
   - Build command: `npm run build`
   - Output directory: `dist`
   - Env: `VITE_API_BASE_URL=https://your-backend-url/api`

2. Deploy the backend to Render, Railway, or Koyeb as a Python web service.
   - Root directory: repository root
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - Env:
     - `GEMINI_API_KEY=...`
     - `GEMINI_MODEL=gemini-2.5-flash`
     - `FRONTEND_ORIGINS=https://your-frontend-url`

3. Database note:
   - The app uses local SQLite (`mediagent.db`). Free hosts often have ephemeral disks, so chat history can reset after redeploys or restarts.
   - For real persistent deployment, move the DB to a free managed Postgres service later.

## Gemini Notes

The app uses Google Gemini through the Gemini API. `gemini-2.5-flash` is the default because it is fast, capable, and suitable for chat-style medical guidance. For even faster but lighter answers, set:

```env
GEMINI_MODEL=gemini-2.5-flash-lite
```
