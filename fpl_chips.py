"""FPL chip naming for 2025/26 double-chip seasons (two uses per chip type)."""

CHIP_HALF_SPLIT_GW = 20
SPLITTABLE_CHIPS = frozenset({"wildcard", "bboost", "freehit", "3xc"})

BENCH_BOOST_CHIPS = frozenset({"bboost", "bboost1", "bboost2"})
TRIPLE_CAPTAIN_CHIPS = frozenset({"3xc", "3xc1", "3xc2"})
FREE_HIT_CHIPS = frozenset({"freehit", "freehit1", "freehit2"})

HALF_CHIP_ORDER = (
    "3xc1",
    "3xc2",
    "bboost1",
    "bboost2",
    "freehit1",
    "freehit2",
    "wildcard1",
    "wildcard2",
)

CHIP_CHART_LABELS = {
    "3xc1": "Triple Captain — 1. połowa (najlepsze pojedyncze użycie)",
    "3xc2": "Triple Captain — 2. połowa (najlepsze pojedyncze użycie)",
    "bboost1": "Bench Boost — 1. połowa (najlepsze pojedyncze użycie)",
    "bboost2": "Bench Boost — 2. połowa (najlepsze pojedyncze użycie)",
    "freehit1": "Free Hit — 1. połowa (najlepsze pojedyncze użycie)",
    "freehit2": "Free Hit — 2. połowa (najlepsze pojedyncze użycie)",
    "wildcard1": "Wildcard — 1. połowa (suma pkt w tej połowie)",
    "wildcard2": "Wildcard — 2. połowa (suma pkt w tej połowie)",
}

COMBINED_HALF_CHART_SPECS = (
    ("Bench Boost", BENCH_BOOST_CHIPS, "bench", "max"),
    ("Free Hit", FREE_HIT_CHIPS, "points", "max"),
    ("Triple Captain", TRIPLE_CAPTAIN_CHIPS, "captain_points", "max_triple"),
)


def normalize_chip_activation(chip, gw):
    """Map API chip to half-specific id (GW < 20 → *1, GW >= 20 → *2)."""
    if chip is None:
        return None
    if chip in SPLITTABLE_CHIPS:
        half = 1 if gw < CHIP_HALF_SPLIT_GW else 2
        return f"{chip}{half}"
    return chip


def normalize_chips_dataframe(df):
    """Split legacy unsuffixed chip rows by gameweek (in-place safe copy)."""
    if "chip" not in df.columns:
        return df
    out = df.copy()
    mask = out["chip"].isin(SPLITTABLE_CHIPS)
    if not mask.any():
        return out
    out.loc[mask, "chip"] = [
        normalize_chip_activation(chip, int(gw))
        for chip, gw in zip(out.loc[mask, "chip"], out.loc[mask, "gw"])
    ]
    return out


def is_bench_boost_chip(chip):
    return chip in BENCH_BOOST_CHIPS
