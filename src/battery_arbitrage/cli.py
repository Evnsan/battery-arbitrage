import argparse
import logging
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from battery_arbitrage.csv_export import write_report_csv
from battery_arbitrage.pipeline import run_optimization


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="battery-arbitrage",
        description="Optimize battery dispatch and export CSV reports.",
        epilog=(
            "The selected time window is [start, end): start is inclusive, "
            "end is exclusive. Bounds outside data coverage are clipped to "
            "the available timeline. Bounds must align with boundaries "
            "shared by all markets. A window with no overlap is an error."
        ),
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        required=True,
        help="market data workbook (.xlsx)",
    )
    parser.add_argument(
        "-d",
        "--dispatch-csv",
        type=Path,
        default=Path("results/dispatch.csv"),
        help="dispatch report output path (default: results/dispatch.csv)",
    )
    parser.add_argument(
        "-o",
        "--operation-csv",
        type=Path,
        default=Path("results/operation.csv"),
        help="operation report output path (default: results/operation.csv)",
    )
    parser.add_argument(
        "-t",
        "--tolerance-millis",
        type=int,
        default=1000,
        help="timestamp alignment tolerance in milliseconds (default: 1000)",
    )
    parser.add_argument(
        "-s",
        "--start-time",
        type=datetime.fromisoformat,
        help="inclusive start timestamp in ISO format",
    )
    parser.add_argument(
        "-e",
        "--end-time",
        type=datetime.fromisoformat,
        help="exclusive end timestamp in ISO format",
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        default="INFO",
        help="logging verbosity (default: INFO)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.verbosity),
        format="%(levelname)s: %(message)s",
    )

    try:
        report = run_optimization(
            args.input,
            config=None,
            tolerance_millis=args.tolerance_millis,
            start_time=args.start_time,
            end_time=args.end_time,
        )
        dispatch_path, operation_path = write_report_csv(
            report,
            args.dispatch_csv,
            args.operation_csv,
        )
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Dispatch report saved to {dispatch_path}")
    print(f"Operation report saved to {operation_path}")
    print(f"Total profit: £{report.total_profit_gbp:.2f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
