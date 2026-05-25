# -*- coding: utf-8 -*-
"""CLI entry point: generate FPL league season PDF/HTML reports."""

import argparse
import sys

from fpl_stats.aggregates import build_aggregates
from fpl_stats.awards import build_awards, player_display_name
from fpl_stats.data_loader import load_data
from fpl_stats.report import (
    build_awards_html,
    report_project_root,
    run_report,
    write_awards_pdf,
)

__all__ = [
    "build_aggregates",
    "build_awards",
    "build_awards_html",
    "load_data",
    "player_display_name",
    "report_project_root",
    "run_report",
    "write_awards_pdf",
]


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Generate FPL league season PDF/HTML reports.")
    parser.add_argument("--csv", default="csv/fpl_season_data.csv", help="Input season CSV path")
    parser.add_argument("--output-dir", default="fpl_output", help="Directory for PDF/HTML output")
    parser.add_argument("--season", default=None, help="Season label (default: current football season)")
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Skip writing PDF/HTML files (useful for tests)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    try:
        run_report(
            csv_path=args.csv,
            output_dir=args.output_dir,
            season=args.season,
            write_output=not args.no_write,
        )
    except FileNotFoundError as exc:
        print(f"❌ {exc.args[0]}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main(sys.argv[1:])
