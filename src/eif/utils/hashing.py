"""Content hashing helpers used for provenance and de-duplication."""

from __future__ import annotations

import hashlib
from pathlib import Path


def hash_bytes(data: bytes, *, algo: str = "sha256") -> str:
    """Return ``algo:hexdigest`` for ``data``."""
    h = hashlib.new(algo)
    h.update(data)
    return f"{algo}:{h.hexdigest()}"


def hash_text(text: str, *, algo: str = "sha256") -> str:
    """Return ``algo:hexdigest`` for the UTF-8 encoding of ``text``."""
    return hash_bytes(text.encode("utf-8"), algo=algo)


def hash_file(path: str | Path, *, algo: str = "sha256", chunk_size: int = 1 << 20) -> str:
    """Stream ``path`` and return ``algo:hexdigest`` without loading it fully."""
    h = hashlib.new(algo)
    with Path(path).open("rb") as fh:
        while chunk := fh.read(chunk_size):
            h.update(chunk)
    return f"{algo}:{h.hexdigest()}"
