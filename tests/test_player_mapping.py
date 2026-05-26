import json

import pytest

from fpl_stats.player_mapping import CLUB_POINT_AWARDS, load_bootstrap_clubs


def test_load_bootstrap_clubs_maps_short_names(bootstrap_map_json):
    id_to_team, short_names = load_bootstrap_clubs(bootstrap_map_json)
    assert id_to_team[1] == 11
    assert id_to_team[2] == 14
    assert short_names["LEE"] == 11
    assert short_names["MUN"] == 14


def test_club_point_awards_cover_configured_short_names():
    assert {short for _, short, _ in CLUB_POINT_AWARDS} == {
        "LEE",
        "MUN",
        "ARS",
        "MCI",
        "TOT",
        "CHE",
    }


def test_load_bootstrap_clubs_requires_teams(tmp_path):
    path = tmp_path / "bootstrap.json"
    path.write_text(json.dumps({"elements": [{"id": 1, "team": 11}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="teams"):
        load_bootstrap_clubs(path)
