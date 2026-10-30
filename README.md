# Real-Time AI Sales Copilot

An interview MVP that recommends the next response for a sales development representative (SDR) during a **text-based** sales conversation. The fictitious product is **FlowDesk CRM**; the bundled product documentation is sample data, not a real commercial product.

## Architecture

React + TypeScript (Vite) → WebSocket → FastAPI → conversation history → EmbeddingGemma + FAISS retrieval → local Ollama Qwen3 4B Instruct → structured SDR recommendation.

Recommendations include the detected customer intent, a short SDR-facing suggestion, rationale, next action, document source IDs, and end-to-end latency.

## Prerequisites

- Python 3.11 or newer, Node.js 20 or newer.
- [Ollama](https://ollama.com/download) running locally.
- A machine capable of running the Qwen3 4B model; response times depend on memory, hardware and prompt size.

Download the models:

```bash
ollama pull qwen3:4b-instruct
ollama pull embeddinggemma
```

## Start the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m pytest -q
python -m uvicorn app.main:app --reload
```

If you already have a `backend/.env`, update it manually: copying the example is not required. Recommended local settings:

```dotenv
AI_PROVIDER=ollama
OLLAMA_CHAT_MODEL=qwen3:4b-instruct
OLLAMA_EMBED_MODEL=embeddinggemma
OLLAMA_TWO_STAGE=0
USE_FAISS=1
OLLAMA_CONTEXT_SIZE=4096
OLLAMA_MAX_OUTPUT_TOKENS=200
```

Check [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health); expected mode is `ollama`, chat model `qwen3:4b-instruct`, and retrieval `faiss`. If `keyword-fallback` appears, check Ollama embedding availability and backend logs.

## Start the frontend

In a **separate** terminal:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Enter messages marked **Customer** or **SDR**. The sample conversation is optional. Review the proposed recommendation and edit it before speaking to a customer.

## Verification

```bash
cd backend
source .venv/bin/activate
python -m pytest -q
python -m scripts.evaluate_scenarios
```

```bash
cd frontend
npm run build
```

The tests primarily mock external inference: a passing unit suite **does not** prove live model accuracy, hardware latency, or factual grounding. The evaluation script sends eight customer scenarios through the configured provider and prints raw recommendations and timing. Actual model inference requires Ollama running.

### Suggested live test

Enter these **Customer** turns in the same session, reviewing each suggestion:

1. “We have 15 representatives processing 500 leads every day in Excel.”
2. “Our representatives often miss follow-ups. Can FlowDesk remind them?”
3. “Can FlowDesk automatically score and rank our leads using AI?”
4. “Does FlowDesk support automatic Salesforce synchronization?”
5. “Your pricing seems expensive compared with Excel.”
6. “I'd like to schedule a demonstration next Tuesday.”

The documentation supports lead tracking and reminders; it **does not** establish automated lead scoring or native Salesforce synchronization. The last customer turn should take precedence over earlier pricing discussion.

## Evaluation and limits

- The live Ollama path uses **one model call per customer recommendation** by default. Experimental two-stage customer understanding is available only when `OLLAMA_TWO_STAGE=1`, and may increase latency.
- The application displays **raw, unverified model-generated recommendations**. It filters source IDs to retrieved passages but **does not** replace mistaken claims with canned or verified fallback responses. This is intentional for model evaluation.
- Older guard/evidence/recovery modules remain for historical tests; they are **not used** in the live Ollama recommendation path.
- All knowledge is bundled in `knowledge/*.md`. FAISS embeddings are built at backend startup; keyword retrieval is a fallback.
- Sessions are in memory, with versioning to discard outdated results. There is **no automatic transcription, live telephone audio, diarization, authentication or persistent conversation storage**.
- The model can invent product capabilities or overstate outcomes; a human must verify suggestions before use. This is not production-ready.
- Report measured response times, not guaranteed latency targets. A local thinking-mode model may take substantially longer to generate a usable response.
- Never commit `.env`, credentials or personal customer data.

## Alternative providers

The code includes an optional OpenAI generation path and deterministic offline demonstration mode. The primary documented submission path is **local Ollama + Qwen3 4B Instruct + EmbeddingGemma + FAISS**. Offline demo outputs are not AI-generated.

## Submission

Repository: [Akshayknchalapalli/realtime-ai-sales-copilot](https://github.com/Akshayknchalapalli/realtime-ai-sales-copilot)

Present this as a **transcript-driven RAG sales copilot prototype**, not a deployed real-time telephone assistant. Explain the retrieval pipeline, latest-turn priority, JSON output validation, source references, evaluation cases, and measured latency trade-offs.
