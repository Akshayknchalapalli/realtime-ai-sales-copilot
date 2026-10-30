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

## AI generation vs. safety fallback

The live Ollama/OpenAI pipeline now preserves normal LLM-generated recommendations. A
narrow rule-based guard checks high-risk promises and basic speakability; when it
detects a recognized risk, it substitutes a neutral uncertainty statement rather
than a canned intent-specific sales pitch. The WebSocket `recommendation.ready`
event includes `response_origin`: `ai_generated`, `safety_fallback`, or
`offline_demo`. The React dashboard displays this next to the suggestion.
`quality_corrected` indicates a safety substitution. Both mechanisms are
heuristic; neither proves factual grounding. Offline mode is explicitly a
deterministic demonstration, not LLM inference.

For interview evaluation, test several unseen customer questions and record
the answer, its response origin, relevant evidence, and measured latency.
If an unsafe output triggers a fallback, explain why; do not present it as
proof that Qwen authored that particular sentence.

## Labeled model-quality evaluation

After starting Ollama and installing dependencies, run from `backend/`:

```bash
python -m scripts.evaluate_scenarios
```

This runs eight unseen customer questions through the **actual** embedding + FAISS + Qwen + validation pipeline. It prints predicted versus expected intent, response provenance, timings, source IDs and generated text. Intent agreement is only a diagnostic; manually review each answer for speakability and factual grounding. This is not a production-grade benchmark or a claim that RAG alone prevents hallucinations.

The latest Qwen system prompt defines intent categories, emphasizes the latest customer turn, distinguishes reminders from automated lead scoring, and requests direct spoken responses rather than internal SDR instructions. Normal model output is preserved unless a targeted guardrail is triggered.

## Evidence-aware recommendation architecture (interview MVP)

The model receives the latest customer question as a **separate prompt field** from
prior conversation history. After Qwen generates its structured recommendation,
the server validates recognizable high-risk claims against documented product
capabilities in `app/evidence.py`. The evidence gate is shared by the live
WebSocket and the evaluation script; rejected outputs become neutral,
clearly labeled `safety_fallback` responses. Supported claims such as lead
follow-up reminders can pass unchanged.

This architecture intentionally separates generative language from factual
policy enforcement. The current evidence validator is **not** a general-purpose
entailment model: it has narrowly scoped capability families based on known
FlowDesk documentation, and may miss novel unsupported claims. Production work
would require document ingestion with structured facts, source-level entailment
checking, permission-aware tenant retrieval, independent evaluation and
monitoring. No microphone streaming or production deployment is included.

To verify: `cd backend && python -m pytest -q && python -m scripts.evaluate_scenarios`.
Check intent agreement, evidence flags, response origin and *manual* answer quality.
Do not treat a high intent agreement or fewer fallbacks as proof of grounding.

## Interview demo: actionable recovery (October 2026)

Normal suggestions still come from Qwen3. If a suggestion conflicts with verified
FlowDesk capabilities, repeats the customer question, or misses an explicit
latest-customer intent, the shared `app/pipeline.py` substitutes a **topic-specific
document-backed recovery**. This is transparently labeled `verified_recovery` in
the WebSocket and UI; it is **not** claimed to be an LLM-generated response.
This replaces the former repeated generic safety sentence. Qwen remains the
generative engine for normal replies.

Use `python -m pytest -q` and `python -m scripts.evaluate_scenarios` in
`backend/`. The scenario runner uses the same finalization as the app. Inspect
`origin` to distinguish actual model output from deterministic recovery.

This is an interview MVP. Recovery covers the fictional product's tested
capabilities, not arbitrary future features. A production design would replace
these case-specific recovery messages with a verified product capability store,
retrieval-backed claim verification and grounded regeneration.

## Raw Qwen interview evaluation mode (latest)

The **live Ollama/OpenAI WebSocket** now sends the generated structured
recommendation unchanged (except filtering source IDs to retrieved documents).
There is **no fallback substitution**, safety recovery, intent rewriting,
or claim-based response blocking in the live AI path. The evaluation runner
also reports the model's exact recommendation. The dashboard labels these
answers `Raw AI output · Unverified`.

This is intentionally an **evaluation-only behavior**. The model can make
incorrect, misleading or unsupported claims; never present its wording to a
customer without review. The older `quality.py`, `evidence.py`,
`pipeline.py` and `recovery.py` remain in the repository for historical
tests but **are not called by the live AI or evaluation routes**. The
`offline-demo` provider is still a separate deterministic mode; set
`AI_PROVIDER=ollama` to evaluate genuine local Qwen inference.

## Submission quick-start (raw AI output)

Use Ollama locally with `qwen3:4b` and `embeddinggemma`. The
submission build uses a concise task-focused prompt, retrieves product
documentation via FAISS, and displays **unverified raw Qwen output** without
fallback substitution. Do not present model claims as verified product facts.

From `backend/`:
```bash
python -m pytest -q
python -m scripts.evaluate_scenarios
python -m scripts.compare_models
```
The comparison script runs the same eight scenarios with the same retrieval
index on installed `qwen3:4b` and `qwen3:1.7b` models, prints actual outputs,
intent agreement and inference timing. To install the optional second model,
run `ollama pull qwen3:1.7b`. A model that gives the fastest responses is
not necessarily the most accurate; manually compare capability claims.
The app defaults to `OLLAMA_CHAT_MODEL=qwen3:4b` if unset.
