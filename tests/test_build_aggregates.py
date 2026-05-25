"""Regression tests for per-manager aggregate alignment (issue #8)."""

import pandas as pd
import pytest

from fpl_stats import build_aggregates


def _minimal_season_df(rows):
    """Build a minimal season DataFrame matching build_aggregates expectations."""
    return pd.DataFrame(rows)


@pytest.fixture
def uneven_gw_and_bboost_fixture():
    """
    Managers with uneven GW coverage and one manager only on Bench Boost rows.

    Alpha: 3 GWs, 30 pts each -> avg 30.0
    Beta: 5 GWs, 10 pts each -> avg 10.0
    Gamma: only bboost rows -> excluded from non-bboost bench sum (expect 0)
    Delta: one non-bboost GW with bench 7
    """
    rows = []
    for gw in range(1, 4):
        rows.append({
            "entry_name": "Alpha",
            "gw": gw,
            "points": 30,
            "bench": 2,
            "hits": 0,
            "captain_points": 0,
            "transfer_gain": 0,
            "autosub_count": 0,
            "event_transfers": 0,
            "chip": "",
        })
    for gw in range(1, 6):
        rows.append({
            "entry_name": "Beta",
            "gw": gw,
            "points": 10,
            "bench": 100,
            "hits": 0,
            "captain_points": 0,
            "transfer_gain": 0,
            "autosub_count": 0,
            "event_transfers": 0,
            "chip": "",
        })
    for gw in range(1, 3):
        rows.append({
            "entry_name": "Gamma",
            "gw": gw,
            "points": 50,
            "bench": 999,
            "hits": 0,
            "captain_points": 0,
            "transfer_gain": 0,
            "autosub_count": 0,
            "event_transfers": 0,
            "chip": "bboost",
        })
    rows.append({
        "entry_name": "Delta",
        "gw": 1,
        "points": 20,
        "bench": 7,
        "hits": 0,
        "captain_points": 0,
        "transfer_gain": 0,
        "autosub_count": 0,
        "event_transfers": 0,
        "chip": "",
    })
    return _minimal_season_df(rows)


def test_aggregate_columns_aligned_by_entry_name(uneven_gw_and_bboost_fixture):
    df = uneven_gw_and_bboost_fixture
    agg, num_gw = build_aggregates(df)

    assert num_gw == 5

    by_name = agg.set_index("entry_name")

    assert by_name.loc["Alpha", "avg_gw_points"] == pytest.approx(30.0)
    assert by_name.loc["Beta", "avg_gw_points"] == pytest.approx(10.0)
    assert by_name.loc["Gamma", "avg_gw_points"] == pytest.approx(50.0)

    assert by_name.loc["Alpha", "avg_bench_points"] == pytest.approx(2.0)
    assert by_name.loc["Beta", "avg_bench_points"] == pytest.approx(100.0)
    assert by_name.loc["Gamma", "avg_bench_points"] == pytest.approx(999.0)

    # Non-bboost bench sums: Alpha 3*2=6, Beta 5*100=500, Gamma none -> 0, Delta 7
    assert by_name.loc["Alpha", "max_bench_points"] == 6
    assert by_name.loc["Beta", "max_bench_points"] == 500
    assert by_name.loc["Gamma", "max_bench_points"] == 0
    assert by_name.loc["Delta", "max_bench_points"] == 7


def test_max_bench_points_not_misassigned_when_manager_missing_from_filtered_groupby(
    uneven_gw_and_bboost_fixture,
):
    """Positional .values would mis-assign when a manager has no non-bboost rows."""
    df = uneven_gw_and_bboost_fixture
    agg, _ = build_aggregates(df)
    gamma_row = agg.loc[agg["entry_name"] == "Gamma"].iloc[0]
    beta_row = agg.loc[agg["entry_name"] == "Beta"].iloc[0]

    assert gamma_row["max_bench_points"] == 0
    assert beta_row["max_bench_points"] == 500
    assert gamma_row["max_bench_points"] != beta_row["max_bench_points"]
