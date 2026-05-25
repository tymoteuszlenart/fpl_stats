"""FPL chip naming for 2025/26 double-chip seasons (two uses per chip type)."""

import pandas as pd

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
    ("Triple Captain", TRIPLE_CAPTAIN_CHIPS, "captain_contribution_points", "max"),
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


def captain_contribution_multiplier(chip):
    """FPL captain bonus: 2× normally, 3× on Triple Captain chip."""
    if chip in TRIPLE_CAPTAIN_CHIPS or chip == "3xc":
        return 3
    return 2


def ensure_captain_columns(df):
    """Backfill captain_raw_points / captain_contribution_points from legacy CSV columns."""
    out = df.copy()
    if "captain_raw_points" not in out.columns:
        if "captain_points" not in out.columns:
            raise ValueError("CSV missing captain_points or captain_raw_points column")
        out["captain_raw_points"] = out["captain_points"]
    if "captain_contribution_points" not in out.columns:
        out["captain_contribution_points"] = out["captain_raw_points"] * out["chip"].map(
            captain_contribution_multiplier
        )
    return out


SEASON_CHIP_SLOTS = frozenset(HALF_CHIP_ORDER)
MAX_CHIPS_PER_SEASON = len(HALF_CHIP_ORDER)

CHIP_SLOT_SHORT_LABELS = {
    "3xc1": "3xC (I poł.)",
    "3xc2": "3xC (II poł.)",
    "bboost1": "BB (I poł.)",
    "bboost2": "BB (II poł.)",
    "freehit1": "FH (I poł.)",
    "freehit2": "FH (II poł.)",
    "wildcard1": "WC (I poł.)",
    "wildcard2": "WC (II poł.)",
}


def used_season_chips(chip_series):
    """Half-specific chip slots present in *chip_series*, in display order."""
    used = set(chip_series.dropna()) & SEASON_CHIP_SLOTS
    return [chip for chip in HALF_CHIP_ORDER if chip in used]


def unused_season_chips(chip_series):
    """Half-specific chip slots not present in *chip_series* (2025/26, up to 8)."""
    used = set(chip_series.dropna()) & SEASON_CHIP_SLOTS
    return [chip for chip in HALF_CHIP_ORDER if chip not in used]


def format_chip_slots_summary(slots):
    if not slots:
        return ""
    return ", ".join(CHIP_SLOT_SHORT_LABELS.get(c, c) for c in slots)


def format_unused_chips_summary(unused_slots):
    return format_chip_slots_summary(unused_slots)


def season_chip_usage_by_entry(df):
    """Per manager: distinct half-specific chip activations (0–8). Includes zero-use entries."""
    entries = pd.Index(df["entry_name"].unique())
    used = (
        df.loc[df["chip"].isin(SEASON_CHIP_SLOTS), ["entry_name", "chip"]]
        .groupby("entry_name")["chip"]
        .nunique()
    )
    return used.reindex(entries, fill_value=0).astype(int)
