import pandas as pd
import pytest

from fpl_generate_report_v3 import build_awards, build_aggregates, load_data, run_report


def _award_titles(awards):
    return [a["Nagroda"] for a in awards]


def test_run_report_no_write(season_csv, mapping_json):
    result = run_report(season_csv, mapping_json, write_output=False)
    assert "agg" in result
    assert len(result["awards"]) > 0
    assert len(result["top_captains"]) > 0


def test_bench_boost_award_present_when_chip_used(season_csv, mapping_json):
    df, id_to_name = load_data(season_csv, mapping_json)
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, id_to_name)
    assert "Mykolenko w końcu punktuje" in _award_titles(awards)
    bb_award = next(a for a in awards if a["Nagroda"] == "Mykolenko w końcu punktuje")
    assert bb_award["Drużyna"] == "Alpha United"
    assert bb_award["Wartość"].endswith(" pkt")


def test_triple_captain_award_when_chip_used(season_csv, mapping_json):
    df, id_to_name = load_data(season_csv, mapping_json)
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, id_to_name)
    assert "Salah czy nie Salah?" in _award_titles(awards)


def test_optional_chip_awards_skipped_when_chip_unused():
    """bboost / 3xc / freehit awards only when those chips appear in the CSV."""
    base = {
        "points": 50,
        "bench": 5,
        "hits": 0,
        "captain_points": 10,
        "transfer_gain": 0,
        "autosub_count": 0,
        "event_transfers": 0,
        "entry_name": "Solo FC",
        "captain_id": 1,
        "team": "[{'player_id': 1, 'multiplier': 2, 'points': 6}]",
    }
    df = pd.DataFrame([
        {**base, "gw": 1, "chip": None},
        {**base, "gw": 20, "points": 55, "chip": None},
        {**base, "entry_name": "Other FC", "gw": 5, "chip": "wildcard1"},
    ])
    from fpl_chips import BENCH_BOOST_CHIPS, FREE_HIT_CHIPS, TRIPLE_CAPTAIN_CHIPS

    assert df[df["chip"].isin(BENCH_BOOST_CHIPS)].empty
    assert df[df["chip"].isin(TRIPLE_CAPTAIN_CHIPS)].empty
    assert df[df["chip"].isin(FREE_HIT_CHIPS)].empty

    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, {})
    titles = _award_titles(awards)
    assert "Mykolenko w końcu punktuje" not in titles
    assert "Salah czy nie Salah?" not in titles
    assert "Upolowane" not in titles


def test_autosub_award_uses_razy_unit(season_csv, mapping_json):
    df, id_to_name = load_data(season_csv, mapping_json)
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, id_to_name)
    autosub = next(a for a in awards if a["Nagroda"] == "Jak to mówią: super sub!")
    assert autosub["Wartość"].endswith(" razy")
    assert " pkt" not in autosub["Wartość"]


def test_best_gw_count_award_uses_razy(season_csv, mapping_json):
    df, id_to_name = load_data(season_csv, mapping_json)
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, id_to_name)
    best_gw = next(a for a in awards if a["Nagroda"] == "WSZYSCY SĄ W TYLE!!! NA CZELE")
    assert best_gw["Wartość"].endswith(" razy")
