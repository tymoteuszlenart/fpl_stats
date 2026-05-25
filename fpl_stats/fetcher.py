"""Transform FPL API responses into per-gameweek manager rows."""

import time

from fpl_stats.api import (
    FplApiError,
    FplAuthError,
    FplGameweekNotAvailableError,
    FplNotFoundError,
    FplRateLimitError,
    FplResponseError,
    fpl_get,
)
from fpl_stats.chips import captain_contribution_multiplier, normalize_chip_activation


def normalize_wildcard_chip(chip, gw):
    """Backward-compatible alias for :func:`normalize_chip_activation`."""
    return normalize_chip_activation(chip, gw)


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
        captain_raw_points = live_points.get(captain_id, 0)
    else:
        captain_id = vice_captain_id
        captain_raw_points = live_points.get(vice_captain_id, 0)

    history = picks.get("entry_history") or {}
    automatic_subs = picks.get("automatic_subs") or []
    chip = picks.get("active_chip")
    if chip is None and isinstance(history, dict):
        chip = history.get("active_chip") or history.get("chip")

    cap_mult = captain_contribution_multiplier(chip)
    captain_contribution_points = captain_raw_points * cap_mult

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
        "captain_raw_points": captain_raw_points,
        "captain_contribution_points": captain_contribution_points,
        "captain_points": captain_raw_points,
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
        except KeyError as exc:
            print(
                f"  GW{gw}: nieoczekiwana struktura odpowiedzi API (brak pola {exc!s}) — pominięto"
            )
            continue

        data.update({
            "player_name": player_name,
            "entry_name": entry_name,
        })
        gw_num = data.get("gw", gw)
        data["chip"] = normalize_chip_activation(data.get("chip"), gw_num)
        rows.append(data)
        time.sleep(sleep_seconds)
    return rows
