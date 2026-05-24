import pandas as pd

from fpl_chips import (
    MAX_CHIPS_PER_SEASON,
    format_chip_slots_summary,
    format_unused_chips_summary,
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
