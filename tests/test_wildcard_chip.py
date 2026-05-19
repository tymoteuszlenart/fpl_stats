import pytest

from fetch_fpl_league_data import normalize_wildcard_chip


@pytest.mark.parametrize(
    "chip,gw,expected",
    [
        ("wildcard", 1, "wildcard1"),
        ("wildcard", 19, "wildcard1"),
        ("wildcard", 20, "wildcard2"),
        ("wildcard", 38, "wildcard2"),
        ("bboost", 10, "bboost"),
        (None, 5, None),
        ("3xc", 12, "3xc"),
    ],
)
def test_normalize_wildcard_chip(chip, gw, expected):
    assert normalize_wildcard_chip(chip, gw) == expected
