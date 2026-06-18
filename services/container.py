from __future__ import annotations

from dataclasses import dataclass
from services.classifier import KeywordLayoutClassifier
from services.factories import ParserFactory, RendererFactory, TransformationStrategyFactory
from services.observer import PipelineEventHub, LoggingPipelineObserver
from services.ocr_service import TesseractPyMuPDFOCRService
from services.transformation_service import TransformationService


@dataclass(frozen=True)
class AppContainer:
    ocr_service: TesseractPyMuPDFOCRService
    classifier: KeywordLayoutClassifier
    parser_factory: ParserFactory
    transformation_service: TransformationService
    renderer_factory: RendererFactory
    event_hub: PipelineEventHub

    @classmethod
    def create(cls, ocr_lang: str = "heb+eng", tesseract_cmd: str | None = None) -> "AppContainer":
        event_hub = PipelineEventHub()
        event_hub.subscribe(LoggingPipelineObserver())

        ocr_service = TesseractPyMuPDFOCRService(ocr_lang=ocr_lang, tesseract_cmd=tesseract_cmd)
        classifier = KeywordLayoutClassifier()
        parser_factory = ParserFactory()
        strategy_factory = TransformationStrategyFactory()
        transformation_service = TransformationService(strategy_factory=strategy_factory, event_hub=event_hub)
        renderer_factory = RendererFactory()

        return cls(
            ocr_service=ocr_service,
            classifier=classifier,
            parser_factory=parser_factory,
            transformation_service=transformation_service,
            renderer_factory=renderer_factory,
            event_hub=event_hub,
        )

    def build_renderer(self, output_format: str):
        return self.renderer_factory.get_renderer(output_format)
