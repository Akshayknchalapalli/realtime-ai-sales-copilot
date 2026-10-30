# Real-Time AI Sales Copilot

Transcript-based SDR copilot: React / TypeScript → WebSocket → FastAPI → session context → Ollama embeddings + FAISS → Ollama Qwen recommendation → dashboard.

## Prerequisites

Python 3.11+; Node.js 20+; [Ollama](https://ollama.com/download) installed and running.

## 1. Download local models

```bash
ollama pull qwen3:4b
ollama pull embeddinggemma
ollama list
```

Ollama serves its local API at `http://127.0.0.1:11434`. On macOS launch the Ollama app, or run `ollama serve` if it is not already running.

## 2. Start backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload
```

If you already have a `backend/.env` with an exhausted OpenAI key, **set `AI_PROVIDER=ollama`**; do not commit the key. The local model is not billed through OpenAI.

Confirm semantic indexing:

```bash
curl http://127.0.0.1:8000/health
```

Expect `"mode":"ollama"` and `"retrieval":"faiss"`. If retrieval says `keyword-fallback`, check Ollama availability and ensure `embeddinggemma` is pulled. The initial embedding pass may take time.

## 3. Start frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Send customer messages or play the sample conversation. The dashboard reports generation latency. On a MacBook Air the first local inference can be much slower than cloud API inference; latency targets are not guaranteed.

## 4. Tests

```bash
cd backend
python -m pytest -q
```

The tests use `AI_PROVIDER=offline` so they can run without downloaded models.

## Architecture & limits

- Text transcript input with explicit speaker labels; no microphone or automatic diarization.
- In-memory sessions; WebSocket versioning suppresses stale recommendations.
- Knowledge is bundled in `knowledge/*.md`. FAISS cosine-similarity index is created at backend startup and populated using local Ollama embedding vectors.
- A local Qwen model generates structured suggestions from recent conversation and relevant sources. Structured output and source-ID checks are not full factual verification.
- Keyword retrieval fallback is available if embeddings cannot initialize. Ollama generation failures are surfaced to the UI rather than falsely marked as successful AI inference.
- To use OpenAI instead, set `AI_PROVIDER=openai`, provide `OPENAI_API_KEY`, and configure its models. For a deterministic demo use `AI_PROVIDER=offline`.
- This interview prototype needs authentication, explicit recording consent, persistence, personal data controls, deeper evaluation, and production observability before real deployment.

## Interview demo and final QA

1. Start Ollama, FastAPI and Vite using the commands above.
2. Verify `/health` reports `mode: ollama` and `retrieval: faiss`.
3. Run `cd backend && python -m pytest -q`; from frontend run `npm run build`.
4. In a new dashboard session, submit a **Customer** turn (not an SDR suggestion):
   - Pricing: "We have 15 sales reps and miss follow-ups, but this seems expensive."
   - Integration: "Does FlowDesk offer native Salesforce integration?"
   - Buying: "Can we arrange a demo next week?"
   - Competitor: "We already use another CRM. Why switch?"
   - Feature: "Can it remind us about overdue follow-ups?"
   - Unknown feature: "Can it automate WhatsApp voice calling?"
5. Check the generated wording, intent, knowledge references, and retrieval / generation / total latency.
6. Use **Use / Edit suggestion** to move a recommendation to the SDR composer. Edit it before sending. Or choose **Dismiss**.
7. The backend applies deterministic validation to high-risk sales claims and switches to a safe, speakable recommendation when a known rule is broken. The WebSocket event includes `quality_corrected` to indicate this happened.

### Interpreting the demo

The customer and SDR turns are entered manually or played from an example script; the tool is a *copilot* and does **not** automatically speak as the SDR. The RAG sources describe fictional FlowDesk CRM product facts. The product's seat eligibility, discounts and free trial policies are not documented, so the copilot must not promise those. An Excel/CSV import is not equivalent to continuous Salesforce synchronization.

The reported latency covers retrieval + generation; it **does not include audio transcription**. Two observed local demo turns took approximately 2.77 and 2.85 seconds, but these are not statistically representative benchmarks and the model and hardware must be documented when sharing performance results. Use `python scripts/benchmark_ollama.py --models qwen3:4b qwen3:1.7b` to compare models on your own machine. Guardrails are heuristic and do not guarantee factual accuracy. All production-facing responses need human review.
