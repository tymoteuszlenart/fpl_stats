import pandas as pd
import pytest

from fpl_stats.chips import is_bench_boost_chip
from fpl_stats import build_aggregates, load_data


def test_build_aggregates_aligns_by_entry_name(season_csv, mapping_json):
    df, _ = load_data(season_csv, mapping_json)
    agg, num_gw = build_aggregates(df)

    expected_avg = df.groupby("entry_name")["points"].mean()
    for _, row in agg.iterrows():
        name = row["entry_name"]
        assert row["avg_gw_points"] == pytest.approx(expected_avg[name])
        assert row["avg_bench_points"] == pytest.approx(
            df.groupby("entry_name")["bench"].mean()[name]
        )

    non_bb = df[~df["chip"].apply(is_bench_boost_chip)]
    expected_max_bench = non_bb.groupby("entry_name")["bench"].sum()
    for _, row in agg.iterrows():
        name = row["entry_name"]
        assert row["max_bench_points"] == expected_max_bench.get(name, 0)

    assert num_gw == df["gw"].nunique()


def test_build_aggregates_order_independent():
    """Row order in CSV must not mis-attach groupby means via positional .values."""
    rows = []
    for entry_name, pts in [("Charlie", 40), ("Alice", 50), ("Bob", 60)]:
        rows.append({
            "gw": 1,
            "entry_name": entry_name,
            "points": pts,
            "bench": 1,
            "hits": 0,
            "captain_points": 0,
            "transfer_gain": 0,
            "autosub_count": 0,
            "event_transfers": 0,
            "chip": None,
        })
    df = pd.DataFrame(rows)
    agg, _ = build_aggregates(df)
    by_name = agg.set_index("entry_name")
    assert by_name.loc["Alice", "avg_gw_points"] == 50
    assert by_name.loc["Bob", "avg_gw_points"] == 60
    assert by_name.loc["Charlie", "avg_gw_points"] == 40
