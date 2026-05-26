import pandas as pd
import pytest

from fpl_stats import build_awards, build_aggregates, load_data, run_report
from fpl_stats.player_mapping import (
    load_bootstrap_clubs,
    season_club_points_by_entry,
    season_player_points_by_entry,
)


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
    assert "Ławka" in _award_titles(awards)
    bb_award = next(a for a in awards if a["Nagroda"] == "Ławka")
    assert bb_award["Drużyna"] == "Alpha United"
    assert bb_award["Wartość"].endswith(" pkt")
    assert "Po co był ten BB?" not in _award_titles(awards)


def test_triple_captain_award_when_chip_used(season_csv, mapping_json):
    df, id_to_name = load_data(season_csv, mapping_json)
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, id_to_name)
    assert "Haaland na podkurwkę Radka" in _award_titles(awards)
    tc = next(a for a in awards if a["Nagroda"] == "Haaland na podkurwkę Radka")
    assert tc["Drużyna"] == "Beta City"
    assert tc["Wartość"] == "18 pkt"
    assert "3× i zero zysków" not in _award_titles(awards)


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
    df = pd.DataFrame(
        [
            {**base, "gw": 1, "chip": None},
            {**base, "gw": 20, "points": 55, "chip": None},
            {**base, "entry_name": "Other FC", "gw": 5, "chip": "wildcard1"},
        ]
    )
    from fpl_stats.chips import BENCH_BOOST_CHIPS, FREE_HIT_CHIPS, TRIPLE_CAPTAIN_CHIPS

    assert df[df["chip"].isin(BENCH_BOOST_CHIPS)].empty
    assert df[df["chip"].isin(TRIPLE_CAPTAIN_CHIPS)].empty
    assert df[df["chip"].isin(FREE_HIT_CHIPS)].empty

    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, {})
    titles = _award_titles(awards)
    assert "Ławka" not in titles
    assert "Po co był ten BB?" not in titles
    assert "Haaland na podkurwkę Radka" not in titles
    assert "3× i zero zysków" not in titles
    assert "Free Hit — i nigdy więcej tak" not in titles
    assert "Free Hit — i pożegnałem nadzieję" not in titles


def test_autosub_award_uses_razy_unit(season_csv, mapping_json):
    df, id_to_name = load_data(season_csv, mapping_json)
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, id_to_name)
    autosub = next(a for a in awards if a["Nagroda"] == "Oczywiście, tak planowałem")
    assert autosub["Wartość"].endswith(" razy")
    assert " pkt" not in autosub["Wartość"]


def test_best_gw_count_award_uses_razy(season_csv, mapping_json):
    df, id_to_name = load_data(season_csv, mapping_json)
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, id_to_name)
    best_gw = next(a for a in awards if a["Nagroda"] == "WSZYSCY SĄ W TYLE!!! NA CZELE")
    assert best_gw["Wartość"].endswith(" razy")


def test_thrift_chip_award_2025_26_rules(season_csv, mapping_json):
    df, id_to_name = load_data(season_csv, mapping_json)
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, id_to_name)
    thrift = next(a for a in awards if a["Nagroda"] == "Chipy? W 2026 jeszcze mam")
    assert thrift["Drużyna"] == "Zebra FC"
    assert thrift["Wartość"] == "0 razy (z 8)"
    assert "max 8" in thrift["Za co"]
    assert "2025/26" in thrift["Za co"]
    assert "nieużywane:" in thrift["Za co"]
    assert "3xC (I poł.)" in thrift["Za co"]


def test_hoarder_chip_award_2025_26_rules(season_csv, mapping_json):
    df, id_to_name = load_data(season_csv, mapping_json)
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, id_to_name)
    hoarder = next(a for a in awards if a["Nagroda"] == "Yolo na każdym chipie")
    assert hoarder["Drużyna"] == "Beta City"
    assert hoarder["Wartość"] == "2 razy (z 8)"
    assert "użyte:" in hoarder["Za co"]
    assert "3xC (I poł.)" in hoarder["Za co"]


