import pandas as pd

from fpl_stats.chips import normalize_chips_dataframe
from fpl_stats import build_awards, build_aggregates


def test_legacy_unsuffixed_chips_split_by_gameweek():
    df = pd.DataFrame([
        {"entry_name": "A", "gw": 5, "chip": "bboost", "bench": 10, "points": 50,
         "hits": 0, "captain_points": 0, "transfer_gain": 0, "autosub_count": 0, "event_transfers": 0},
        {"entry_name": "A", "gw": 25, "chip": "bboost", "bench": 20, "points": 60,
         "hits": 0, "captain_points": 0, "transfer_gain": 0, "autosub_count": 0, "event_transfers": 0},
    ])
    out = normalize_chips_dataframe(df)
    assert set(out["chip"]) == {"bboost1", "bboost2"}


def test_bench_boost_award_uses_best_single_not_sum_of_halves():
    team = "[{'player_id': 1, 'multiplier': 2, 'points': 6}]"
    df = normalize_chips_dataframe(pd.DataFrame([
        {"entry_name": "A", "gw": 5, "chip": "bboost", "bench": 10, "points": 50,
         "hits": 0, "captain_points": 0, "transfer_gain": 0, "autosub_count": 0,
         "event_transfers": 0, "team": team, "captain_id": 1},
        {"entry_name": "A", "gw": 25, "chip": "bboost", "bench": 20, "points": 60,
         "hits": 0, "captain_points": 0, "transfer_gain": 0, "autosub_count": 0,
         "event_transfers": 0, "team": team, "captain_id": 1},
        {"entry_name": "B", "gw": 1, "chip": None, "bench": 1, "points": 40,
         "hits": 0, "captain_points": 0, "transfer_gain": 0, "autosub_count": 0,
         "event_transfers": 0, "team": team, "captain_id": 1},
    ]))
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, {})
    bb = next(a for a in awards if a["Nagroda"] == "Mykolenko w końcu punktuje")
    assert bb["Drużyna"] == "A"
    assert bb["Wartość"] == "20 pkt"
    assert "GW 25" in bb["Za co"]


def test_max_bench_excludes_all_bench_boost_halves():
    df = normalize_chips_dataframe(pd.DataFrame([
        {"entry_name": "Only BB", "gw": 1, "chip": "bboost", "bench": 99, "points": 50,
         "hits": 0, "captain_points": 0, "transfer_gain": 0, "autosub_count": 0, "event_transfers": 0},
        {"entry_name": "Mixed", "gw": 2, "chip": None, "bench": 4, "points": 50,
         "hits": 0, "captain_points": 0, "transfer_gain": 0, "autosub_count": 0, "event_transfers": 0},
    ]))
    agg, _ = build_aggregates(df)
    by_name = agg.set_index("entry_name")
    assert by_name.loc["Only BB", "max_bench_points"] == 0
    assert by_name.loc["Mixed", "max_bench_points"] == 4
