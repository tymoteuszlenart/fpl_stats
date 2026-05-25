import pandas as pd
import pytest

from fpl_stats.chips import (
    MAX_CHIPS_PER_SEASON,
    format_chip_slots_summary,
    format_unused_chips_summary,
    normalize_chips_dataframe,
    season_chip_efficiency_by_entry,
    season_chip_total_return_by_entry,
    season_chip_usage_by_entry,
    unused_season_chips,
    used_season_chips,
)


def test_unused_second_half_slots_listed_in_order():
    chips = pd.Series(["bboost1", "3xc1", "freehit1", "wildcard1"])
    unused = unused_season_chips(chips)
    assert unused == ["3xc2", "bboost2", "freehit2", "wildcard2"]
    summary = format_unused_chips_summary(unused)
    assert "II poł." in summary
    assert summary.count("II poł.") == 4


def test_used_season_chips_listed_in_order():
    chips = pd.Series(["wildcard2", "bboost1", "3xc1"])
    assert used_season_chips(chips) == ["3xc1", "bboost1", "wildcard2"]
    assert format_chip_slots_summary(used_season_chips(chips)) == "3xC (I poł.), BB (I poł.), WC (II poł.)"


def test_season_chip_usage_caps_at_eight_distinct_slots():
    rows = []
    for i, chip in enumerate(
        ["3xc1", "3xc2", "bboost1", "bboost2", "freehit1", "freehit2", "wildcard1", "wildcard2"]
    ):
        rows.append({"entry_name": "Full", "gw": i + 1, "chip": chip})
    df = pd.DataFrame(rows)
    assert season_chip_usage_by_entry(df)["Full"] == MAX_CHIPS_PER_SEASON


def test_season_chip_return_and_efficiency_metrics():
    team = "[{'player_id': 1, 'multiplier': 2, 'points': 6}]"
    base = {
        "points": 50,
        "bench": 5,
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
    df = pd.DataFrame([
        {**base, "entry_name": "Saver", "gw": 5, "chip": "bboost", "bench": 12},
        {**base, "entry_name": "Saver", "gw": 25, "chip": "bboost", "bench": 8},
        {**base, "entry_name": "Pro", "gw": 1, "chip": "3xc1", "captain_contribution_points": 30},
        {**base, "entry_name": "Pro", "gw": 10, "chip": "wildcard1", "points": 70},
        {**base, "entry_name": "Pro", "gw": 21, "chip": "wildcard2", "points": 90},
        {**base, "entry_name": "Flop", "gw": 2, "chip": "freehit1", "points": 40},
    ])
    df = normalize_chips_dataframe(df)
    usage = season_chip_usage_by_entry(df)
    returns = season_chip_total_return_by_entry(df)
    efficiency = season_chip_efficiency_by_entry(df)

    assert usage["Saver"] == 2
    assert returns["Saver"] == 20  # max bench per BB slot: 12 + 8
    assert efficiency["Saver"] == 10.0

    assert usage["Pro"] == 3
    assert returns["Pro"] == 190  # 30 + 70 + 90
    assert efficiency["Pro"] == pytest.approx(190 / 3)

    assert usage["Flop"] == 1
    assert returns["Flop"] == 40
    assert efficiency["Flop"] == 40.0
