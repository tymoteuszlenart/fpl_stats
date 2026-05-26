import pandas as pd

from fpl_stats.chips import captain_contribution_multiplier, ensure_captain_columns
from fpl_stats import build_awards, build_aggregates


def test_legacy_csv_backfills_contribution_from_raw():
    df = pd.DataFrame(
        [
            {
                "gw": 1,
                "entry_name": "A",
                "captain_points": 10,
                "chip": None,
                "points": 50,
                "bench": 0,
                "hits": 0,
                "transfer_gain": 0,
                "autosub_count": 0,
                "event_transfers": 0,
            },
            {
                "gw": 2,
                "entry_name": "A",
                "captain_points": 8,
                "chip": "3xc",
                "points": 60,
                "bench": 0,
                "hits": 0,
                "transfer_gain": 0,
                "autosub_count": 0,
                "event_transfers": 0,
            },
        ]
    )
    out = ensure_captain_columns(df)
    assert out.loc[0, "captain_raw_points"] == 10
    assert out.loc[0, "captain_contribution_points"] == 20
    assert out.loc[1, "captain_contribution_points"] == 24


def test_triple_captain_award_uses_contribution_not_triple_raw():
    team = "[{'player_id': 100, 'multiplier': 2, 'points': 6}]"
    base = {
        "bench": 0,
        "hits": 0,
        "transfer_gain": 0,
        "autosub_count": 0,
        "event_transfers": 0,
        "team": team,
    }
    df = pd.DataFrame(
        [
            {
                **base,
                "entry_name": "Beta City",
                "gw": 1,
                "chip": "3xc",
                "captain_raw_points": 6,
                "captain_contribution_points": 18,
                "captain_points": 6,
                "points": 40,
                "captain_id": 100,
            },
            {
                **base,
                "entry_name": "Beta City",
                "gw": 2,
                "chip": None,
                "captain_raw_points": 4,
                "captain_contribution_points": 8,
                "captain_points": 4,
                "points": 30,
                "captain_id": 100,
            },
            {
                **base,
                "entry_name": "Other",
                "gw": 1,
                "chip": None,
                "captain_raw_points": 15,
                "captain_contribution_points": 30,
                "captain_points": 15,
                "points": 50,
                "captain_id": 1,
            },
            {
                **base,
                "entry_name": "Other",
                "gw": 2,
                "chip": None,
                "captain_raw_points": 5,
                "captain_contribution_points": 10,
                "captain_points": 5,
                "points": 45,
                "captain_id": 1,
            },
            {
                **base,
                "entry_name": "Beta City",
                "gw": 21,
                "chip": None,
                "captain_raw_points": 3,
                "captain_contribution_points": 6,
                "captain_points": 3,
                "points": 35,
                "captain_id": 100,
            },
            {
                **base,
                "entry_name": "Other",
                "gw": 21,
                "chip": None,
                "captain_raw_points": 2,
                "captain_contribution_points": 4,
                "captain_points": 2,
                "points": 40,
                "captain_id": 1,
            },
        ]
    )
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, {})
    tc = next(a for a in awards if a["Nagroda"] == "Haaland na podkurwkę Radka")
    assert tc["Drużyna"] == "Beta City"
    assert tc["Wartość"] == "18 pkt"


def test_captain_multiplier_values():
    assert captain_contribution_multiplier(None) == 2
    assert captain_contribution_multiplier("3xc") == 3
    assert captain_contribution_multiplier("3xc1") == 3
