"""STEP 01: minimal Markdown-aware chunking.
- Detect headings, fenced code, list items, paragraphs.
- Never split inside code fences or a list item.
- Return chunks with stable IDs and simple token counts.
"""

from __future__ import annotations

import hashlib, re
from typing import List, Dict

HEADING = re.compile(r"^(#{1,6})\s+.+$")
FENCE = re.compile(r"^```.*$")
LIST = re.compile(r"^\s{0,3}(?:[-*+]\s+|\d{1,9}[.)]\s+)")


def _tok_count(s: str) -> int:
    return len(s.split())


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


def split(text: str) -> List[Dict]:
    # Show both character and token counts up front
    try:
        import tiktoken
        tok_total = len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        tok_total = len(text.split())
    print(f"[compressor] splitting text: {len(text)} chars, {tok_total} tokens")
    lines = text.splitlines(keepends=True)
    n, i, pos, blocks = len(lines), 0, 0, []

    def emit(kind: str, start: int, end: int):
        t = text[start:end]
        did = hashlib.sha1(_norm(t).encode()).hexdigest()[:10]
        blocks.append({
            "id": f"ch_{len(blocks):05d}_{did}",
            "idx": len(blocks),
            "start": start,
            "end": end,
            "text": t,
            "tokens": _tok_count(t),
            "kind": kind,
        })

    while i < n:
        line = lines[i]

        if FENCE.match(line):  # code block
            s = pos; i += 1; pos += len(line)
            while i < n and not FENCE.match(lines[i]):
                pos += len(lines[i]); i += 1
            if i < n:
                pos += len(lines[i]); i += 1
            emit("code", s, pos); continue

        if HEADING.match(line):  # heading line
            s = pos; i += 1; pos += len(line)
            emit("heading", s, pos); continue

        if LIST.match(line):  # one list item (with continuations until break)
            s = pos; i += 1; pos += len(line)
            while i < n:
                nxt = lines[i]
                if nxt.strip() == "" or LIST.match(nxt) or HEADING.match(nxt) or FENCE.match(nxt):
                    break
                pos += len(nxt); i += 1
            emit("list", s, pos)
            if i < n and lines[i].strip() == "":
                pos += len(lines[i]); i += 1
            continue

        if line.strip() == "":  # skip blank runs
            while i < n and lines[i].strip() == "":
                pos += len(lines[i]); i += 1
            continue

        # paragraph until blank or structural marker
        s = pos; i += 1; pos += len(line)
        while i < n:
            nxt = lines[i]
            if nxt.strip() == "" or HEADING.match(nxt) or LIST.match(nxt) or FENCE.match(nxt):
                break
            pos += len(nxt); i += 1
        emit("paragraph", s, pos)
    # Pack blocks into ~4k-8k token chunks, respecting boundaries.
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        def tok(s: str) -> int: return len(enc.encode(s))
    except Exception:
        def tok(s: str) -> int: return len(s.split())

    CH_MIN, CH_MAX = 2000, 4000
    packed: List[Dict] = []
    cur_parts: List[str] = []
    cur_start = None
    cur_end = None
    cur_tokens = 0
    cur_kind = "section"

    def flush():
        nonlocal cur_parts, cur_start, cur_end, cur_tokens, cur_kind
        if not cur_parts:
            return
        txt = "".join(cur_parts)
        did = hashlib.sha1(_norm(txt).encode()).hexdigest()[:10]
        packed.append({
            "id": f"ch_{len(packed):05d}_{did}",
            "idx": len(packed),
            "start": cur_start,
            "end": cur_end,
            "text": txt,
            "tokens": tok(txt),
            "kind": cur_kind,
        })
        cur_parts, cur_start, cur_end, cur_tokens, cur_kind = [], None, None, 0, "section"

    for b in blocks:
        btok = tok(b["text"])  # accurate token count per block
        # Oversized single block: emit alone (can't split code/list safely)
        if btok > CH_MAX and not cur_parts:
            txt = b["text"]; did = hashlib.sha1(_norm(txt).encode()).hexdigest()[:10]
            packed.append({
                "id": f"ch_{len(packed):05d}_{did}",
                "idx": len(packed),
                "start": b["start"],
                "end": b["end"],
                "text": txt,
                "tokens": btok,
                "kind": b["kind"],
            })
            continue

        if not cur_parts:
            cur_parts = [b["text"]]; cur_start, cur_end = b["start"], b["end"]
            cur_tokens = btok; cur_kind = b["kind"]
            continue

        # If adding keeps us under max, add
        if cur_tokens + btok <= CH_MAX:
            cur_parts.append(b["text"]); cur_end = b["end"]; cur_tokens += btok
            if cur_kind != b["kind"]: cur_kind = "section"
            continue

        # Adding would exceed max
        if cur_tokens >= CH_MIN:
            flush()
            # start new with current block
            cur_parts = [b["text"]]; cur_start, cur_end = b["start"], b["end"]
            cur_tokens = btok; cur_kind = b["kind"]
        else:
            # Try to merge small current chunk into previous if it fits
            if packed and (packed[-1]["tokens"] + cur_tokens) <= CH_MAX:
                # merge into previous by appending cur to last chunk
                last = packed.pop()
                merged_txt = last["text"] + "".join(cur_parts)
                did = hashlib.sha1(_norm(merged_txt).encode()).hexdigest()[:10]
                packed.append({
                    "id": f"ch_{len(packed):05d}_{did}",
                    "idx": len(packed),
                    "start": last["start"],
                    "end": cur_end,
                    "text": merged_txt,
                    "tokens": tok(merged_txt),
                    "kind": "section",
                })
                # start new with block
                cur_parts = [b["text"]]; cur_start, cur_end = b["start"], b["end"]
                cur_tokens = btok; cur_kind = b["kind"]
            else:
                # Flush small chunk (may be < CH_MIN), start new
                flush()
                cur_parts = [b["text"]]; cur_start, cur_end = b["start"], b["end"]
                cur_tokens = btok; cur_kind = b["kind"]

    # Flush last chunk; if too small and can merge into previous, do it
    if cur_parts:
        if packed and (tok(packed[-1]["text"]) + cur_tokens) <= CH_MAX and cur_tokens < CH_MIN:
            last = packed.pop()
            merged_txt = last["text"] + "".join(cur_parts)
            did = hashlib.sha1(_norm(merged_txt).encode()).hexdigest()[:10]
            packed.append({
                "id": f"ch_{len(packed):05d}_{did}",
                "idx": len(packed),
                "start": last["start"],
                "end": cur_end,
                "text": merged_txt,
                "tokens": tok(merged_txt),
                "kind": "section",
            })
        else:
            flush()

    print(f"[compressor] produced {len(packed)} chunks (~{CH_MIN}-{CH_MAX} toks)")
    return packed


def recount(chunks: List[Dict]) -> int:
    """STEP 05: recompute per-chunk tokens and return total.
    Uses tiktoken if available, else falls back to words.
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        def _tok(s: str) -> int: return len(enc.encode(s))
    except Exception:
        def _tok(s: str) -> int: return len(s.split())
    total = 0
    for c in chunks:
        c["tokens"] = _tok(c.get("text", ""))
        total += c["tokens"]
    return total


def sort_candidates(chunks: List[Dict]) -> List[Dict]:
    """Sort by relevance asc, then size desc (least-relevant largest first)."""
    return sorted(chunks, key=lambda c: (c.get("score", 5.0), -c.get("tokens", 0)))


def plan(chunks: List[Dict], reduce_by: float) -> Dict:
    cur = recount(chunks)
    tgt = max(0, int(cur * (1.0 - reduce_by)))
    return {"current": cur, "target": tgt, "reduce_by": reduce_by}


__all__ = ["split", "recount", "sort_candidates", "plan"]
