# -*- coding: utf-8 -*-
"""Season CSV and player mapping loaders for FPL league reports."""

import pandas as pd

from fpl_chips import ensure_captain_columns, normalize_chips_dataframe
from fpl_season_storage import load_season_dataframe


def load_data(csv_path="csv/fpl_season_data.csv", mapping_path="json/player_id_mapped.json"):
    """Load season CSV and player ID mapping. Returns (df, id_to_name)."""
    print(f"🔄 Ładowanie danych z pliku {csv_path}...")
    try:
        df = load_season_dataframe(csv_path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Plik {csv_path} nie został znaleziony") from exc
    df = normalize_chips_dataframe(df)
    df = ensure_captain_columns(df)
    print(f"✅ Załadowano dane z pliku {csv_path}")

    print(f"🔄 Ładowanie danych z pliku {mapping_path}...")
    try:
        mapping = pd.read_json(mapping_path)
        id_to_name = dict(zip(mapping["id"], mapping["name"]))
        print("✅ Załadowano mapowanie ID na nazwiska zawodników.")
    except Exception as e:
        id_to_name = {}
        print("❌ Błąd podczas ładowania mapowania ID na nazwiska zawodników:", e)

    return df, id_to_name
