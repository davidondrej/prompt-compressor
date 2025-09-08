# Prompt Compressor

A minimal, end-to-end tool to compress very long Markdown prompts by a target percentage while preserving intent and structure. It uses a split → rate → plan → compress → recount → stitch loop with GPT‑4.1.

## Features
- Markdown-aware chunking (headings, lists, fenced code) with 2k–4k token chunks.
- Relevance scoring per chunk with GPT‑4.1 (async, parallel), guided by your stated intent.
- Iterative compression targeting global token budget; preserves code fences/structure.
- Simple observability and a final JSON summary.

## Requirements
- Python 3.8+
- `openai>=1.35.0`, `tiktoken>=0.5.2`
- `.env` with `OPENAI_API_KEY=...` (access to model `gpt-4.1`).

## Setup
- Install deps: `pip install -r requirements.txt`
- Create `.env` in repo root:
  - `OPENAI_API_KEY=sk-...`

## Full Pipeline (Steps 1–6)
Run all steps on a file (defaults to `original-prompt.md`):

- `python main.py [path]`

You’ll be prompted for:
- Author intent/focus (one line)
- Desired reduction (e.g., `0.30` or `30%`)

Outputs:
- `<input>.compressed.md`
- JSON summary (original/target/final tokens) to stdout

## Quick Peek (Steps 1–3 only)
- `python demo.py [path]`
- Shows chunking + relevance summary without compressing.

## How It Works
- Step 1 — Chunking (`compressor.py: split`): packs Markdown blocks into ~2k–4k token chunks, never splitting code fences or list items.
- Step 2 — Rating (`rater.py: rate_chunks`): async GPT‑4.1 scoring 0–10 for importance, using your intent.
- Step 3 — Target (`compressor.py: plan`): computes original/target tokens from desired reduction.
- Step 4 — Compression (`step4.py: compress_to_target`): shortens least‑relevant largest chunks until the target is met or no progress.
- Step 5 — Recount (`compressor.py: recount`): recomputes per‑chunk tokens to steer the loop.
- Step 6 — Stitch & Stats (`main.py`): reassembles in order, writes output, prints summary.

## Project Structure
- `main.py` — Orchestrates the full pipeline
- `demo.py` — Steps 1–3 summary
- `compressor.py` — Split/plan/recount and small helpers
- `rater.py` — Async relevance scoring (Responses API)
- `step4.py` — Iterative compression loop
- `build-idea.md` — Problem and refined 6‑step plan
- `original-prompt.md` — Example input
- `previous_attempts/` — Prior approaches to avoid
- `requirements.txt`, `LICENSE`

## Configuration
- Chunk size: edit `compressor.py` constants `CH_MIN, CH_MAX` (default `2000, 4000`).
- Model: change the `model` argument in `rater.rate_chunks` and `step4.compress_to_target`.
- Concurrency: adjust semaphore limit in `rater.rate_chunks_async` (default 8).

## Troubleshooting
- 400 BadRequest (tokens): keep `openai>=1.35.0` and ensure model access; we request `max_output_tokens` ≥ 200.
- Rate limits: reduce concurrency in `rater.py`.
- Token accuracy: install `tiktoken`; otherwise word counts are used as fallback.
- Missing key: ensure `.env` contains `OPENAI_API_KEY`.

## Cost Note
Large inputs mean many API calls (rating + compression). Monitor usage.

## License
MIT — see `LICENSE`.

