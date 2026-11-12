"""Quote verification: a claim counts only if its quote exists in the case text."""

from __future__ import annotations

from precedent.models import Span

_QUOTE_FOLD = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})


def _normalize(text: str) -> tuple[str, list[int]]:
    """Lowercase, fold curly quotes, collapse whitespace; keep an index map back."""
    out: list[str] = []
    index: list[int] = []
    prev_space = False
    for i, ch in enumerate(text.translate(_QUOTE_FOLD)):
        if ch.isspace():
            if prev_space or not out:
                continue
            out.append(" ")
            index.append(i)
            prev_space = True
        else:
            out.append(ch.lower())
            index.append(i)
            prev_space = False
    return "".join(out), index


def find_quote(text: str, quote: str | None) -> Span | None:
    """Locate ``quote`` in ``text``; tolerant to case and whitespace only."""
    if not quote or not quote.strip():
        return None
    q = quote.strip().strip('"').strip()
    if len(q) < 3:
        return None
    pos = text.find(q)
    if pos >= 0:
        return Span(start=pos, end=pos + len(q), text=q)
    norm_text, index = _normalize(text)
    norm_q, _ = _normalize(q)
    norm_q = norm_q.strip()
    pos = norm_text.find(norm_q)
    if pos < 0:
        return None
    start = index[pos]
    end = index[pos + len(norm_q) - 1] + 1
    return Span(start=start, end=end, text=text[start:end])
