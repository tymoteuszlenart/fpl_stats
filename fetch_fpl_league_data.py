import requests
import pandas as pd
import time
import os
from dotenv import load_dotenv

load_dotenv()
COOKIE = os.getenv("FPL_COOKIE")
LEAGUE_ID = os.getenv("FPL_LEAGUE_ID")

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
    team = [{"player_id":p["element"], "multiplier":p["multiplier"]} for p in picks_data]
    live_points = {e["id"]: e["stats"]["total_points"] for e in live["elements"]}

    # Build team with points and identify captain/vice-captain
    captain_id = next((pd["element"] for pd in picks_data if pd.get("is_captain")), None)
    vice_captain_id = next((pd["element"] for pd in picks_data if pd.get("is_vice_captain")), None)

    team_with_points = [
        {
            "player_id": p["player_id"],
            "multiplier": p["multiplier"],
            "points": live_points.get(p["player_id"], 0)
        }
        for p in team
    ]

    # Determine captain points: if captain played (multiplier > 1), use captain; else use vice-captain
    captain_played = any(p["player_id"] == captain_id and p["multiplier"] > 1 for p in team_with_points)
    if captain_played:
        captain_points = live_points.get(captain_id, 0)
    else:
        captain_id = vice_captain_id
        captain_points = live_points.get(vice_captain_id, 0)

    history = picks.get("entry_history", {})
    automatic_subs = picks.get("automatic_subs", [])
    chip = picks.get("active_chip", None)

    if chip == "bboost":
        bench_ids = [p["element"] for p in picks_data if p["position"] > 11]
        element_stats = live.get("elements", [])
        live_points = {e["id"]: e["stats"]["total_points"] for e in element_stats}
        bench_boost_points = sum(live_points.get(e, 0) for e in bench_ids)
        bench = bench_boost_points
    else:
        bench = history.get("points_on_bench")

    
    in_ids = [t["element_in"] for t in automatic_subs]
    out_ids = [t["element_out"] for t in automatic_subs]

    transfer_gain = 0
    for in_id, out_id in zip(in_ids, out_ids):
        in_pts = next((e["stats"]["total_points"] for e in live["elements"] if e["id"] == in_id), 0)
        out_pts = next((e["stats"]["total_points"] for e in live["elements"] if e["id"] == out_id), 0)
        transfer_gain += (in_pts - out_pts)

    return {
        "gw": gw,
        "points": history.get("points"),
        "team": team_with_points,
        "bench": bench,
        "hits": history.get("event_transfers_cost"),
        "event_transfers": history.get("event_transfers"),
        "chip": chip,
        "autosub_count": len(automatic_subs),
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
        entry_name = member["entry_name"]
        print(f"Pobieram dane drużyny: {entry_name}")
        for gw in range(1, NUM_GW + 1):
            try:
                data = get_manager_data(entry_id, gw)
                data.update({
                    "player_name": name,
                    "entry_name": entry_name
                })
                if data["chip"] == "wildcard":
                    data.update({"chip": "wildcard1"}) if data["gw"] < 20 else data.update({"chip": "wildcard2"})
                all_data.append(data)
                time.sleep(0.3)
            except Exception as e:
                print(f"❌ Błąd podczas pobierania danych dla {entry_name} GW{gw}: {e}")
                continue

    pd.DataFrame(all_data).to_csv(output_file, index=False)
    print(f"Zapisano dane do {output_file}")

if __name__ == "__main__":
    main()