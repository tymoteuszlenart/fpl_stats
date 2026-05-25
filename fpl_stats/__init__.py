"""FPL league stats: fetch, aggregates, awards, and PDF reports."""

from fpl_stats.aggregates import build_aggregates
from fpl_stats.awards import build_awards, player_display_name
from fpl_stats.data_loader import load_data
from fpl_stats.report import (
    build_awards_html,
    default_season_label,
    generate_pdfs,
    report_project_root,
    run_report,
    write_awards_pdf,
)

__all__ = [
    "build_aggregates",
    "build_awards",
    "build_awards_html",
    "default_season_label",
    "generate_pdfs",
    "load_data",
    "player_display_name",
    "report_project_root",
    "run_report",
    "write_awards_pdf",
]
