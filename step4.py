"""STEP 04: minimal compress loop.
While current > target, compress chunks via GPT-4.1 starting from the
least‑relevant largest ones. Tries multiple candidates per round; stops
when none improve or target is met.
"""
from __future__ import annotations
from typing import List, Dict, Optional

def _tok(s: str) -> int:
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(s))
    except Exception:
        return len(s.split())

def _key(ch: Dict) -> tuple:
    return (ch.get("score", 5.0), -ch.get("tokens", _tok(ch.get("text",""))))

def _load_key() -> None:
    import os, pathlib
    if os.environ.get("OPENAI_API_KEY"): return
    try:
        for ln in pathlib.Path(".env").read_text(encoding="utf-8").splitlines():
            if ln.startswith("OPENAI_API_KEY="):
                os.environ["OPENAI_API_KEY"] = ln.split("=",1)[1].strip().strip('"').strip("'")
                break
    except Exception: pass

def compress_to_target(
    chunks: List[Dict], target_tokens: int, model: str = "gpt-4.1", intent: Optional[str] = None
) -> List[Dict]:
    from openai import OpenAI
    _load_key(); cli = OpenAI()
    def total(): return _tok("".join(c["text"] for c in chunks))
    cur, it = total(), 0
    print(f"[compress] starting compression loop: {cur} -> {target_tokens} tokens")
    while cur > target_tokens and it < 64:
        it += 1
        improved = False
        candidates = sorted(chunks, key=_key)
        for idx, ch in enumerate(candidates):
            t = ch["text"]; t0 = _tok(t); need = cur - target_tokens
            if t0 <= 1:  # nothing to shave
                continue
            new_tok = max(1, t0 - max(1, min(int(t0*0.3), need)))
            print(f"\r[compress] iteration {it}: trying chunk {idx+1}/{len(candidates)} ({t0} -> {new_tok} tokens)", end='', flush=True)
            sys = ("Shorten the Markdown chunk conservatively. Preserve meaning. "
                   "KEEP code fences unchanged; do not alter code. Keep headings/lists. "
                   f"Aim for <= {new_tok} tokens (roughly words). Return only the chunk.")
            if intent:
                sys += f" Author intent: {intent}"
            rsp = cli.responses.create(
                model=model,
                input=[{"role":"system","content":sys},{"role":"user","content":f"```md\n{t[:12000]}\n```"}],
                temperature=0,
                max_output_tokens=2048,
            )
            out = (getattr(rsp, "output_text", None) or "").strip() or t
            if _tok(out) < t0:
                ch["text"] = out; ch["tokens"] = _tok(out)
                cur = total()
                print(f"\r[compress] iteration {it}: compressed chunk {ch['idx']} ({t0} -> {_tok(out)} tokens, total: {cur})" + " "*20)
                improved = True
                break
        if not improved:
            print(f"\n[compress] no more improvements possible at iteration {it}")
            break
    print(f"[compress] finished: {cur} tokens (target was {target_tokens})")
    return chunks

__all__ = ["compress_to_target"]
