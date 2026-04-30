from __future__ import annotations

import logging
import random
from datetime import datetime

from core.entities import AttendanceRow, hhmm_to_minutes, parse_time
from interfaces.strategy import BaseTransformationStrategy


class TransformationError(Exception):
    """Raised when a transformed row fails domain-level audit constraints."""


class ValidatingStrategyDecorator(BaseTransformationStrategy):
    """Decorator that wraps any BaseTransformationStrategy with an audit step.

    After the inner strategy produces a new row, this decorator checks:
    - exit_time > entry_time
    - total_hours is within a reasonable upper bound (MAX_REASONABLE_HOURS)

    On audit failure a ``TransformationError`` is raised.  The
    ``TransformationService`` catches that exception and falls back to the
    original (pre-transformation) row, ensuring the pipeline never crashes.
    """

    MAX_REASONABLE_HOURS: int = 14 * 60  # 14 h in minutes

    def __init__(self, inner: BaseTransformationStrategy) -> None:
        self._inner = inner

    def transform(self, row: AttendanceRow, rng: random.Random) -> AttendanceRow:
        result = self._inner.transform(row, rng)
        self._audit(result)
        return result

    def _audit(self, row: AttendanceRow) -> None:
        """Raise TransformationError if the row violates business constraints."""
        start_t = parse_time(row.start_time)
        end_t = parse_time(row.end_time)

        if start_t and end_t:
            start_dt = datetime.combine(datetime.today(), start_t)
            end_dt = datetime.combine(datetime.today(), end_t)
            if end_dt <= start_dt:
                raise TransformationError(
                    f"Audit failed: exit {row.end_time!r} <= entry {row.start_time!r}"
                )

        total = hhmm_to_minutes(row.total_hours)
        if total is not None and total > self.MAX_REASONABLE_HOURS:
            raise TransformationError(
                f"Audit failed: total_hours {row.total_hours!r} exceeds "
                f"{self.MAX_REASONABLE_HOURS // 60}h maximum"
            )
        logging.debug(
            "Audit passed: entry=%s exit=%s total=%s",
            row.start_time,
            row.end_time,
            row.total_hours,
        )
