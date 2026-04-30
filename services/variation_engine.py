"""Backward-compatible shim.

New code should import TransformationService directly from
``services.transformation_service``.  This module keeps
``DeterministicVariationService`` as an alias so existing tests and
scripts keep working without modification.
"""
from __future__ import annotations

from core.entities import ReportType
from services.factories import TransformationStrategyFactory
from services.transformation_service import TransformationService


def _default_strategy_factory() -> TransformationStrategyFactory:
    return TransformationStrategyFactory()


class DeterministicVariationService(TransformationService):
    """Convenience subclass with a pre-wired default strategy factory."""

    def __init__(self) -> None:
        super().__init__(strategy_factory=_default_strategy_factory())


__all__ = ["DeterministicVariationService"]

