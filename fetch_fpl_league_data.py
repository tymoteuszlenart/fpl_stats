"""CLI entry point: download FPL classic league data to CSV."""

import argparse
import os
import sys

from dotenv import load_dotenv

from fpl_stats.api import (
    COOKIE,
    FplApiError,
    FplAuthError,
    FplResponseError,
    get_bootstrap_events,
    get_league_entries,
)
from fpl_stats.fetcher import fetch_entry_gameweeks
from fpl_stats.season_storage import write_season_csv_and_picks

load_dotenv()
LEAGUE_ID = os.getenv("FPL_LEAGUE_ID")

FETCH_MODES = ("finished", "current", "full")

output_file = "csv/fpl_season_data.csv"
os.makedirs("csv", exist_ok=True)


def require_env():
    missing = []
    if not COOKIE:
        missing.append("FPL_COOKIE")
    if not LEAGUE_ID:
        missing.append("FPL_LEAGUE_ID")
    if missing:
        raise SystemExit(
            "Missing required environment variable(s): "
            + ", ".join(missing)
            + ". Set them in .env (see README.md or .env.example)."
        )


def _event_by_id(events):
    return {e["id"]: e for e in events if "id" in e}


def _current_gameweek_id(events):
    for event in events:
        if event.get("is_current"):
            return event["id"]
    finished = [e["id"] for e in events if e.get("finished")]
    if finished:
        return max(finished)
    return max(e["id"] for e in events)


def resolve_gameweeks(events, *, fetch_mode="finished", max_gw=None):
    """
    Build sorted GW ids to fetch from bootstrap events.

    fetch_mode:
      finished — only events with finished=True (default mid-season)
      current  — GW 1 through the current gameweek
      full     — all gameweeks in bootstrap (typically 38)
    """
    if fetch_mode not in FETCH_MODES:
        raise ValueError(
            f"fetch_mode must be one of {FETCH_MODES!r}, got {fetch_mode!r}"
        )

    all_ids = sorted(e["id"] for e in events)
    if not all_ids:
        raise FplResponseError("Bootstrap static: no gameweek ids in events")

    if fetch_mode == "full":
        gw_list = list(all_ids)
    elif fetch_mode == "finished":
        finished_ids = {e["id"] for e in events if e.get("finished")}
        gw_list = [gw for gw in all_ids if gw in finished_ids]
    else:
        current_id = _current_gameweek_id(events)
        gw_list = [gw for gw in all_ids if gw <= current_id]

    if max_gw is not None:
        gw_list = [gw for gw in gw_list if gw <= max_gw]

    return gw_list


def parse_fetch_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Download FPL classic league data to CSV."
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--finished-only",
        action="store_const",
        const="finished",
        dest="fetch_mode",
        help="Fetch only finished gameweeks (default mid-season)",
    )
    mode_group.add_argument(
        "--through-current",
        action="store_const",
        const="current",
        dest="fetch_mode",
        help="Fetch GW 1 through the current gameweek",
    )
    mode_group.add_argument(
        "--full-season",
        action="store_const",
        const="full",
        dest="fetch_mode",
        help="Fetch every gameweek listed in bootstrap (full season)",
    )
    parser.add_argument(
        "--max-gw",
        type=int,
        metavar="N",
        help="Do not fetch gameweeks above N (also via FPL_MAX_GW)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=output_file,
        help=f"Output CSV path (default: {output_file})",
    )
    args = parser.parse_args(argv)

    env_mode = os.getenv("FPL_FETCH_MODE", "").strip().lower()
    if args.fetch_mode is None:
        if env_mode:
            if env_mode not in FETCH_MODES:
                parser.error(
                    f"FPL_FETCH_MODE must be one of {', '.join(FETCH_MODES)}"
                )
            args.fetch_mode = env_mode
        else:
            args.fetch_mode = "finished"
    elif env_mode and env_mode != args.fetch_mode:
        parser.error(
            f"Conflicting fetch mode: CLI selected {args.fetch_mode!r} "
            f"but FPL_FETCH_MODE is {env_mode!r}"
        )

    env_max = os.getenv("FPL_MAX_GW", "").strip()
    if args.max_gw is None and env_max:
        try:
            args.max_gw = int(env_max)
        except ValueError:
            parser.error(f"FPL_MAX_GW must be an integer, got {env_max!r}")

    if args.max_gw is not None and args.max_gw < 1:
        parser.error("--max-gw must be at least 1")

    return args


def main(argv=None):
    args = parse_fetch_args(argv)
    require_env()

    try:
        events = get_bootstrap_events()
    except FplAuthError as exc:
        print(f"Fatal: {exc}")
        raise SystemExit(1) from exc
    except FplApiError as exc:
        print(f"Fatal: could not load bootstrap metadata: {exc}")
        raise SystemExit(1) from exc

    events_by_id = _event_by_id(events)
    try:
        gameweeks = resolve_gameweeks(
            events, fetch_mode=args.fetch_mode, max_gw=args.max_gw
        )
    except ValueError as exc:
        print(f"Fatal: {exc}")
        raise SystemExit(2) from exc

    if not gameweeks:
        print(
            "Fatal: no gameweeks to fetch for the selected range "
            f"(mode={args.fetch_mode!r}, max_gw={args.max_gw!r})."
        )
        raise SystemExit(2)

    print(
        f"Tryb pobierania: {args.fetch_mode}; "
        f"kolejki: {gameweeks[0]}–{gameweeks[-1]} ({len(gameweeks)} GW)"
    )

    try:
        league = get_league_entries(LEAGUE_ID)
    except FplAuthError as exc:
        print(f"Fatal: {exc}")
        raise SystemExit(1) from exc
    except FplApiError as exc:
        print(f"Fatal: could not load league {LEAGUE_ID}: {exc}")
        raise SystemExit(1) from exc

    all_data = []

    for member in league:
        entry_id = member["entry"]
        name = member["player_name"]
        entry_name = member["entry_name"]
        print(f"Pobieram dane drużyny: {entry_name}")
        try:
            rows = fetch_entry_gameweeks(
                entry_id,
                entry_name,
                name,
                gameweeks,
                events_by_id,
            )
        except FplAuthError as exc:
            print(f"Fatal: {exc}")
            raise SystemExit(1) from exc
        all_data.extend(rows)

    out_path = args.output
    picks_path = write_season_csv_and_picks(all_data, out_path)
    print(f"Zapisano dane do {out_path}")
    print(f"Zapisano wybory drużyn do {picks_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
