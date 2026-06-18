from __future__ import annotations

import re


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def recursive_character_splitter(
    text: str,
    chunk_size: int = 700,
    chunk_overlap: int = 100,
    separators: list[str] | None = None,
) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    separators = separators or ["\n\n", "\n", "。", "！", "？", ". ", " ", ""]

    def split_with_separator(value: str, remaining: list[str]) -> list[str]:
        if len(value) <= chunk_size:
            return [value]
        separator = remaining[0]
        next_separators = remaining[1:]
        if separator == "":
            step = chunk_size - chunk_overlap
            return [value[i : i + chunk_size] for i in range(0, len(value), step)]

        parts = value.split(separator)
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for part in parts:
            part_len = len(part) + len(separator)
            if current and current_len + part_len > chunk_size:
                candidate = separator.join(current).strip()
                if len(candidate) > chunk_size and next_separators:
                    chunks.extend(split_with_separator(candidate, next_separators))
                elif candidate:
                    chunks.append(candidate)

                overlap_text = candidate[-chunk_overlap:] if chunk_overlap else ""
                current = [overlap_text, part] if overlap_text else [part]
                current_len = len(overlap_text) + part_len
            else:
                current.append(part)
                current_len += part_len

        candidate = separator.join(current).strip()
        if candidate:
            if len(candidate) > chunk_size and next_separators:
                chunks.extend(split_with_separator(candidate, next_separators))
            else:
                chunks.append(candidate)
        return chunks

    return [chunk for chunk in split_with_separator(text, separators) if chunk.strip()]

