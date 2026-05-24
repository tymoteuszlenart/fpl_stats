import json

import pytest

from fpl_generate_report_v3 import build_awards, build_aggregates, load_data, player_display_name
from map_players_name import build_mapped_players, refresh_from_local_map, sanitize_web_name


def test_sanitize_web_name_strips_diacritics():
    assert sanitize_web_name("Fábio") == "Fabio"
    assert sanitize_web_name("Haaland") == "Haaland"


def test_build_mapped_players_from_elements():
    elements = [
        {"id": 1, "web_name": "Saka"},
        {"id": 2, "web_name": "Ødegaard"},
    ]
    mapped = build_mapped_players(elements)
    assert mapped == [{"id": 1, "name": "Saka"}, {"id": 2, "name": "Odegaard"}]


def test_refresh_from_local_map(tmp_path):
    bootstrap = {"elements": [{"id": 10, "web_name": "Test"}]}
    map_path = tmp_path / "player_id_map.json"
    mapped_path = tmp_path / "player_id_mapped.json"
    map_path.write_text(json.dumps(bootstrap), encoding="utf-8")

    result = refresh_from_local_map(map_path=map_path, mapped_path=mapped_path)

    assert result == [{"id": 10, "name": "Test"}]
    saved = json.loads(mapped_path.read_text(encoding="utf-8"))
    assert saved == result


def test_player_display_name_unknown_id():
    assert player_display_name(999, {1: "Saka"}) == "Gracz #999"
    assert player_display_name(1, {1: "Saka"}) == "Saka"


def test_most_picked_award_unknown_player_id(season_csv, tmp_path):
    """Award still works when mapping has no entries for picked players."""
    unknown_map = tmp_path / "empty_map.json"
    unknown_map.write_text("[]", encoding="utf-8")
    df, id_to_name = load_data(season_csv, str(unknown_map))
    agg, _ = build_aggregates(df)
    awards, _ = build_awards(df, agg, id_to_name)
    picked = next(a for a in awards if a["Nagroda"] == "Bez niego ani rusz")
    assert picked["Drużyna"].startswith("Gracz #")
