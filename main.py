from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from core.entities import AttendanceReport, ReportType
from generators.html_renderer import HtmlRenderer
from generators.pdf_generator import PdfRenderer
from interfaces.renderer import BaseRenderer
from interfaces.strategy import BaseTransformationStrategy
from parsers.factory import ParserFactory
from services.classifier import KeywordLayoutClassifier
from services.decorators import ValidatingStrategyDecorator
from services.ocr_service import TesseractPyMuPDFOCRService
from services.strategies import TypeATransformationStrategy, TypeBTransformationStrategy
from services.transformation_service import TransformationService


# ---------------------------------------------------------------------------
# Registry wiring
# ---------------------------------------------------------------------------

def build_registry() -> dict[ReportType, BaseTransformationStrategy]:
    """Wire the Strategy Registry: each type maps to a *decorated* strategy.

    ValidatingStrategyDecorator wraps every concrete strategy so each
    transformed row is audited for business-rule compliance.  The
    TransformationService never knows concrete types – only the interface.
    """
    return {
        ReportType.TYPE_A: ValidatingStrategyDecorator(TypeATransformationStrategy()),
        ReportType.TYPE_B: ValidatingStrategyDecorator(TypeBTransformationStrategy()),
    }


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
    p.add_argument("--output-format", choices=["pdf", "html"], default="pdf")
    p.add_argument("--log-level", default="INFO")
    return p


def _resolve_output_path(args: argparse.Namespace) -> str:
    if args.output_file:
        return args.output_file
    stem = Path(args.input_pdf).stem
    ext = "html" if args.output_format == "html" else "pdf"
    out_dir = Path(args.output_dir) if args.output_dir else Path("real_reports_output")
    return str(out_dir / f"{stem}_varied.{ext}")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    input_pdf: str,
    output_path: str,
    seed: int | str,
    ocr_lang: str,
    tesseract_cmd: str | None,
    renderer: BaseRenderer,
) -> None:
    """Load → OCR → Classify → Parse → Transform (Registry+Decorator) → Render."""

    logging.info("Step 1/6  Load file")
    source = Path(input_pdf)
    if not source.exists():
        raise FileNotFoundError(f"Input PDF not found: {source}")

    logging.info("Step 2/6  OCR extraction")
    ocr_service = TesseractPyMuPDFOCRService(ocr_lang=ocr_lang, tesseract_cmd=tesseract_cmd)
    ocr_result = ocr_service.extract(str(source))

    logging.info("Step 3/6  Classify")
    classifier = KeywordLayoutClassifier()
    report_type = classifier.classify(ocr_result)
    parser_factory = ParserFactory()

    if report_type == ReportType.UNKNOWN:
        report_type = _infer_type_from_filename(source.name)
        if report_type != ReportType.UNKNOWN:
            logging.warning("Inferred type from filename: %s", report_type.value)
        else:
            report_type = _infer_type_by_parser_success(ocr_result, parser_factory)
            if report_type != ReportType.UNKNOWN:
                logging.warning("Inferred type by parser success: %s", report_type.value)
            else:
                raise ValueError("Unable to determine report type (A/B).")

    ocr_result.metadata["layout_metadata"] = classifier.infer_layout_metadata(
        report_type=report_type, ocr_result=ocr_result
    )

    logging.info("Step 4/6  Parse  [%s]", report_type.value)
    report = _parse_with_fallback(ocr_result, parser_factory, report_type)

    logging.info("Step 5/6  Transform  [seed=%s]", seed)
    varied_report = TransformationService(registry=build_registry()).apply(report, seed)

    logging.info("Step 6/6  Render → %s", output_path)
    renderer.render(report=varied_report, source_path=str(source), output_path=output_path)


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
    renderer: BaseRenderer = HtmlRenderer() if args.output_format == "html" else PdfRenderer()

    try:
        run_pipeline(
            input_pdf=args.input_pdf,
            output_path=output_path,
            seed=args.seed,
            ocr_lang=args.ocr_lang,
            tesseract_cmd=args.tesseract_cmd,
            renderer=renderer,
        )
    except Exception as exc:
        logging.exception("Pipeline failed: %s", exc)
        return 1

    logging.info("Done → %s", output_path)
    return 0


# ---------------------------------------------------------------------------
# Fallback helpers
# ---------------------------------------------------------------------------

def _infer_type_from_filename(name: str) -> ReportType:
    lower = name.lower()
    if lower.startswith("a_") or "a_r" in lower:
        return ReportType.TYPE_A
    if lower.startswith("n_") or "n_r" in lower or lower.startswith("b_"):
        return ReportType.TYPE_B
    return ReportType.UNKNOWN


def _infer_type_by_parser_success(ocr_result, factory: ParserFactory) -> ReportType:
    best_type, best_rows = ReportType.UNKNOWN, -1
    for candidate in (ReportType.TYPE_A, ReportType.TYPE_B):
        try:
            count = len(factory.create(candidate).parse(ocr_result).rows)
            if count > best_rows:
                best_rows, best_type = count, candidate
        except Exception:
            continue
    return best_type if best_rows > 0 else ReportType.UNKNOWN


def _parse_with_fallback(ocr_result, factory: ParserFactory, primary_type: ReportType) -> AttendanceReport:
    alternates = [primary_type, ReportType.TYPE_B if primary_type == ReportType.TYPE_A else ReportType.TYPE_A]
    for rtype in alternates:
        try:
            return factory.create(rtype).parse(ocr_result)
        except Exception as exc:
            logging.warning("Parser %s failed: %s", rtype.value, exc)

    logging.warning("All parsers failed – producing empty report.")
    empty = AttendanceReport(
        report_type=primary_type if primary_type != ReportType.UNKNOWN else ReportType.TYPE_A,
        employee_name=None,
        month=None,
        rows=[],
        metadata={"layout_metadata": ocr_result.metadata.get("layout_metadata", {})},
    )
    empty.recompute_monthly_total()
    return empty


if __name__ == "__main__":
    sys.exit(main())

