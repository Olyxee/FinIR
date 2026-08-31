"""FinIR command-line interface."""

from __future__ import annotations

__all__ = ["main"]


def __getattr__(name: str):
    if name == "main":
        from .main import main

        return main
    raise AttributeError(name)
