import requests
import pandas as pd
import time
import os
from dotenv import load_dotenv

load_dotenv()
COOKIE = os.getenv("FPL_COOKIE")
LEAGUE_ID = os.getenv("LEAGUE_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Cookie": COOKIE
}

NUM_GW = 38
output_file = "csv/fpl_season_data.csv"
os.makedirs("csv", exist_ok=True)

def get_league_entries(league_id):
    entries = []
    page = 1
    while True:
        url = f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/?page_standings={page}"
        res = requests.get(url, headers=HEADERS)
        data = res.json()
        entries.extend(data["standings"]["results"])
        if not data["standings"]["has_next"]:
            break
        page += 1
    return entries

def get_manager_data(entry_id, gw):
    picks_url = f"https://fantasy.premierleague.com/api/entry/{entry_id}/event/{gw}/picks/"
    live_url = f"https://fantasy.premierleague.com/api/event/{gw}/live/"

    picks = requests.get(picks_url, headers=HEADERS).json()
    live = requests.get(live_url, headers=HEADERS).json()

    picks_data = picks.get("picks", [])
    history = picks.get("entry_history", {})
    captain_id = next((p["element"] for p in picks_data if p["is_captain"]), None)
    captain_points = next((e["stats"]["total_points"] for e in live["elements"] if e["id"] == captain_id), 0)

    transfers = picks.get("automatic_subs", [])
    in_ids = [t["element_in"] for t in transfers]
    out_ids = [t["element_out"] for t in transfers]

    transfer_gain = 0
    for in_id, out_id in zip(in_ids, out_ids):
        in_pts = next((e["stats"]["total_points"] for e in live["elements"] if e["id"] == in_id), 0)
        out_pts = next((e["stats"]["total_points"] for e in live["elements"] if e["id"] == out_id), 0)
        transfer_gain += (in_pts - out_pts)

    return {
        "gw": gw,
        "points": history.get("points"),
        "bench": history.get("points_on_bench"),
        "hits": history.get("event_transfers_cost"),
        "captain_id": captain_id,
        "captain_points": captain_points,
        "transfer_in_ids": in_ids,
        "transfer_out_ids": out_ids,
        "transfer_gain": transfer_gain
    }

def main():
    league = get_league_entries(LEAGUE_ID)
    all_data = []

    for member in league:
        entry_id = member["entry"]
        name = member["player_name"]
        print(f"Pobieram dane gracza: {name}")
        for gw in range(1, NUM_GW + 1):
            try:
                data = get_manager_data(entry_id, gw)
                data.update({"player_name": name})
                all_data.append(data)
                time.sleep(0.3)
            except:
                print(f"Błąd: {name} GW{gw}")
                continue

    pd.DataFrame(all_data).to_csv(output_file, index=False)
    print(f"Zapisano dane do {output_file}")

if __name__ == "__main__":
    main()
