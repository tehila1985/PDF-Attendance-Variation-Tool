from __future__ import annotations

from abc import ABC, abstractmethod

from core.entities import AttendanceReport


class VariationService(ABC):
    """Contract for deterministic attendance variations."""

    @abstractmethod
    def apply(self, report: AttendanceReport, seed: int | str) -> AttendanceReport:
        """Apply deterministic business variation to a report."""
        raise NotImplementedError
