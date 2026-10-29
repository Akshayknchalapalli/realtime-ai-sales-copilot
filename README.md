# Real-Time AI Sales Copilot

Interview assignment: live transcript → FastAPI WebSocket → conversation context → RAG product retrieval → AI next-best-response → React SDR dashboard.

## Run backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Run frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Without an API key, the backend uses transparent offline demo recommendations. For live grounded AI, copy `backend/.env.example` to `.env` and set `OPENAI_API_KEY`, then run backend with the environment loaded.

The input is a simulated live transcript with separate SDR/customer speakers. It is not live microphone transcription. Production needs authentication, persisted sessions, consent, hardened PII handling, and expanded evaluation.
