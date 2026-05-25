from unittest.mock import patch

import pytest

from fetch_fpl_league_data import get_manager_data


def _picks_payload(*, captain_id, vice_id, captain_multiplier, chip=None, bench_positions=None):
    bench_positions = bench_positions or [12, 13, 14, 15]
    picks = []
    for pos in range(1, 16):
        element = {12: 201, 13: 202, 14: 203, 15: 204}.get(pos, pos)
        if pos <= 11:
            mult = captain_multiplier if element == captain_id else 1
        else:
            mult = 0
        picks.append({
            "element": element,
            "position": pos,
            "multiplier": mult,
            "is_captain": element == captain_id,
            "is_vice_captain": element == vice_id,
        })
    return {
        "picks": picks,
        "entry_history": {
            "points": 55,
            "points_on_bench": 7,
            "event_transfers_cost": 0,
            "event_transfers": 0,
        },
        "automatic_subs": [],
        "active_chip": chip,
    }


def _live_payload(player_points):
    return {
        "elements": [
            {"id": pid, "stats": {"total_points": pts}}
            for pid, pts in player_points.items()
        ]
    }


@patch("fetch_fpl_league_data.fpl_get")
def test_captain_played_uses_captain_points(mock_get):
    captain_id, vice_id = 1, 2
    mock_get.side_effect = [
        _picks_payload(captain_id=captain_id, vice_id=vice_id, captain_multiplier=2),
        _live_payload({1: 10, 2: 6, 3: 4, 4: 2, 5: 1, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0}),
    ]
    row = get_manager_data(999, 1)
    assert row["captain_id"] == captain_id
    assert row["captain_raw_points"] == 10
    assert row["captain_contribution_points"] == 20
    assert row["captain_points"] == 10


@patch("fetch_fpl_league_data.fpl_get")
def test_captain_dnp_uses_vice_captain(mock_get):
    captain_id, vice_id = 1, 2
    mock_get.side_effect = [
        _picks_payload(captain_id=captain_id, vice_id=vice_id, captain_multiplier=1),
        _live_payload({1: 0, 2: 8, 3: 4, 4: 2, 5: 1, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0}),
    ]
    row = get_manager_data(999, 1)
    assert row["captain_id"] == vice_id
    assert row["captain_raw_points"] == 8
    assert row["captain_contribution_points"] == 16
    assert row["captain_points"] == 8


@patch("fetch_fpl_league_data.fpl_get")
def test_triple_captain_applies_3x_contribution(mock_get):
    captain_id, vice_id = 1, 2
    mock_get.side_effect = [
        _picks_payload(
            captain_id=captain_id,
            vice_id=vice_id,
            captain_multiplier=2,
            chip="3xc",
        ),
        _live_payload({1: 12, 2: 6, 3: 4, 4: 2, 5: 1, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0}),
    ]
    row = get_manager_data(999, 1)
    assert row["captain_raw_points"] == 12
    assert row["captain_contribution_points"] == 36


@patch("fetch_fpl_league_data.fpl_get")
def test_bench_boost_sums_bench_players_not_points_on_bench(mock_get):
    captain_id, vice_id = 1, 2
    mock_get.side_effect = [
        _picks_payload(
            captain_id=captain_id,
            vice_id=vice_id,
            captain_multiplier=2,
            chip="bboost",
        ),
        _live_payload({
            1: 5, 2: 4, 3: 3, 4: 2, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1, 11: 1,
            201: 6, 202: 4, 203: 2, 204: 1,
        }),
    ]
    row = get_manager_data(999, 1)
    assert row["bench"] == 13
    assert row["bench"] != 7


@patch("fetch_fpl_league_data.fpl_get")
def test_non_bench_boost_uses_points_on_bench(mock_get):
    captain_id, vice_id = 1, 2
    mock_get.side_effect = [
        _picks_payload(captain_id=captain_id, vice_id=vice_id, captain_multiplier=2),
        _live_payload({1: 5, 2: 4, 3: 3, 4: 2, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1, 11: 1}),
    ]
    row = get_manager_data(999, 1)
    assert row["bench"] == 7


@patch("fetch_fpl_league_data.fpl_get")
def test_null_entry_history_still_returns_chip_key(mock_get):
    captain_id, vice_id = 1, 2
    payload = _picks_payload(
        captain_id=captain_id, vice_id=vice_id, captain_multiplier=2, chip="bboost"
    )
    payload["entry_history"] = None
    mock_get.side_effect = [
        payload,
        _live_payload({
            1: 5, 2: 4, 3: 3, 4: 2, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1, 11: 1,
            201: 1, 202: 1, 203: 1, 204: 1,
        }),
    ]
    row = get_manager_data(999, 38)
    assert "chip" in row
    assert row["chip"] == "bboost"
    assert row["gw"] == 38
