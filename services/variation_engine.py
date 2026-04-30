"""Backward-compatible shim.

New code should import TransformationService directly from
``services.transformation_service``.  This module keeps
``DeterministicVariationService`` as an alias so existing tests and
scripts keep working without modification.
"""
from __future__ import annotations

from core.entities import ReportType
from services.decorators import ValidatingStrategyDecorator
from services.strategies import TypeATransformationStrategy, TypeBTransformationStrategy
from services.transformation_service import TransformationService


def _default_registry():
    return {
        ReportType.TYPE_A: ValidatingStrategyDecorator(TypeATransformationStrategy()),
        ReportType.TYPE_B: ValidatingStrategyDecorator(TypeBTransformationStrategy()),
    }


class DeterministicVariationService(TransformationService):
    """Convenience subclass with a pre-wired default Registry.

    Equivalent to instantiating TransformationService with the standard
    decorated strategies for TYPE_A and TYPE_B.
    """

    def __init__(self) -> None:
        super().__init__(registry=_default_registry())


__all__ = ["DeterministicVariationService"]

