from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


@dataclass(slots=True)
class Registry(Generic[K, V]):
    """Generic key-value registry with optional default key fallback."""

    default_key: K | None = None
    _items: dict[K, V] = field(default_factory=dict, init=False)

    def register(self, key: K, value: V, *, overwrite: bool = False) -> None:
        if key in self._items and not overwrite:
            raise KeyError(f"Registry key already exists: {key!r}")
        self._items[key] = value

    def resolve(self, key: K, *, fallback_key: K | None = None) -> V:
        if key in self._items:
            return self._items[key]

        effective_fallback = fallback_key if fallback_key is not None else self.default_key
        if effective_fallback is not None and effective_fallback in self._items:
            return self._items[effective_fallback]

        raise KeyError(f"No registry entry for key {key!r}")

    def keys(self) -> tuple[K, ...]:
        return tuple(self._items.keys())
