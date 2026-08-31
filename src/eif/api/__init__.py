"""Optional FastAPI service for EIF."""

from __future__ import annotations

__all__ = ["app", "create_app", "get_eif"]


def __getattr__(name: str):
    if name in __all__:
        from . import app as _app_module

        return getattr(_app_module, name)
    raise AttributeError(name)
