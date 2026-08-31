"""A tiny, generic, thread-safe registry used for all open vocabularies.

Event types, entity types, and metrics are *open* vocabularies: users must be
able to add their own without patching the framework. Each is backed by an
instance of :class:`Registry`. Definitions are Pydantic models (see the sibling
modules) so they validate and serialize like everything else.
"""

from __future__ import annotations

import threading
from collections.abc import Iterable, Iterator
from typing import Generic, Protocol, TypeVar, runtime_checkable

from ..exceptions import RegistryError


@runtime_checkable
class HasKey(Protocol):
    key: str


T = TypeVar("T", bound=HasKey)


class Registry(Generic[T]):
    """A name-to-definition registry with register/get/list semantics."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._items: dict[str, T] = {}
        self._lock = threading.RLock()

    def register(self, item: T, *, overwrite: bool = False) -> T:
        with self._lock:
            if item.key in self._items and not overwrite:
                raise RegistryError(
                    f"{self._name}: key '{item.key}' already registered "
                    f"(pass overwrite=True to replace)."
                )
            self._items[item.key] = item
            return item

    def register_many(self, items: Iterable[T], *, overwrite: bool = False) -> None:
        for item in items:
            self.register(item, overwrite=overwrite)

    def get(self, key: str) -> T:
        with self._lock:
            try:
                return self._items[key]
            except KeyError as exc:
                raise RegistryError(f"{self._name}: unknown key '{key}'.") from exc

    def try_get(self, key: str) -> T | None:
        with self._lock:
            return self._items.get(key)

    def has(self, key: str) -> bool:
        with self._lock:
            return key in self._items

    def keys(self) -> list[str]:
        with self._lock:
            return sorted(self._items)

    def all(self) -> list[T]:
        with self._lock:
            return [self._items[k] for k in sorted(self._items)]

    def __iter__(self) -> Iterator[T]:
        return iter(self.all())

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)
