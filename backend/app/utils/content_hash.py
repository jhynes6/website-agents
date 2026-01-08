from __future__ import annotations

import hashlib
import re


def normalize_text(text: str) -> str:
    """
    Normalize text for stable hashing.

    Goal: detect meaningful content changes while being resilient to:
    - extra whitespace
    - line ending differences
    """
    t = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    # Collapse whitespace runs (including newlines/tabs) to single spaces.
    t = re.sub(r"\s+", " ", t)
    return t


def compute_content_hash(text: str) -> str:
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


