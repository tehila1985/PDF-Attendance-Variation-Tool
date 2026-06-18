from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class PipelineEventType(str, Enum):
    PIPELINE_STARTED = "pipeline_started"
    STEP_COMPLETED = "step_completed"
    ROW_TRANSFORMED = "row_transformed"
    PIPELINE_FINISHED = "pipeline_finished"
    PIPELINE_FAILED = "pipeline_failed"


@dataclass(slots=True)
class PipelineEvent:
    event_type: PipelineEventType
    step: str | None = None
    message: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


class PipelineObserver(Protocol):
    def on_event(self, event: PipelineEvent) -> None:
        ...


class PipelineEventHub:
    """Subject that publishes pipeline events to subscribed observers."""

    def __init__(self) -> None:
        self._observers: list[PipelineObserver] = []

    def subscribe(self, observer: PipelineObserver) -> None:
        self._observers.append(observer)

    def publish(self, event: PipelineEvent) -> None:
        for observer in self._observers:
            observer.on_event(event)


class LoggingPipelineObserver:
    """Observer that turns pipeline events into structured logs."""

    def on_event(self, event: PipelineEvent) -> None:
        if event.event_type == PipelineEventType.PIPELINE_FAILED:
            logging.error("Pipeline event [%s]: %s | %s", event.event_type, event.step, event.message)
            return

        level = logging.DEBUG if event.event_type == PipelineEventType.ROW_TRANSFORMED else logging.INFO
        logging.log(level, "Pipeline event [%s]: %s | %s", event.event_type, event.step, event.message)


class MetricsPipelineObserver:
    """Simple in-memory metrics observer useful for tests and diagnostics."""

    def __init__(self) -> None:
        self.counters: dict[PipelineEventType, int] = {}

    def on_event(self, event: PipelineEvent) -> None:
        self.counters[event.event_type] = self.counters.get(event.event_type, 0) + 1
