"""
Season CSV storage: flat aggregates in one file, normalized picks in a sibling CSV.

The fetcher writes ``csv/fpl_season_data.csv`` (no embedded ``team`` column) and
``csv/fpl_season_picks.csv`` (one row per manager / gameweek / player pick).

Legacy season files may still embed ``team`` as a Python-literal string in the
main CSV; the loader accepts those only after structural validation.
"""

from __future__ import annotations

import ast
import json
import os
from typing import Any

import pandas as pd

PICK_COLUMNS = ("entry_name", "gw", "player_id", "multiplier", "points")
TEAM_PICK_KEYS = frozenset({"player_id", "multiplier", "points"})


def picks_path_for_season_csv(season_csv_path: str) -> str:
    """Sibling picks table path for a given season CSV (e.g. data -> picks)."""
    directory, basename = os.path.split(season_csv_path)
    if basename == "fpl_season_data.csv":
        return os.path.join(directory or ".", "fpl_season_picks.csv")
    stem, ext = os.path.splitext(basename)
    if stem.endswith("_data"):
        stem = stem[: -len("_data")] + "_picks"
    else:
        stem = f"{stem}_picks"
    return os.path.join(directory or ".", stem + ext)


def _normalize_pick_dict(item: dict[str, Any]) -> dict[str, int]:
    extra = set(item.keys()) - TEAM_PICK_KEYS
    if extra:
        raise ValueError(f"unexpected team pick keys: {sorted(extra)}")
    missing = TEAM_PICK_KEYS - set(item.keys())
    if missing:
        raise ValueError(f"missing team pick keys: {sorted(missing)}")
    return {
        "player_id": int(item["player_id"]),
        "multiplier": int(item["multiplier"]),
        "points": int(item["points"]),
    }


def validate_team_list(data: Any) -> list[dict[str, int]]:
    """Validate parsed team data before use in reports."""
    if not isinstance(data, list):
        raise ValueError("team must be a list of pick dicts")
    return [_normalize_pick_dict(item) for item in data]


def parse_team_cell(value: Any) -> list[dict[str, int]] | None:
    """
    Parse a legacy ``team`` CSV cell (JSON or Python literal) with validation.

    Returns None for empty/missing values. Raises ValueError on malformed data.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, list):
        return validate_team_list(value)
    if not isinstance(value, str):
        raise ValueError(f"team must be str or list, got {type(value).__name__}")
    text = value.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(text)
        except (SyntaxError, ValueError) as exc:
            raise ValueError("team cell is not valid JSON or a safe literal") from exc
    return validate_team_list(parsed)


def team_rows_from_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Explode in-memory ``team`` lists into a normalized picks table."""
    records: list[dict[str, Any]] = []
    for row in df.itertuples(index=False):
        team = getattr(row, "team", None)
        if team is None or (isinstance(team, float) and pd.isna(team)):
            continue
        if isinstance(team, str):
            team = parse_team_cell(team)
        if not team:
            continue
        entry_name = row.entry_name
        gw = int(row.gw)
        for pick in team:
            records.append({
                "entry_name": entry_name,
                "gw": gw,
                "player_id": pick["player_id"],
                "multiplier": pick["multiplier"],
                "points": pick["points"],
            })
    return pd.DataFrame(records, columns=list(PICK_COLUMNS))


def attach_team_from_picks(df: pd.DataFrame, picks: pd.DataFrame) -> pd.Series:
    """Build a ``team`` list column from a normalized picks table."""

    def _group_to_team(group: pd.DataFrame) -> list[dict[str, int]]:
        return [
            {
                "player_id": int(r.player_id),
                "multiplier": int(r.multiplier),
                "points": int(r.points),
            }
            for r in group.itertuples(index=False)
        ]

    grouped = (
        picks.groupby(["entry_name", "gw"], sort=False)
        .apply(_group_to_team, include_groups=False)
    )
    keys = list(zip(df["entry_name"], df["gw"]))
    return pd.Series([grouped.get(key) for key in keys], index=df.index, dtype=object)


def load_season_dataframe(
    season_csv_path: str,
    picks_csv_path: str | None = None,
) -> pd.DataFrame:
    """
    Load season CSV and attach ``team`` pick lists.

    Prefers ``fpl_season_picks.csv`` when present; otherwise parses legacy
    ``team`` column cells with :func:`parse_team_cell`.
    """
    df = pd.read_csv(season_csv_path)
    picks_path = picks_csv_path or picks_path_for_season_csv(season_csv_path)

    if os.path.isfile(picks_path):
        picks = pd.read_csv(picks_path)
        for col in PICK_COLUMNS:
            if col not in picks.columns:
                raise ValueError(f"picks file missing column {col!r}: {picks_path}")
        df["team"] = attach_team_from_picks(df, picks)
    elif "team" in df.columns:
        df["team"] = df["team"].apply(parse_team_cell)
    else:
        df["team"] = None

    return df


def write_season_csv_and_picks(rows: list[dict[str, Any]], season_csv_path: str) -> str:
    """
    Write flat season CSV (no ``team`` column) and normalized picks CSV.

    Returns the picks file path.
    """
    df = pd.DataFrame(rows)
    picks_df = team_rows_from_dataframe(df)
    season_df = df.drop(columns=["team"], errors="ignore")
    os.makedirs(os.path.dirname(season_csv_path) or ".", exist_ok=True)
    season_df.to_csv(season_csv_path, index=False)
    picks_path = picks_path_for_season_csv(season_csv_path)
    os.makedirs(os.path.dirname(picks_path) or ".", exist_ok=True)
    picks_df.to_csv(picks_path, index=False)
    return picks_path


def team_lists_series(df: pd.DataFrame) -> pd.Series:
    """Series of validated team pick lists (skips rows with no team)."""
    if "team_list" in df.columns:
        return df["team_list"]

    def _to_list(value: Any) -> list[dict[str, int]] | None:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        if isinstance(value, list):
            return validate_team_list(value)
        return parse_team_cell(value)

    return df["team"].apply(_to_list)
