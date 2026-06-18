from __future__ import annotations

import argparse
import dataclasses
import logging
import sys
from pathlib import Path

from core.entities import ReportType
from interfaces.renderer import BaseRenderer
from services.container import AppContainer
from services.observer import LoggingPipelineObserver, PipelineEvent, PipelineEventHub, PipelineEventType
from services.transformation_service import TransformationService


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Attendance Report Variation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("input_pdf", help="Path to source attendance PDF")
    p.add_argument("output_file", nargs="?", default=None, help="Output file path (overrides -o)")
    p.add_argument("-o", "--output-dir", default=None, help="Output directory; filename auto-generated")
    p.add_argument("--seed", default="42", help="Deterministic variation seed")
    p.add_argument("--ocr-lang", default="heb+eng", help="Tesseract OCR language codes")
    p.add_argument("--tesseract-cmd", default=None, help="Path to tesseract executable")
    p.add_argument("--output-format", choices=["pdf", "html", "json"], default="pdf")
    p.add_argument("--log-level", default="INFO")
    return p


def _resolve_output_path(args: argparse.Namespace) -> str:
    if args.output_file:
        return args.output_file
    stem = Path(args.input_pdf).stem
    if args.output_format == "html":
        ext = "html"
    elif args.output_format == "json":
        ext = "json"
    else:
        ext = "pdf"
    out_dir = Path(args.output_dir) if args.output_dir else Path("real_reports_output")
    return str(out_dir / f"{stem}_varied.{ext}")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    input_pdf: str,
    output_path: str,
    seed: int | str,
    renderer: BaseRenderer,
    container: AppContainer,
) -> None:
    """Load -> OCR -> Classify -> Parse -> Transform -> Render."""

    event_hub = container.event_hub
    event_hub.publish(
        PipelineEvent(
            event_type=PipelineEventType.PIPELINE_STARTED,
            step="start",
            message="Pipeline started",
            payload={"input_pdf": input_pdf, "output_path": output_path},
        )
    )

    try:
        logging.info("Step 1/6  Load file")
        source = Path(input_pdf)
        if not source.exists():
            raise FileNotFoundError(f"Input PDF not found: {source}")
        event_hub.publish(PipelineEvent(PipelineEventType.STEP_COMPLETED, step="load", message="Source loaded"))

        logging.info("Step 2/6  OCR extraction")
        ocr_result = container.ocr_service.extract(str(source))
        event_hub.publish(PipelineEvent(PipelineEventType.STEP_COMPLETED, step="ocr", message="OCR extracted"))

        logging.info("Step 3/6  Classify")
        report_type = container.classifier.classify(ocr_result)
        event_hub.publish(
            PipelineEvent(
                PipelineEventType.STEP_COMPLETED,
                step="classify",
                message=f"Classified report as {report_type.value}",
            )
        )

        parser = container.parser_factory.get_parser(report_type)
        logging.info("Step 4/6  Parse  [%s]", report_type.value)
        report = parser.parse(ocr_result)
        event_hub.publish(PipelineEvent(PipelineEventType.STEP_COMPLETED, step="parse", message="Parsed report rows"))

        effective_type = report.report_type if report.report_type != ReportType.UNKNOWN else report_type
        ocr_result = dataclasses.replace(
            ocr_result,
            metadata={**dict(ocr_result.metadata), "layout_metadata": container.classifier.infer_layout_metadata(
                report_type=effective_type,
                ocr_result=ocr_result,
            )},
        )

        logging.info("Step 5/6  Transform  [seed=%s]", seed)
        varied_report = container.transformation_service.apply(report, seed)
        event_hub.publish(PipelineEvent(PipelineEventType.STEP_COMPLETED, step="transform", message="Rows transformed"))

        logging.info("Step 6/6  Render → %s", output_path)
        renderer.render(report=varied_report, source_path=str(source), output_path=output_path)
        event_hub.publish(PipelineEvent(PipelineEventType.PIPELINE_FINISHED, step="finish", message="Pipeline finished"))
    except Exception as exc:
        event_hub.publish(
            PipelineEvent(
                event_type=PipelineEventType.PIPELINE_FAILED,
                step="error",
                message=str(exc),
            )
        )
        raise


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

def main() -> int:
    arg_parser = build_arg_parser()
    args = arg_parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    output_path = _resolve_output_path(args)
    container = AppContainer.create(ocr_lang=args.ocr_lang, tesseract_cmd=args.tesseract_cmd)
    renderer: BaseRenderer = container.build_renderer(args.output_format)

    try:
        run_pipeline(
            input_pdf=args.input_pdf,
            output_path=output_path,
            seed=args.seed,
            renderer=renderer,
            container=container,
        )
    except Exception as exc:
        logging.exception("Pipeline failed: %s", exc)
        return 1

    logging.info("Done → %s", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

