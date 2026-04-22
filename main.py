from __future__ import annotations

import argparse
from pathlib import Path

from app.services.report_processing_service import ProcessedReportResult, ReportProcessingService


PROCESSING_SERVICE = ReportProcessingService()
DEFAULT_OUTPUT_DIR = Path("output_files")


def process_file(input_path: str | Path, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> ProcessedReportResult:
    source_path = Path(input_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Input file not found: {source_path}")
    if source_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported")

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = _next_available_output_path(target_dir / f"modified_{source_path.name}")
    return PROCESSING_SERVICE.process(str(source_path), str(output_path))


def _next_available_output_path(output_path: str | Path) -> Path:
    output_path = Path(output_path)
    base_name = output_path.with_suffix("")
    extension = output_path.suffix

    if not output_path.exists():
        return output_path

    index = 1

    while True:
        candidate = Path(f"{base_name}_{index}{extension}")
        if not candidate.exists():
            return candidate
        index += 1


def _print_result(result: ProcessedReportResult) -> None:
    report_data = result.report_data
    print(f"--- Processing: {Path(result.input_path).name} ---")
    print(f"Parsed data for: {report_data.employee_name}")
    print(f"Rows extracted: {len(report_data.rows)}")
    for idx, row in enumerate(report_data.rows[:5], start=1):
        print(
            f"  Row {idx}: date={row.date}, start={row.start_time}, end={row.end_time}, total={row.total_hours}"
        )
    print("Calculation of variations completed.")
    print(f"Success! New file saved at: {result.output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a varied attendance-report PDF from a single input PDF."
    )
    parser.add_argument("input_file", nargs="?", help="Path to the source PDF report")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where the generated PDF will be written",
    )
    args = parser.parse_args()

    if not args.input_file:
        parser.print_help()
        return 1

    try:
        result = process_file(args.input_file, args.output_dir)
    except Exception as exc:
        print(f"Error processing {args.input_file}: {exc}")
        return 1

    _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())