def test_thrift_chip_award_counts_half_specific_slots():
    from fpl_stats.chips import MAX_CHIPS_PER_SEASON, season_chip_usage_by_entry

    team = "[{'player_id': 1, 'multiplier': 2, 'points': 6}]"
    base = {
        "points": 50,
        "bench": 5,
        "hits": 0,
        "captain_points": 10,
        "transfer_gain": 0,
        "autosub_count": 0,
        "event_transfers": 0,
        "team": team,
        "captain_id": 1,
    }
    df = pd.DataFrame(
        [
            {**base, "entry_name": "Saver", "gw": 5, "chip": "bboost"},
            {**base, "entry_name": "Saver", "gw": 25, "chip": "bboost"},
            {**base, "entry_name": "Hoarder", "gw": 1, "chip": "3xc1"},
            {**base, "entry_name": "Hoarder", "gw": 5, "chip": "bboost1"},
            {**base, "entry_name": "Hoarder", "gw": 10, "chip": "freehit1"},
            {**base, "entry_name": "Hoarder", "gw": 21, "chip": "wildcard2"},
        ]
    )
    from fpl_stats.chips import normalize_chips_dataframe

    df = normalize_chips_dataframe(df)
    usage = season_chip_usage_by_entry(df)
    assert usage["Saver"] == 2
    assert usage["Hoarder"] == 4
    assert MAX_CHIPS_PER_SEASON == 8

    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, {})
    thrift = next(a for a in awards if a["Nagroda"] == "Chipy? W 2026 jeszcze mam")
    assert thrift["Drużyna"] == "Saver"
    assert thrift["Wartość"] == "2 razy (z 8)"
    hoarder = next(a for a in awards if a["Nagroda"] == "Yolo na każdym chipie")
    assert hoarder["Drużyna"] == "Hoarder"
    assert hoarder["Wartość"] == "4 razy (z 8)"


def test_best_chip_efficiency_award_2025_26(season_csv, mapping_json):
    df, id_to_name = load_data(season_csv, mapping_json)
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, id_to_name)
    best = next(a for a in awards if a["Nagroda"] == "Strateg? Nie, szczęście")
    assert best["Drużyna"] == "Gamma Rovers"
    assert best["Wartość"] == "85.0 pkt/aktywacja (170 pkt, 2 aktyw.)"
    assert "pkt/aktywacja" in best["Wartość"]
    assert "2025/26" in best["Za co"]


def test_worst_chip_efficiency_award_2025_26(season_csv, mapping_json):
    df, id_to_name = load_data(season_csv, mapping_json)
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, id_to_name)
    worst = next(a for a in awards if a["Nagroda"] == "Złoty chip, miedziany wynik")
    assert worst["Drużyna"] == "Alpha United"
    assert worst["Wartość"] == "6.0 pkt/aktywacja (6 pkt, 1 aktyw.)"


def test_chip_efficiency_awards_skipped_when_no_chips_used():
    team = "[{'player_id': 1, 'multiplier': 2, 'points': 6}]"
    base = {
        "points": 50,
        "bench": 5,
        "hits": 0,
        "captain_points": 10,
        "transfer_gain": 0,
        "autosub_count": 0,
        "event_transfers": 0,
        "team": team,
        "captain_id": 1,
        "chip": None,
    }
    df = pd.DataFrame(
        [
            {**base, "entry_name": "A", "gw": 1},
            {**base, "entry_name": "A", "gw": 25},
            {**base, "entry_name": "B", "gw": 2},
            {**base, "entry_name": "B", "gw": 26},
        ]
    )
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, {})
    titles = _award_titles(awards)
    assert "Strateg? Nie, szczęście" not in titles
    assert "Złoty chip, miedziany wynik" not in titles


def test_best_chip_efficiency_tiebreak_fewer_activations():
    team = "[{'player_id': 1, 'multiplier': 2, 'points': 6}]"
    base = {
        "points": 50,
        "bench": 10,
        "hits": 0,
        "captain_points": 10,
        "captain_raw_points": 10,
        "captain_contribution_points": 20,
        "transfer_gain": 0,
        "autosub_count": 0,
        "event_transfers": 0,
        "team": team,
        "captain_id": 1,
    }
    df = pd.DataFrame(
        [
            {**base, "entry_name": "One", "gw": 5, "chip": "bboost1"},
            {**base, "entry_name": "One", "gw": 25, "chip": None},
            {
                **base,
                "entry_name": "Two",
                "gw": 1,
                "chip": "3xc1",
                "captain_contribution_points": 20,
            },
            {**base, "entry_name": "Two", "gw": 10, "chip": "freehit1", "points": 0},
            {**base, "entry_name": "Two", "gw": 26, "chip": None},
        ]
    )
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, {})
    best = next(a for a in awards if a["Nagroda"] == "Strateg? Nie, szczęście")
    assert best["Drużyna"] == "One"
    assert best["Wartość"] == "10.0 pkt/aktywacja (10 pkt, 1 aktyw.)"


