import pandas as pd
import pytest

from fpl_stats.season_storage import (
    load_season_dataframe,
    parse_team_cell,
    picks_path_for_season_csv,
    team_rows_from_dataframe,
    validate_team_list,
    write_season_csv_and_picks,
)


def test_picks_path_for_default_season_csv():
    assert picks_path_for_season_csv("csv/fpl_season_data.csv") == "csv/fpl_season_picks.csv"


def test_picks_path_for_fixture_csv():
    path = picks_path_for_season_csv("tests/fixtures/fpl_season_minimal.csv")
    assert path.endswith("fpl_season_minimal_picks.csv")


def test_parse_team_cell_rejects_unsafe_literal():
    with pytest.raises(ValueError, match="team"):
        parse_team_cell("__import__('os').system('x')")


def test_validate_team_list_requires_expected_keys():
    with pytest.raises(ValueError, match="missing"):
        validate_team_list([{"player_id": 1}])


def test_fixture_loads_picks_not_literal_eval(season_csv):
    df = load_season_dataframe(season_csv)
    assert "team" not in pd.read_csv(season_csv).columns
    row = df.iloc[0]
    assert isinstance(row["team"], list)
    assert row["team"][0]["player_id"] == 1


def test_legacy_team_column_still_loads(tmp_path):
    legacy = """gw,points,entry_name,team
1,50,Solo FC,"[{'player_id': 1, 'multiplier': 2, 'points': 6}]"
"""
    path = tmp_path / "legacy.csv"
    path.write_text(legacy, encoding="utf-8")
    df = load_season_dataframe(str(path))
    assert df.iloc[0]["team"][0]["multiplier"] == 2


def test_write_round_trip(tmp_path):
    rows = [{
        "gw": 1,
        "points": 50,
        "entry_name": "A",
        "team": [{"player_id": 10, "multiplier": 2, "points": 6}],
    }]
    season_path = tmp_path / "fpl_season_data.csv"
    picks_path = write_season_csv_and_picks(rows, str(season_path))
    assert picks_path == str(tmp_path / "fpl_season_picks.csv")
    season = pd.read_csv(season_path)
    assert "team" not in season.columns
    loaded = load_season_dataframe(str(season_path))
    assert loaded.iloc[0]["team"] == rows[0]["team"]


def test_team_rows_from_dataframe():
    df = pd.DataFrame([{
        "entry_name": "X",
        "gw": 2,
        "team": [
            {"player_id": 1, "multiplier": 2, "points": 6},
            {"player_id": 2, "multiplier": 0, "points": 0},
        ],
    }])
    picks = team_rows_from_dataframe(df)
    assert len(picks) == 2
    assert set(picks.columns) == {"entry_name", "gw", "player_id", "multiplier", "points"}
