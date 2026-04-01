from __future__ import annotations

from pathlib import Path
import re


REFERENCE_HEADERS = (
    "referencias",
    "referencias bibliograficas",
    "referencias bibliograficas",
    "referencias",
    "references",
    "bibliografia",
    "bibliography",
)


def detect_language(text: str) -> str:
    sample = text[:5000].lower()
    portuguese_markers = sum(sample.count(token) for token in (" de ", " que ", " para ", " nao ", " uma ", " com ", "cao", "coes"))
    english_markers = sum(sample.count(token) for token in (" the ", " and ", " for ", " with ", "ing ", "tion", " of "))
    return "pt-BR" if portuguese_markers >= english_markers else "en"


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_repeated_lines(text: str, min_occurrences: int = 3) -> str:
    lines = [line.strip() for line in text.splitlines()]
    counts: dict[str, int] = {}
    for line in lines:
        if line:
            counts[line] = counts.get(line, 0) + 1
    cleaned: list[str] = []
    for line in lines:
        if line and counts.get(line, 0) >= min_occurrences and len(line) < 100:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def remove_reference_section(text: str) -> str:
    lowered = text.lower()
    positions: list[int] = []
    for heading in REFERENCE_HEADERS:
        for pattern in (
            rf"(^|\n)\s*#+\s*{re.escape(heading)}\s*(\n|$)",
            rf"(^|\n)\s*{re.escape(heading)}\s*:?\s*(\n|$)",
        ):
            match = re.search(pattern, lowered)
            if match:
                positions.append(match.start())
    if not positions:
        return text
    return text[: min(positions)].rstrip()


def clean_extracted_text(text: str) -> str:
    text = normalize_whitespace(text)
    text = remove_repeated_lines(text)
    text = remove_reference_section(text)
    text = re.sub(r"\n\s*\d+\s*\n", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_title(text: str, fallback: Path | str) -> str:
    for line in text.splitlines():
        stripped = line.strip().strip("#").strip()
        if len(stripped) >= 5:
            return stripped[:180]
    if isinstance(fallback, Path):
        return fallback.stem.replace("_", " ").replace("-", " ").strip() or "Documento"
    return fallback or "Documento"


def split_blocks(text: str) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    return blocks or [text.strip()]


def chunk_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    blocks = split_blocks(text)
    chunks: list[str] = []
    current = ""
    for block in blocks:
        candidate = f"{current}\n\n{block}".strip() if current else block
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current.strip())
            overlap = current[-overlap_chars:].strip() if overlap_chars > 0 else ""
            current = f"{overlap}\n\n{block}".strip() if overlap else block
        else:
            sentences = re.split(r"(?<=[.!?])\s+", block)
            buffer = ""
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                candidate = f"{buffer} {sentence}".strip()
                if len(candidate) <= max_chars:
                    buffer = candidate
                else:
                    if buffer:
                        chunks.append(buffer)
                    overlap = buffer[-overlap_chars:].strip() if overlap_chars > 0 else ""
                    buffer = f"{overlap} {sentence}".strip() if overlap else sentence
            current = buffer
    if current:
        chunks.append(current.strip())
    return [chunk for chunk in chunks if chunk]
