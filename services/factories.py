from __future__ import annotations

from typing import Callable

from core.entities import ReportType
from generators.html_renderer import HtmlRenderer
from generators.json_renderer import JsonRenderer
from generators.pdf_generator import PdfRenderer
from interfaces.parser import ReportParser
from interfaces.renderer import BaseRenderer
from interfaces.strategy import BaseTransformationStrategy
from parsers.factory import ParserFactory as ParserStrategyFactory
from services.decorators import ValidatingStrategyDecorator
from services.registry import Registry
from services.strategies import TypeATransformationStrategy, TypeBTransformationStrategy


class ParserFactory:
    """Service-level adapter for parser strategy selection."""

    def __init__(self) -> None:
        self._inner = ParserStrategyFactory()

    def get_parser(self, report_type: ReportType) -> ReportParser:
        # Unknown defaults to TYPE_A to keep the pipeline running.
        effective_type = ReportType.TYPE_A if report_type == ReportType.UNKNOWN else report_type
        return self._inner.create(effective_type)


class TransformationStrategyFactory:
    """Factory that returns decorated transformation strategies by report type."""

    def __init__(self) -> None:
        self._registry: Registry[ReportType, BaseTransformationStrategy] = Registry(default_key=ReportType.TYPE_A)
        self._registry.register(ReportType.TYPE_A, ValidatingStrategyDecorator(TypeATransformationStrategy()))
        self._registry.register(ReportType.TYPE_B, ValidatingStrategyDecorator(TypeBTransformationStrategy()))

    def get_strategy(self, report_type: ReportType) -> BaseTransformationStrategy:
        return self._registry.resolve(report_type)


class RendererFactory:
    """Factory for selecting output renderer by format key."""

    def __init__(self) -> None:
        self._registry: Registry[str, Callable[[], BaseRenderer]] = Registry(default_key="pdf")
        self._registry.register("pdf", PdfRenderer)
        self._registry.register("html", HtmlRenderer)
        self._registry.register("json", JsonRenderer)

    def get_renderer(self, output_format: str) -> BaseRenderer:
        builder = self._registry.resolve(str(output_format).lower())
        return builder()
