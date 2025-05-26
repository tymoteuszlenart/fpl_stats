import pandas as pd

# Load static players data
try:
    mapping_df = pd.read_json("../json/player_id_mapped.json", orient='records')
    id_to_name = dict(zip(mapping_df["id"], mapping_df["name"]))
    print("Mapowanie ID zawodników wczytane pomyślnie.")
    print(id_to_name.get(1))  # Example usage to check if the mapping works
except Exception as e:
    id_to_name = {}
    print("Nie udało się wczytać mapowania ID zawodników. Używam domyślnego.")
    print(f"Błąd: {e}")