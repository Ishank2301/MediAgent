# ✚ MediAgent v5.0 — AI Medical Copilot

> Full-stack AI medical assistant with agentic services: appointments, email/WhatsApp notifications, live drug search, medication adherence tracking, and persistent AI chat.

---

## Features

| Module | Description |
|---|---|
| 💬 **Persistent Chat** | 4 modes — General, Symptoms, Drug Check, Prescription. History saved forever. |
| 🧠 **Smart Triage** | Weighted symptom scoring + risk factor detection (diabetes, pregnancy, etc.) |
| 📅 **Appointment Planner** | Book & manage doctor appointments. One-click email/WhatsApp reminders. |
| 🔔 **Email Notifications** | Medication reminders, adherence reports with PDF, missed dose alerts (Gmail SMTP) |
| 💬 **WhatsApp Notifications** | All alerts via Twilio sandbox — free to set up in 5 minutes |
| ⏰ **Auto Scheduler** | Background jobs: daily med reminders, appointment alerts, weekly reports |
| 🌐 **Web Search Agent** | Live drug info via DuckDuckGo + PubMed + AI summarization |
| 👨‍⚕️ **Doctor Finder** | Suggests specialists based on your symptoms |
| 💊 **Drug Interaction Checker** | RxNorm + FDA database + AI explanation |
| 🔬 **Medicine Info** | FDA label data lookup with AI-powered patient summary |
| 💉 **Medication Tracker** | Daily schedule, dose logging, 30-day adherence % |
| 📄 **PDF Export** | Chat sessions + adherence reports as professional PDFs |
| ⚖️ **BMI Calculator** | Metric & imperial with visual gauge |
| 🌙 **Dark Mode** | Full dark/light theme, persisted to localStorage |

---

## Quick Start

### 1. Install Ollama & pull a model
```bash
# Install: https://ollama.com
ollama pull mistral:7b-instruct-q4_0
# Or faster: ollama pull phi3:mini
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure credentials (optional but recommended)
```bash
cp .env.example .env
# Edit .env — add Gmail App Password + Twilio credentials
```

### 4. Start backend
```bash
uvicorn backend.main:app --reload --port 8000
```

### 5. Start frontend
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

---

## Notification Setup

### ✉️ Email (Gmail — free)
1. Enable 2FA on your Google account
2. Visit **myaccount.google.com/apppasswords**
3. Create App Password → "Mail" → copy 16-char code
4. Set `SMTP_USER` and `SMTP_PASS` in `.env`

### 💬 WhatsApp (Twilio — free sandbox)
1. Sign up at **twilio.com** (no credit card needed for sandbox)
2. Go to **Messaging → Try it out → Send a WhatsApp message**
3. Text `join <word>` to `+1 415 523 8886` from YOUR WhatsApp
4. Copy `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` to `.env`

### ⏰ Auto Reminders
Add to `.env`:
```
REMINDER_EMAIL=your@gmail.com
REMINDER_PHONE=+1234567890
```
The background scheduler then automatically sends:
- **Daily at 7 AM UTC** — today's medication schedule
- **Every hour** — appointment reminders (24h in advance)
- **Every Monday at 8 AM UTC** — weekly adherence report + PDF attachment

---

## API Docs
Visit **http://localhost:8000/docs** for the interactive Swagger UI.

---

## Tech Stack
- **Backend**: FastAPI · SQLAlchemy · SQLite · APScheduler
- **LLM**: Ollama (local, free) — Mistral 7B or Phi-3 Mini
- **Frontend**: React 18 · Vite · Tailwind CSS · Syne + Instrument Sans fonts
- **PDF**: ReportLab
- **Email**: Python smtplib (Gmail SMTP, no paid service)
- **WhatsApp**: Twilio Messaging API
- **Drug data**: FDA OpenFDA API · RxNorm API
- **Search**: DuckDuckGo Instant Answers · PubMed E-utilities

---

> ⚠️ **Disclaimer**: MediAgent is for informational and educational purposes only. It does not provide medical advice, diagnosis, or treatment. Always consult a qualified healthcare professional.
