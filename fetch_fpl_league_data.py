import argparse
import json
import os
import time

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
COOKIE = os.getenv("FPL_COOKIE")
LEAGUE_ID = os.getenv("FPL_LEAGUE_ID")

REQUEST_TIMEOUT = 30
MAX_RETRIES = 4
INITIAL_BACKOFF = 1.0

BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Cookie": COOKIE,
}

FETCH_MODES = ("finished", "current", "full")

output_file = "csv/fpl_season_data.csv"
os.makedirs("csv", exist_ok=True)


class FplApiError(Exception):
    """FPL HTTP/API failure."""


class FplAuthError(FplApiError):
    """401/403 — invalid or expired session cookie."""


class FplNotFoundError(FplApiError):
    """404 — resource not found."""


class FplGameweekNotAvailableError(FplNotFoundError):
    """404 for a gameweek that is not finished / not yet published."""


class FplRateLimitError(FplApiError):
    """429 — rate limited after retries."""


class FplResponseError(FplApiError):
    """JSON parse failure or unexpected response shape."""


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


def _status_message(status_code, url):
    if status_code in (401, 403):
        return (
            f"HTTP {status_code} (authentication failed). "
            "Check FPL_COOKIE in .env — copy a fresh session cookie from "
            "https://fantasy.premierleague.com while logged in."
        )
    if status_code == 404:
        return f"HTTP 404 (not found): {url}"
    if status_code == 429:
        return "HTTP 429 (rate limited). Try again later or reduce request frequency."
    return f"HTTP {status_code}: {url}"


def fpl_get(url, *, context="", retries=MAX_RETRIES, backoff=INITIAL_BACKOFF):
    """GET JSON from the FPL API with status checks and transient retries."""
    prefix = f"{context}: " if context else ""
    last_error = None

    for attempt in range(retries):
        try:
            response = requests.get(
                url, headers=HEADERS, timeout=REQUEST_TIMEOUT
            )
        except requests.Timeout as exc:
            last_error = FplApiError(
                f"{prefix}Request timed out after {REQUEST_TIMEOUT}s: {url}"
            )
            last_error.__cause__ = exc
        except requests.RequestException as exc:
            last_error = FplApiError(
                f"{prefix}Network error for {url}: {exc}"
            )
            last_error.__cause__ = exc
        else:
            status = response.status_code
            if status in (401, 403):
                raise FplAuthError(prefix + _status_message(status, url))
            if status == 404:
                raise FplNotFoundError(prefix + _status_message(status, url))
            if status == 429 or status >= 500:
                last_error = (
                    FplRateLimitError(prefix + _status_message(status, url))
                    if status == 429
                    else FplApiError(prefix + _status_message(status, url))
                )
            elif not response.ok:
                raise FplApiError(prefix + _status_message(status, url))
            else:
                try:
                    return response.json()
                except json.JSONDecodeError as exc:
                    snippet = response.text[:200].strip()
                    raise FplResponseError(
                        f"{prefix}Invalid JSON from {url}: {exc}. "
                        f"Body starts with: {snippet!r}"
                    ) from exc

        if attempt < retries - 1:
            delay = backoff * (2**attempt)
            print(
                f"{prefix}Retry {attempt + 1}/{retries - 1} in {delay:.1f}s "
                f"({last_error})"
            )
            time.sleep(delay)

    raise last_error


def get_bootstrap_events():
    """Return gameweek metadata from bootstrap-static."""
    data = fpl_get(BOOTSTRAP_URL, context="Bootstrap static")
    events = data.get("events")
    if not isinstance(events, list) or not events:
        raise FplResponseError("Bootstrap static: missing or empty 'events'")
    return events


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


def get_league_entries(league_id):
    entries = []
    page = 1
    while True:
        url = (
            f"https://fantasy.premierleague.com/api/leagues-classic/"
            f"{league_id}/standings/?page_standings={page}"
        )
        data = fpl_get(url, context=f"League {league_id} standings page {page}")
        try:
            standings = data["standings"]
            entries.extend(standings["results"])
            if not standings["has_next"]:
                break
            page += 1
        except (KeyError, TypeError) as exc:
            raise FplResponseError(
                f"League {league_id} standings page {page}: "
                f"unexpected response shape ({exc})"
            ) from exc
    return entries


def normalize_wildcard_chip(chip, gw):
    """Map API wildcard chip to wildcard1 (GW < 20) or wildcard2 (GW >= 20)."""
    if chip == "wildcard":
        return "wildcard1" if gw < 20 else "wildcard2"
    return chip


