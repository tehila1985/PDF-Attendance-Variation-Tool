from __future__ import annotations

import random
from abc import ABC, abstractmethod

from core.entities import AttendanceRow


class BaseTransformationStrategy(ABC):
    """Contract for deterministic row transformation strategies.

    Each concrete strategy receives a row and a pre-seeded RNG, applies
    type-specific business logic, and returns a *new* modified row.
    The strategy must NOT mutate the original row.
    """

    @abstractmethod
    def transform(self, row: AttendanceRow, rng: random.Random) -> AttendanceRow:
        """Transform a single attendance row using the provided RNG."""
        raise NotImplementedError
