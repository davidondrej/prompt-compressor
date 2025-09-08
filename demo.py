"""Tiny demo: split + rate on original-prompt.md.
Usage: python demo.py [path]
"""
import sys, json, pathlib
from compressor import split, plan as make_plan
from rater import rate_chunks

p = sys.argv[1] if len(sys.argv) > 1 else "original-prompt.md"
intent = input("Author intent/focus (one line): ").strip()
reduction_raw = input("Desired reduction (e.g., 0.30 or 30%): ").strip() or "0.30"
reduce_frac = (float(reduction_raw[:-1]) / 100.0) if reduction_raw.endswith('%') else float(reduction_raw)
text = pathlib.Path(p).read_text(encoding="utf-8")
chunks = split(text)
budget = make_plan(chunks, reduce_by=reduce_frac)
print(f"[demo] tokens: original {budget['current']} -> target {budget['target']} ({int(reduce_frac*100)}%)")
chunks = rate_chunks(chunks, intent=intent or None)
cands = sorted(chunks, key=lambda c: (c.get("score", 5.0), -c.get("tokens", 0)))[:10]
print(json.dumps({
    "file": p,
    "chunks": len(chunks),
    "original_tokens": budget["current"],
    "target_tokens": budget["target"],
    "reduction": budget["reduce_by"],
    "top_candidates": [{k: c[k] for k in ("idx","kind","tokens","score","id")} for c in cands]
}, indent=2))
