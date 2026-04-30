from __future__ import annotations

import copy
import hashlib
import logging
import random
from typing import Protocol

from core.entities import AttendanceReport, AttendanceRow, ReportType
from interfaces.strategy import BaseTransformationStrategy
from services.decorators import TransformationError


class StrategyFactory(Protocol):
    def get_strategy(self, report_type: ReportType) -> BaseTransformationStrategy:
        ...


class TransformationService:
    """Deterministic transformation service that resolves strategies via a factory."""

    def __init__(self, strategy_factory: StrategyFactory) -> None:
        self._strategy_factory = strategy_factory

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
        return self._strategy_factory.get_strategy(report_type)

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
