import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import os

df = pd.read_csv("csv/fpl_season_data.csv")
num_gameweeks = df["gw"].nunique()

# Sumary statistics for each manager
agg = df.groupby("player_name").agg({
    "points": "sum",
    "bench": "sum",
    "hits": "sum",
    "captain_points": "sum",
    "transfer_gain": "sum"
}).reset_index()

agg["avg_gw_points"] = df.groupby("player_name")["points"].mean().values
agg["efficiency"] = (agg["points"] - agg["hits"]) / num_gameweeks
agg["transfer_loss"] = df.groupby("player_name")["transfer_gain"].apply(lambda x: x[x < 0].sum()).reset_index(drop=True)

# Best and worst GW performance
best = df.loc[df.groupby("gw")["points"].idxmax()].player_name.value_counts()
worst = df.loc[df.groupby("gw")["points"].idxmin()].player_name.value_counts()
agg["best_gw_count"] = agg["player_name"].map(best).fillna(0).astype(int)
agg["worst_gw_count"] = agg["player_name"].map(worst).fillna(0).astype(int)

# 1st and 2nd half of the season
first_half = df[df["gw"] <= 19].groupby("player_name")["points"].sum()
second_half = df[df["gw"] > 19].groupby("player_name")["points"].sum()
agg["runda_1"] = agg["player_name"].map(first_half)
agg["runda_2"] = agg["player_name"].map(second_half)
agg["roznica_rund"] = agg["runda_2"] - agg["runda_1"]

# Load player ID mapping
try:
    mapping_df = pd.read_json("json/player_id_mapped.json", orient='records')
    id_to_name = dict(zip(mapping_df["id"], mapping_df["name"]))
except:
    id_to_name = {}

# Ligowe Steczki - Award data structure
award_data = []

def add_award(title, player, reason, value=None):
    award_data.append({
        "Kategoria": title,
        "Zwycięzca": player,
        "Kryterium": reason,
        "Wartość": value if value else ""
    })

# Categories
add_award("Nagroda Salaha",
          agg.sort_values("captain_points", ascending=False).iloc[0]["player_name"],
          "Najwięcej punktów kapitana",
          f'{int(agg["captain_points"].max())}')

add_award("Nagroda Mykolenki",
          agg.sort_values("bench", ascending=False).iloc[0]["player_name"],
          "Najwięcej punktów na ławce",
          f'{int(agg["bench"].max())}')

add_award("Król Hitów",
          agg.sort_values("hits", ascending=False).iloc[0]["player_name"],
          "Najwięcej punktów z hitów -4",
          f'{int(agg["hits"].max())}')

add_award("Mam czutkę",
          agg.sort_values("transfer_gain", ascending=False).iloc[0]["player_name"],
          "Największy przyrost punktowy z transferów",
          f'{int(agg["transfer_gain"].max())}')

#add_award("Transferowy Bankrut",
#          agg.sort_values("transfer_loss", ascending=True).iloc[0]["player_name"],
#          "Największa strata punktowa na transferach",
#          f'{int(agg["transfer_loss"].min())}')

add_award("WSZYSCY SĄ W TYLE",
          agg.sort_values("best_gw_count", ascending=False).iloc[0]["player_name"],
          "Najwięcej razy najlepszy w kolejce",
          f'{int(agg["best_gw_count"].max())}')

add_award("Pierwszy sezon taki jest",
          agg.sort_values("worst_gw_count", ascending=False).iloc[0]["player_name"],
          "Najwięcej razy najgorszy w kolejce",
          f'{int(agg["worst_gw_count"].max())}')

add_award("Budzi się jak City",
          agg.sort_values("roznica_rund", ascending=False).iloc[0]["player_name"],
          "Największy progres między rundami",
          f'{int(agg["roznica_rund"].max())}')

add_award("Nie sprint a maraton",
          agg.sort_values("roznica_rund", ascending=True).iloc[0]["player_name"],
          "Największy regres między rundami",
          f'{int(agg["roznica_rund"].min())}')

add_award("Steczek Roku",
          agg.sort_values("efficiency", ascending=False).iloc[0]["player_name"],
          "Najwyższa efektywność",
          f'{agg["efficiency"].max():.2f}')