def test_worst_chip_efficiency_tiebreak_more_activations():
    team = "[{'player_id': 1, 'multiplier': 2, 'points': 6}]"
    base = {
        "points": 40,
        "bench": 4,
        "hits": 0,
        "captain_points": 8,
        "captain_raw_points": 8,
        "captain_contribution_points": 16,
        "transfer_gain": 0,
        "autosub_count": 0,
        "event_transfers": 0,
        "team": team,
        "captain_id": 1,
    }
    df = pd.DataFrame(
        [
            {**base, "entry_name": "Low", "gw": 5, "chip": "bboost1", "bench": 8},
            {**base, "entry_name": "Low", "gw": 25, "chip": None},
            {
                **base,
                "entry_name": "Also",
                "gw": 1,
                "chip": "3xc1",
                "captain_contribution_points": 16,
            },
            {**base, "entry_name": "Also", "gw": 10, "chip": "freehit1", "points": 0},
            {**base, "entry_name": "Also", "gw": 26, "chip": None},
        ]
    )
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, {})
    worst = next(a for a in awards if a["Nagroda"] == "Złoty chip, miedziany wynik")
    assert worst["Drużyna"] == "Also"
    assert worst["Wartość"] == "8.0 pkt/aktywacja (16 pkt, 2 aktyw.)"


def test_hoarder_chip_award_skipped_when_no_chips_used():
    team = "[{'player_id': 1, 'multiplier': 2, 'points': 6}]"
    base = {
        "points": 50,
        "bench": 5,
        "hits": 0,
        "captain_points": 10,
        "transfer_gain": 0,
        "autosub_count": 0,
        "event_transfers": 0,
        "team": team,
        "captain_id": 1,
        "chip": None,
    }
    df = pd.DataFrame(
        [
            {**base, "entry_name": "A", "gw": 1},
            {**base, "entry_name": "A", "gw": 25},
            {**base, "entry_name": "B", "gw": 2},
            {**base, "entry_name": "B", "gw": 26},
        ]
    )
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, {})
    titles = _award_titles(awards)
    assert "Chipy? W 2026 jeszcze mam" in titles
    assert "Yolo na każdym chipie" not in titles


def test_season_player_points_by_entry_sums_counted_picks(season_csv, mapping_json):
    df, id_to_name = load_data(season_csv, mapping_json)
    haaland_id = next(pid for pid, name in id_to_name.items() if name == "Haaland")
    haaland_pts = season_player_points_by_entry(df, haaland_id)
    assert haaland_pts["Beta City"] == 40
    assert haaland_pts["Zebra FC"] == 20


def test_season_club_points_by_entry_sums_counted_picks(
    season_csv, mapping_json, bootstrap_map_json
):
    df, _ = load_data(season_csv, mapping_json)
    id_to_team, short_names = load_bootstrap_clubs(bootstrap_map_json)
    leeds_pts = season_club_points_by_entry(df, id_to_team, short_names["LEE"])
    man_utd_pts = season_club_points_by_entry(df, id_to_team, short_names["MUN"])
    assert leeds_pts["Gamma Rovers"] == 38
    assert man_utd_pts["Beta City"] == 37


def test_single_gw_record_awards_describe_metric(season_csv, mapping_json):
    df, id_to_name = load_data(season_csv, mapping_json)
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, id_to_name)
    best_gw = next(a for a in awards if a["Nagroda"] == "Ten GW to nie przypadek")
    assert best_gw["Za co"].startswith("Najlepszy wynik w jednej kolejce")
    assert "GW" in best_gw["Za co"]
    assert best_gw["Wartość"].endswith(" pkt")
    worst_gw = next(a for a in awards if a["Nagroda"] == "Black week? Lajt.")
    assert worst_gw["Za co"].startswith("Najgorszy wynik w jednej kolejce")
    bench_high = next(a for a in awards if a["Nagroda"] == "Ławka > jedenastka (rekord)")
    assert bench_high["Za co"].startswith("Najwięcej punktów na ławce")
    bench_low = next(a for a in awards if a["Nagroda"] == "Ławka: czysto dekoracyjna")
    assert bench_low["Za co"].startswith("Najmniej punktów na ławce")


def test_leeds_and_man_utd_club_awards(season_csv, mapping_json, bootstrap_map_json):
    df, id_to_name = load_data(season_csv, mapping_json)
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, id_to_name, bootstrap_path=bootstrap_map_json)
    leeds = next(a for a in awards if a["Nagroda"] == "Syn Okafora")
    man_utd = next(a for a in awards if a["Nagroda"] == "Witamy w piekle")
    assert leeds["Drużyna"] == "Gamma Rovers"
    assert leeds["Wartość"] == "38 pkt"
    assert leeds["Za co"] == "Najwięcej punktów od zawodników Leeds"
    assert man_utd["Drużyna"] == "Beta City"
    assert man_utd["Wartość"] == "37 pkt"


def test_club_awards_skipped_when_bootstrap_missing(season_csv, mapping_json, tmp_path):
    df, id_to_name = load_data(season_csv, mapping_json)
    agg, _ = build_aggregates(df)
    missing = tmp_path / "no_bootstrap.json"
    awards, _ = build_awards(df, agg, id_to_name, bootstrap_path=missing)
    titles = _award_titles(awards)
    assert "Syn Okafora" not in titles
    assert "Witamy w piekle" not in titles
