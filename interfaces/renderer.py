from __future__ import annotations

from abc import ABC, abstractmethod

from core.entities import AttendanceReport


class BaseRenderer(ABC):
    """Contract for rendering an attendance report to an output file.

    Implementations choose their own output format (PDF, HTML, etc.)
    without the caller needing to know concrete types.
    """

    @abstractmethod
    def render(self, report: AttendanceReport, source_path: str, output_path: str) -> None:
        """Write the varied report to *output_path* mirroring the source layout."""
        raise NotImplementedError