# Lowest and highest scores in a GW
min_row = df.loc[df["points"].idxmin()]
max_row = df.loc[df["points"].idxmax()]
bench_max = df.loc[df["bench"].idxmax()]
add_award("Najniższy wynik kolejki w sezonie", min_row["player_name"], f"GW{min_row['gw']}", f'{min_row["points"]} pkt')
add_award("Najwyższy wynik kolejki w sezonie", max_row["player_name"], f"GW{max_row['gw']}", f'{max_row["points"]} pkt')
add_award("Najwyższy wynik kolejki na ławce w sezonie", bench_max["player_name"], f"GW{bench_max["gw"]}", f'{bench_max["bench"]} pkt')

# Top 30 captains choices of season
top_captains = df.groupby(["player_name", "captain_id"])["captain_points"].max().reset_index()
top_captains = top_captains.sort_values("captain_points", ascending=False).head(30)
top_captains["captain_name"] = top_captains["captain_id"].map(id_to_name).fillna(top_captains["captain_id"].astype(str))
idx = df.groupby(["player_name", "captain_id"])["captain_points"].idxmax()
top_captain_rows = df.loc[idx, ["player_name", "captain_id", "captain_points", "gw"]]
top_captains = top_captains.merge(top_captain_rows, on=["player_name", "captain_id", "captain_points"], how="left")
top_captains["opis"] = (
    top_captains["player_name"] + " – " +
    top_captains["captain_name"] + " – " +
    "GW" + top_captains["gw"].astype(str) + " – " +
    top_captains["captain_points"].astype(int).astype(str) + " pkt"
)

# PDF
os.makedirs("fpl_output", exist_ok=True)
with PdfPages("fpl_output/fpl_sezon_podsumowanie.pdf") as pdf:

    sns.set(style="whitegrid")
    plt.rcParams.update({'axes.titlesize': 14, 'axes.labelsize': 12})

    wykresy = [
        ("bench", "Punkty zawodników na ławce I", "Blues"),
        ("hits", "Ilość hitów I", "Reds"),
        ("captain_points", "Punkty kapitanów I", "Purples"),
        ("transfer_gain", "Zysk punktów na transferach I", "Greens"),
        ("transfer_loss", "Strata punktów na transferach I", "Oranges"),
        ("best_gw_count", "Ilość najlepszych wyników w kolejce I", "Greens"),
        ("worst_gw_count", "Ilość najgorszych wyników w kolejce I", "Greys"),
        ("avg_gw_points", "Średnia punktowa", "Blues"),
        ("efficiency", "Ranking efektywności", "cividis")
    ]

    for kolumna, tytul, palette in wykresy:
        plt.figure(figsize=(10, 6))
        d = agg.sort_values(kolumna, ascending=False)
        ax = sns.barplot(data=d, x=kolumna, y="player_name", hue="player_name", dodge=False, legend=False, palette=palette)

        integer_only = tytul.endswith(" I")
        for i, v in enumerate(d[kolumna]):
            txt = f"{int(v)}" if integer_only else f"{v:.1f}"
            ax.text(v + 0.5, i, txt, color='black', va='center')

        plt.title(tytul.replace(" I", ""))
        plt.xlabel("")
        plt.ylabel("")
        plt.tight_layout()
        pdf.savefig()
        plt.close()

    # Summary statistics table
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis("off")
    table = ax.table(cellText=agg.round(2).values,
                     colLabels=agg.columns,
                     loc="center",
                     cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(6)
    table.scale(1.2, 2.25)
    plt.title("Statystyki zbiorcze menedżerów")
    pdf.savefig()
    plt.close()

    # Ligowe Steczki - Awards table
    awards_df = pd.DataFrame(award_data)
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.axis("off")
    table = ax.table(cellText=awards_df.values,
                     colLabels=awards_df.columns,
                     loc="center",
                     cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 2.25)
    plt.title("Ligowe Steczki – sezonowe wyróżnienia", fontsize=16)
    pdf.savefig()
    plt.close()

    # Ranking TOP 30 captains choices
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.axis("off")
    table = ax.table(cellText=top_captains[["opis"]].values,
                     colLabels=["TOP 30 wyborów kapitańskich"],
                     loc="center",
                     cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.5)
    pdf.savefig()
    plt.close()

print("📄 Zapisano fpl_output/fpl_sezon_podsumowanie.pdf")
