"""Chunking for mixed content: structured CV sections and free-form notes.

Strategy (deliberately simple, no NLP/tokenizer dependency):
  1. Split on blank-line boundaries into paragraphs.
  2. Merge a short header-like paragraph (an ALL CAPS / Title Case / markdown "#"
     line) into the paragraph that follows it, so section headers never end up
     alone in their own chunk — this is what makes the strategy work for both
     structured CV sections ("EXPERIENCE\n\n...") and free-form notes (no
     headers at all, just paragraphs).
  3. Greedily pack paragraphs into chunks up to a target size.
  4. A paragraph that's too long on its own (e.g. one long free-form note) is
     split with a sliding word-boundary window instead of packed whole.
  5. Every chunk after the first is prefixed with the tail of the previous
     chunk, so retrieval never loses context sitting right at a chunk boundary.

Chunk/overlap sizes are expressed in "tokens" via a fixed chars-per-token
heuristic — good enough for sizing chunks, not a substitute for a real
tokenizer/billing count.
"""

import re
from dataclasses import dataclass

TARGET_TOKENS = 400
OVERLAP_TOKENS = 60
_CHARS_PER_TOKEN = 4

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")
_HEADER_MAX_CHARS = 80
_HEADER_TERMINAL_PUNCTUATION = ".!?;:,"


@dataclass
class Chunk:
    index: int
    content: str
    token_count: int


def chunk_text(
    content: str,
    *,
    target_tokens: int = TARGET_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[Chunk]:
    content = content.strip() if content else ""
    if not content:
        return []

    target_chars = target_tokens * _CHARS_PER_TOKEN
    overlap_chars = overlap_tokens * _CHARS_PER_TOKEN

    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT_RE.split(content) if p.strip()]
    if not paragraphs:
        return []

    units = _merge_headers(paragraphs)
    expanded_units = [
        sub_unit
        for unit in units
        for sub_unit in (
            _split_long_unit(unit, target_chars, overlap_chars) if len(unit) > target_chars else [unit]
        )
    ]

    raw_chunks = _pack_units(expanded_units, target_chars)
    chunks = _apply_overlap(raw_chunks, overlap_chars)

    return [
        Chunk(index=i, content=text, token_count=max(1, len(text) // _CHARS_PER_TOKEN))
        for i, text in enumerate(chunks)
    ]


def _is_header_like(paragraph: str) -> bool:
    if "\n" in paragraph:
        return False
    text = paragraph.strip()
    if not text or len(text) >= _HEADER_MAX_CHARS:
        return False
    if text[-1] in _HEADER_TERMINAL_PUNCTUATION:
        return False
    if text.startswith("#"):
        return True

    letters = [c for c in text if c.isalpha()]
    if letters and all(c.isupper() for c in letters):
        return True

    words = text.split()
    if not words:
        return False
    capitalized_ratio = sum(1 for w in words if w[0].isupper()) / len(words)
    return capitalized_ratio >= 0.6


def _merge_headers(paragraphs: list[str]) -> list[str]:
    units: list[str] = []
    i = 0
    n = len(paragraphs)
    while i < n:
        if _is_header_like(paragraphs[i]) and i + 1 < n:
            units.append(f"{paragraphs[i]}\n\n{paragraphs[i + 1]}")
            i += 2
        else:
            units.append(paragraphs[i])
            i += 1
    return units


def _split_long_unit(unit: str, target_chars: int, overlap_chars: int) -> list[str]:
    words = unit.split()
    if not words:
        return []

    windows: list[str] = []
    start = 0
    n = len(words)
    while start < n:
        length = 0
        end = start
        while end < n and (length + len(words[end]) + (1 if length else 0)) <= target_chars:
            length += len(words[end]) + (1 if length else 0)
            end += 1
        if end == start:
            end = start + 1  # a single word longer than target_chars: take it anyway

        windows.append(" ".join(words[start:end]))
        if end >= n:
            break

        back_idx = end
        back_len = 0
        while back_idx > start and back_len < overlap_chars:
            back_idx -= 1
            back_len += len(words[back_idx]) + 1
        start = max(back_idx, start + 1)  # always make forward progress

    return windows


def _pack_units(units: list[str], target_chars: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}" if current else unit
        if not current or len(candidate) <= target_chars:
            current = candidate
        else:
            chunks.append(current)
            current = unit
    if current:
        chunks.append(current)
    return chunks


def _apply_overlap(raw_chunks: list[str], overlap_chars: int) -> list[str]:
    if len(raw_chunks) <= 1:
        return raw_chunks

    result = [raw_chunks[0]]
    for i in range(1, len(raw_chunks)):
        tail = _tail(raw_chunks[i - 1], overlap_chars)
        current = raw_chunks[i]
        if tail and not current.startswith(tail):
            current = f"{tail}\n\n{current}"
        result.append(current)
    return result


def _tail(text: str, n_chars: int) -> str:
    if n_chars <= 0 or not text:
        return ""
    if len(text) <= n_chars:
        return text.strip()
    tail = text[-n_chars:]
    space_idx = tail.find(" ")
    if 0 <= space_idx < len(tail) - 1:
        tail = tail[space_idx + 1 :]
    return tail.strip()
