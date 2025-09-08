"""STEP 02: minimal relevance rating with GPT-4.1 (async).
- Loads OPENAI_API_KEY from .env if needed.
- Rates all chunks concurrently and adds a 'score' (0..10).
- Accepts an optional 'intent' string to anchor ratings.
"""
from __future__ import annotations

import os, re, pathlib
from typing import List, Dict, Optional
import asyncio


def _load_key() -> None:
    if os.environ.get("OPENAI_API_KEY"):
        return
    try:
        for line in pathlib.Path(".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("OPENAI_API_KEY="):
                os.environ["OPENAI_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    except Exception:
        pass


async def rate_chunks_async(
    chunks: List[Dict], model: str = "gpt-4.1", concurrency: int = 8, intent: Optional[str] = None
) -> List[Dict]:
    """Async rating of chunks; mutates and returns input list."""
    _load_key()
    from openai import AsyncOpenAI  # lazy import
    client = AsyncOpenAI()
    sys = (
        "Rate how critical this chunk is to preserve author intent. "
        "Return only a number 0-10 (float allowed). Higher = more critical."
    ) + (f" Author intent: {intent}" if intent else "")
    print(f"[rater] rating {len(chunks)} chunks with {model} (async, {concurrency} workers)")
    sem = asyncio.Semaphore(concurrency)
    done = 0

    async def one(ch: Dict) -> None:
        nonlocal done
        async with sem:
            rsp = await client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": sys},
                    {"role": "user", "content": f"```md\n{ch['text'][:12000]}\n```"},
                ],
                max_output_tokens=200,
                temperature=0,
            )
            out = (getattr(rsp, "output_text", None) or "").strip()
            m = re.search(r"\d+(?:\.\d+)?", out)
            ch["score"] = float(m.group(0)) if m else 5.0
            done += 1
            bar = '#' * (done * 20 // len(chunks)) + '-' * (20 - done * 20 // len(chunks))
            print(f"\r[rater] [{bar}] {done}/{len(chunks)} chunks", end='', flush=True)

    await asyncio.gather(*(one(ch) for ch in chunks))
    print("\r[rater] done rating" + " " * 40)
    return chunks


def rate_chunks(chunks: List[Dict], model: str = "gpt-4.1", intent: Optional[str] = None) -> List[Dict]:
    """Sync wrapper for convenience in small scripts (demo.py)."""
    return asyncio.run(rate_chunks_async(chunks, model=model, intent=intent))


__all__ = ["rate_chunks", "rate_chunks_async"]
