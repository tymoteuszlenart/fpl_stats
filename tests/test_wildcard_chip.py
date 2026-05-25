import pytest

from fpl_chips import normalize_chip_activation


@pytest.mark.parametrize(
    "chip,gw,expected",
    [
        ("wildcard", 1, "wildcard1"),
        ("wildcard", 19, "wildcard1"),
        ("wildcard", 20, "wildcard2"),
        ("wildcard", 38, "wildcard2"),
        ("bboost", 10, "bboost1"),
        ("bboost", 20, "bboost2"),
        ("freehit", 1, "freehit1"),
        ("freehit", 38, "freehit2"),
        ("3xc", 12, "3xc1"),
        ("3xc", 25, "3xc2"),
        (None, 5, None),
        ("bboost1", 10, "bboost1"),
    ],
)
def test_normalize_chip_activation(chip, gw, expected):
    assert normalize_chip_activation(chip, gw) == expected


def test_normalize_wildcard_chip_alias():
    from fetcher import normalize_wildcard_chip

    assert normalize_wildcard_chip("wildcard", 20) == "wildcard2"
