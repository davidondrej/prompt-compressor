"""End-to-end prompt compressor pipeline (Steps 1-6).

Minimal, readable integration:
- Step 1: chunk (compressor.split)
- Step 2: rate (rater.rate_chunks)
- Step 3: plan (compressor.plan)
- Step 4: compress loop (step4.compress_to_target)
- Step 5: recount (compressor.recount)
- Step 6: stitch + stats

Usage: python main.py [input_path]
"""
from __future__ import annotations

import sys, pathlib, json
from compressor import split, plan, recount
from rater import rate_chunks
from step4 import compress_to_target


def _assemble(chunks):
    # Keep original order using character positions
    return "".join(c["text"] for c in sorted(chunks, key=lambda c: c.get("start", 0)))


def main(argv):
    inp = pathlib.Path(argv[1]) if len(argv) > 1 else pathlib.Path("original-prompt.md")
    text = inp.read_text(encoding="utf-8")

    # Ask operator for intent and reduction target upfront
    intent = input("Author intent/focus (one line): ").strip() or None
    rraw = input("Desired reduction (e.g., 0.30 or 30%): ").strip() or "0.30"
    if rraw.endswith('%'):
        reduce_by = float(rraw[:-1]) / 100.0
    else:
        val = float(rraw)
        reduce_by = val / 100.0 if val > 1 else val  # treat 25 as 25%, 0.25 as 25%

    # 1) Chunk
    chunks = split(text)

    # 2) Rate (uses intent in the system prompt)
    rate_chunks(chunks, intent=intent)

    # 3) Plan budget
    budget = plan(chunks, reduce_by=reduce_by)
    print(f"[main] tokens: original {budget['current']} -> target {budget['target']} ({int(reduce_by*100)}%)")

    # 4) Compress loop until we meet the target or hit no-improvement
    compress_to_target(chunks, target_tokens=budget["target"], intent=intent)

    # 5) Recount tokens
    final_tokens = recount(chunks)

    # 6) Stitch output and write file
    out_text = _assemble(chunks)
    out_path = inp.with_suffix(".compressed.md")
    out_path.write_text(out_text, encoding="utf-8")

    print(json.dumps({
        "file": str(inp),
        "output": str(out_path),
        "original_tokens": budget["current"],
        "target_tokens": budget["target"],
        "final_tokens": final_tokens,
    }, indent=2))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