def get_manager_data(entry_id, gw):
    picks_url = (
        f"https://fantasy.premierleague.com/api/entry/{entry_id}/event/{gw}/picks/"
    )
    live_url = f"https://fantasy.premierleague.com/api/event/{gw}/live/"
    ctx = f"Entry {entry_id} GW{gw}"

    picks = fpl_get(picks_url, context=f"{ctx} picks")
    live = fpl_get(live_url, context=f"{ctx} live")

    picks_data = picks.get("picks", [])
    if not picks_data:
        raise FplResponseError(f"{ctx}: picks response has no 'picks' data")

    try:
        live_points = {
            e["id"]: e["stats"]["total_points"] for e in live["elements"]
        }
    except (KeyError, TypeError) as exc:
        raise FplResponseError(
            f"{ctx}: unexpected live event response shape ({exc})"
        ) from exc

    team = [
        {"player_id": p["element"], "multiplier": p["multiplier"]}
        for p in picks_data
    ]

    captain_id = next(
        (pd["element"] for pd in picks_data if pd.get("is_captain")), None
    )
    vice_captain_id = next(
        (pd["element"] for pd in picks_data if pd.get("is_vice_captain")), None
    )

    team_with_points = [
        {
            "player_id": p["player_id"],
            "multiplier": p["multiplier"],
            "points": live_points.get(p["player_id"], 0),
        }
        for p in team
    ]

    captain_played = any(
        p["player_id"] == captain_id and p["multiplier"] > 1
        for p in team_with_points
    )
    if captain_played:
        captain_points = live_points.get(captain_id, 0)
    else:
        captain_id = vice_captain_id
        captain_points = live_points.get(vice_captain_id, 0)

    history = picks.get("entry_history", {})
    automatic_subs = picks.get("automatic_subs", [])
    chip = picks.get("active_chip", None)

    if chip == "bboost":
        bench_ids = [p["element"] for p in picks_data if p["position"] > 11]
        element_stats = live.get("elements", [])
        live_points = {e["id"]: e["stats"]["total_points"] for e in element_stats}
        bench_boost_points = sum(live_points.get(e, 0) for e in bench_ids)
        bench = bench_boost_points
    else:
        bench = history.get("points_on_bench")

    in_ids = [t["element_in"] for t in automatic_subs]
    out_ids = [t["element_out"] for t in automatic_subs]

    transfer_gain = 0
    for in_id, out_id in zip(in_ids, out_ids):
        in_pts = next(
            (e["stats"]["total_points"] for e in live["elements"] if e["id"] == in_id),
            0,
        )
        out_pts = next(
            (e["stats"]["total_points"] for e in live["elements"] if e["id"] == out_id),
            0,
        )
        transfer_gain += in_pts - out_pts

    return {
        "gw": gw,
        "points": history.get("points"),
        "team": team_with_points,
        "bench": bench,
        "hits": history.get("event_transfers_cost"),
        "event_transfers": history.get("event_transfers"),
        "chip": chip,
        "autosub_count": len(automatic_subs),
        "captain_id": captain_id,
        "captain_points": captain_points,
        "transfer_in_ids": in_ids,
        "transfer_out_ids": out_ids,
        "transfer_gain": transfer_gain,
    }


def _gameweek_not_found_error(exc, gw, events_by_id):
    """Return FplGameweekNotAvailableError for unfinished GWs, else the original 404."""
    event = events_by_id.get(gw)
    if event is not None and not event.get("finished"):
        err = FplGameweekNotAvailableError(
            f"GW{gw} is not finished yet; picks/live data may not be available"
        )
        err.__cause__ = exc
        return err
    return exc


def fetch_entry_gameweeks(
    entry_id,
    entry_name,
    player_name,
    gameweeks,
    events_by_id,
    *,
    sleep_seconds=0.3,
):
    """Fetch all requested gameweeks for one league entry."""
    rows = []
    for gw in gameweeks:
        try:
            data = get_manager_data(entry_id, gw)
        except FplNotFoundError as exc:
            err = _gameweek_not_found_error(exc, gw, events_by_id)
            if isinstance(err, FplGameweekNotAvailableError):
                print(f"  GW{gw}: jeszcze niedostępna ({err})")
            else:
                print(f"  GW{gw}: nie znaleziono — {err}")
            continue
        except FplAuthError:
            raise
        except (FplRateLimitError, FplResponseError, FplApiError) as exc:
            print(f"  GW{gw}: błąd API — {exc}")
            continue

        data.update({
            "player_name": player_name,
            "entry_name": entry_name,
        })
        data["chip"] = normalize_wildcard_chip(data["chip"], data["gw"])
        rows.append(data)
        time.sleep(sleep_seconds)
    return rows


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
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    pd.DataFrame(all_data).to_csv(out_path, index=False)
    print(f"Zapisano dane do {out_path}")


if __name__ == "__main__":
    main()
