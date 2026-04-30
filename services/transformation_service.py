from __future__ import annotations

import copy
import hashlib
import logging
import random

from core.entities import AttendanceReport, AttendanceRow, ReportType
from interfaces.strategy import BaseTransformationStrategy
from services.decorators import TransformationError


class TransformationService:
    """Deterministic transformation service driven by a strategy Registry.

    The Registry maps each ReportType to a strategy object.  The service
    iterates rows, builds a per-row RNG from the global seed, and delegates
    transformation to whichever strategy the Registry provides — without
    knowing the concrete type.

    If the selected strategy is wrapped in a ``ValidatingStrategyDecorator``
    and raises a ``TransformationError``, the service logs the failure and
    keeps the original row (graceful degradation).

    Registry
    --------
    Pass a ``dict[ReportType, BaseTransformationStrategy]`` at construction.
    This allows callers (main.py) to wire the Registry with decorated or bare
    strategies without changing service code.
    """

    def __init__(self, registry: dict[ReportType, BaseTransformationStrategy]) -> None:
        self._registry = registry

    def apply(self, report: AttendanceReport, seed: int | str) -> AttendanceReport:
        """Apply deterministic transformations; return a new modified report."""
        strategy = self._resolve_strategy(report.report_type)

        varied_report = copy.deepcopy(report)
        for index, row in enumerate(varied_report.rows):
            rng = self._build_rng(seed=seed, row=row, index=index)
            try:
                varied_report.rows[index] = strategy.transform(row, rng)
            except TransformationError as exc:
                logging.warning(
                    "Row %d transformation audit failed – keeping original row: %s",
                    index,
                    exc,
                )

        varied_report.recompute_monthly_total()
        return varied_report

    def _resolve_strategy(self, report_type: ReportType) -> BaseTransformationStrategy:
        strategy = self._registry.get(report_type)
        if strategy is not None:
            return strategy
        fallback = self._registry.get(ReportType.TYPE_A)
        if fallback is not None:
            logging.warning(
                "No strategy registered for %s; falling back to TYPE_A strategy.",
                report_type.value,
            )
            return fallback
        raise ValueError(
            f"No strategy for {report_type.value} and no TYPE_A fallback in registry."
        )

    @staticmethod
    def _build_rng(seed: int | str, row: AttendanceRow, index: int) -> random.Random:
        """Build a stable, row-scoped RNG from the global seed and row identity."""
        payload = "|".join(
            [
                str(seed),
                str(index),
                str(row.date),
                str(row.day),
                str(row.start_time),
                str(row.end_time),
                str(row.total_hours),
                str(row.location),
                str(row.percentage_bracket),
            ]
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return random.Random(int(digest[:16], 16))
