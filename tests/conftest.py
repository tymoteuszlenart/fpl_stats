from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def season_csv(fixtures_dir):
    return str(fixtures_dir / "fpl_season_minimal.csv")


@pytest.fixture
def mapping_json(fixtures_dir):
    return str(fixtures_dir / "player_id_mapped.json")


@pytest.fixture
def bootstrap_map_json(fixtures_dir):
    return str(fixtures_dir / "player_id_map_minimal.json")
