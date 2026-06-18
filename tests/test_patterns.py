from __future__ import annotations

from services.factories import RendererFactory
from services.observer import MetricsPipelineObserver, PipelineEvent, PipelineEventHub, PipelineEventType
from services.registry import Registry


def test_registry_resolves_default_fallback() -> None:
    registry: Registry[str, int] = Registry(default_key="a")
    registry.register("a", 10)

    assert registry.resolve("missing") == 10


def test_observer_hub_notifies_subscribers() -> None:
    metrics = MetricsPipelineObserver()
    hub = PipelineEventHub()
    hub.subscribe(metrics)

    hub.publish(PipelineEvent(event_type=PipelineEventType.PIPELINE_STARTED, step="start", message="ok"))
    hub.publish(PipelineEvent(event_type=PipelineEventType.PIPELINE_FINISHED, step="finish", message="ok"))

    assert metrics.counters[PipelineEventType.PIPELINE_STARTED] == 1
    assert metrics.counters[PipelineEventType.PIPELINE_FINISHED] == 1


def test_renderer_factory_supports_pdf_html_and_json() -> None:
    factory = RendererFactory()

    pdf_renderer = factory.get_renderer("pdf")
    html_renderer = factory.get_renderer("html")
    json_renderer = factory.get_renderer("json")

    assert pdf_renderer.__class__.__name__ in {"PdfRenderer", "ReportLabPDFGenerator"}
    assert html_renderer.__class__.__name__ == "HtmlRenderer"
    assert json_renderer.__class__.__name__ == "JsonRenderer"
    assert callable(getattr(pdf_renderer, "render", None))
    assert callable(getattr(html_renderer, "render", None))
    assert callable(getattr(json_renderer, "render", None))


def test_appcontainer_builds_core_pipeline_components() -> None:
    from services.container import AppContainer

    container = AppContainer.create(ocr_lang="heb+eng")

    assert container.ocr_service is not None
    assert container.classifier is not None
    assert container.parser_factory is not None
    assert container.transformation_service is not None
    assert container.renderer_factory is not None
    assert container.event_hub is not None

    html_renderer = container.build_renderer("html")
    json_renderer = container.build_renderer("json")

    assert html_renderer.__class__.__name__ == "HtmlRenderer"
    assert json_renderer.__class__.__name__ == "JsonRenderer"
