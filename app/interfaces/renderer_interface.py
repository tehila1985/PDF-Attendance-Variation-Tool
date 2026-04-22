from abc import ABC, abstractmethod

from app.entities import AttendanceReport


class BaseRenderer(ABC):
	@abstractmethod
	def render(self, report: AttendanceReport, output_path: str):
		pass
