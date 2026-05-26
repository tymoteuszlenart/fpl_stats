# -*- coding: utf-8 -*-
"""FPL player → real club mapping from bootstrap-static snapshots."""

import json
from collections import Counter
from pathlib import Path

import pandas as pd

from fpl_stats.season_storage import team_lists_series

DEFAULT_BOOTSTRAP_PATH = Path("json/player_id_map.json")

# (award title, FPL teams.short_name, label in "Za co" copy)
CLUB_POINT_AWARDS = (
    ("Syn Okafora", "LEE", "Leeds"),
    ("Witamy w piekle", "MUN", "Man Utd"),
    ("Czwarte miejsce to też trofeum", "ARS", "Arsenal"),
    ("Maszyna losująca wylosowała...", "MCI", "Man City"),
    ("Puchar jest w DLC (Season Pass)", "TOT", "Tottenham"),
    ("Kolejny trener, ten sam chaos", "CHE", "Chelsea"),
)


def load_bootstrap_clubs(
    bootstrap_path: str | Path = DEFAULT_BOOTSTRAP_PATH,
) -> tuple[dict[int, int], dict[str, int]]:
    """
    Load player id → FPL team id and short_name → team id from a bootstrap snapshot.

    Returns (id_to_team, team_id_by_short_name). Missing file or shape raises OSError/ValueError.
    """
    path = Path(bootstrap_path)
    with path.open(encoding="utf-8") as file:
        data = json.load(file)

    elements = data.get("elements")
    if not isinstance(elements, list):
        raise ValueError(f"{path}: missing or invalid 'elements' list")

    id_to_team = {
        int(element["id"]): int(element["team"])
        for element in elements
        if "id" in element and "team" in element
    }

    teams = data.get("teams")
    if not isinstance(teams, list):
        raise ValueError(f"{path}: missing or invalid 'teams' list")

    team_id_by_short_name = {
        str(team["short_name"]): int(team["id"])
        for team in teams
        if "short_name" in team and "id" in team
    }
    return id_to_team, team_id_by_short_name


def season_player_points_by_entry(df: pd.DataFrame, player_id: int) -> pd.Series:
    """Sum counted pick points (points × multiplier) for one FPL element per league entry."""
    totals: Counter[str] = Counter()
    player_id = int(player_id)

    for entry_name, team_list in zip(df["entry_name"], team_lists_series(df), strict=False):
        if not team_list:
            continue
        for pick in team_list:
            if pick["multiplier"] <= 0:
                continue
            if int(pick["player_id"]) != player_id:
                continue
            totals[str(entry_name)] += int(pick["points"]) * int(pick["multiplier"])

    if not totals:
        return pd.Series(dtype=int)
    return pd.Series(dict(totals))


def season_club_points_by_entry(
    df: pd.DataFrame,
    id_to_team: dict[int, int],
    club_team_id: int,
) -> pd.Series:
    """Sum counted pick points (points × multiplier) for one real club per league entry."""
    totals: Counter[str] = Counter()

    for entry_name, team_list in zip(df["entry_name"], team_lists_series(df), strict=False):
        if not team_list:
            continue
        for pick in team_list:
            if pick["multiplier"] <= 0:
                continue
            player_id = int(pick["player_id"])
            if id_to_team.get(player_id) != club_team_id:
                continue
            totals[str(entry_name)] += int(pick["points"]) * int(pick["multiplier"])

    if not totals:
        return pd.Series(dtype=int)
    return pd.Series(dict(totals))


def add_season_club_point_awards(df, id_to_team, team_id_by_short_name, add_award):
    """Add one award per configured club when that club has counted pick points in the season."""
    for title, short_name, club_label in CLUB_POINT_AWARDS:
        club_team_id = team_id_by_short_name.get(short_name)
        if club_team_id is None:
            continue
        club_pts = season_club_points_by_entry(df, id_to_team, club_team_id)
        if club_pts.empty:
            continue
        add_award(
            title,
            club_pts.idxmax(),
            f"Najwięcej punktów od zawodników {club_label}",
            f"{int(club_pts.max())} pkt",
        )
