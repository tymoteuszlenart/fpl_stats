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

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Cookie": COOKIE,
}

NUM_GW = 38
output_file = "csv/fpl_season_data.csv"
os.makedirs("csv", exist_ok=True)


class FplApiError(Exception):
    """FPL HTTP/API failure."""


class FplAuthError(FplApiError):
    """401/403 — invalid or expired session cookie."""


class FplNotFoundError(FplApiError):
    """404 — resource not found."""


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


def main():
    require_env()
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
        for gw in range(1, NUM_GW + 1):
            try:
                data = get_manager_data(entry_id, gw)
                data.update({
                    "player_name": name,
                    "entry_name": entry_name,
                })
                data["chip"] = normalize_wildcard_chip(data["chip"], data["gw"])
                all_data.append(data)
                time.sleep(0.3)
            except FplAuthError as exc:
                print(f"Fatal: {exc}")
                raise SystemExit(1) from exc
            except (FplNotFoundError, FplRateLimitError, FplResponseError, FplApiError) as exc:
                print(
                    f"⚠️  Pomijam {entry_name} (entry {entry_id}) GW{gw}: {exc}"
                )
                continue
            except (KeyError, TypeError) as exc:
                print(
                    f"⚠️  Pomijam {entry_name} (entry {entry_id}) GW{gw}: "
                    f"nieoczekiwana struktura danych ({exc})"
                )
                continue

    pd.DataFrame(all_data).to_csv(output_file, index=False)
    print(f"Zapisano dane do {output_file}")


if __name__ == "__main__":
    main()
