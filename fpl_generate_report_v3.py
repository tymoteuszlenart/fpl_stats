# -*- coding: utf-8 -*-
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import os
from collections import Counter
from ast import literal_eval

# Reading the CSV file
print("🔄 Ładowanie danych z pliku csv/fpl_season_data.csv...")
try:
    df = pd.read_csv("csv/fpl_season_data.csv")
    print("✅ Załadowano dane z pliku csv/fpl_season_data.csv")
except FileNotFoundError:
    print("❌ Plik csv/fpl_season_data.csv nie został znaleziony")
    exit()

# Mapping player IDs to names
print("🔄 Ładowanie danych z pliku json/player_id_mapped.json...")
try:
    mapping = pd.read_json("json/player_id_mapped.json")
    id_to_name = dict(zip(mapping["id"], mapping["name"]))
    print("✅ Załadowano mapowanie ID na nazwiska zawodników.")
except Exception as e:
    id_to_name = {}
    print("❌ Błąd podczas ładowania mapowania ID na nazwiska zawodników:", e)

num_gw = df["gw"].nunique()

# Main aggregation
agg = df.groupby("entry_name").agg({
    "points": "sum",
    "bench": "sum",
    "hits": "sum",
    "captain_points": "sum",
    "transfer_gain": "sum",
    "autosub_count": "sum",
    "event_transfers": "sum"
}).reset_index()

agg["avg_gw_points"] = df.groupby("entry_name")["points"].mean().values
agg["efficiency"] = (agg["points"] - agg["hits"]) / num_gw
agg["transfer_loss"] = df.groupby("entry_name")["transfer_gain"].apply(lambda x: x[x < 0].sum()).reset_index(drop=True)
agg["total_hits"] = agg["entry_name"].map(
    df.groupby("entry_name")["hits"].sum().divide(4).astype(int)
)

# Best and worst GWs
best = df.loc[df.groupby("gw")["points"].idxmax()].entry_name.value_counts()
worst = df.loc[df.groupby("gw")["points"].idxmin()].entry_name.value_counts()
agg["best_gw_count"] = agg["entry_name"].map(best).fillna(0).astype(int)
agg["worst_gw_count"] = agg["entry_name"].map(worst).fillna(0).astype(int)

# Points difference between rounds
first = df[df["gw"] <= 19].groupby("entry_name")["points"].sum()
second = df[df["gw"] > 19].groupby("entry_name")["points"].sum()
agg["runda_1"] = agg["entry_name"].map(first)
agg["runda_2"] = agg["entry_name"].map(second)
agg["roznica_rund"] = agg["runda_2"] - agg["runda_1"]

# Awards
awards = []

def add_award(title, team, reason, value):
    awards.append({"Nagroda": title, "Drużyna": team, "Za co": reason, "Wartość": value})

add_award("Kto na kapitanie?",
          agg.sort_values("captain_points", ascending=False).iloc[0]["entry_name"],
          "Najwięcej punktów z kapitana",
          f'{int(agg["captain_points"].max())}')

add_award("Mykolenko pierwsza asysta w życiu a ja...",
          agg.sort_values("bench", ascending=False).iloc[0]["entry_name"],
          "Najwięcej punktów na ławce",
          f'{int(agg["bench"].max())}')

add_award("-4, -8 czy -12... A kto by to liczył?",
          agg.sort_values("hits", ascending=False).iloc[0]["entry_name"],
          "Najwięcej punktów z hitów -4",
          f'{int(agg["hits"].max())}')

add_award("Słuchaj mam czutkę!",
          agg.sort_values("transfer_gain", ascending=False).iloc[0]["entry_name"],
          "Najwięcej punktów z transferów",
          f'{int(agg["transfer_gain"].max())}')

add_award("WSZYSCY SĄ W TYLE!!! NA CZELE",
          agg.sort_values("best_gw_count", ascending=False).iloc[0]["entry_name"],
          "Najwięcej razy najlepszy w kolejce",
          f'{int(agg["best_gw_count"].max())}')

add_award("Pierwsze sezony takie są",
          agg.sort_values("worst_gw_count", ascending=False).iloc[0]["entry_name"],
          "Najwięcej razy najgorszy w kolejce",
          f'{int(agg["worst_gw_count"].max())}')

add_award("Budzi się jak City",
          agg.sort_values("roznica_rund", ascending=False).iloc[0]["entry_name"],
          "Największy progres między pierwszą a drugą rundą",
          f'{int(agg["roznica_rund"].max())}')

add_award("Pomylił sprint z maratonem",
          agg.sort_values("roznica_rund", ascending=True).iloc[0]["entry_name"],
          "Największy regres między pierwszą a drugą rundą",
          f'{int(agg["roznica_rund"].min())}')

add_award("Steczek Roku",
          agg.sort_values("efficiency", ascending=False).iloc[0]["entry_name"],
          "Najwyższa efektywność",
          f'{agg["efficiency"].max():.2f}')

add_award("Jak to mówią: super sub!", 
          agg.sort_values("autosub_count", ascending=False).iloc[0]["entry_name"],
          "Najwięcej trafionych autosubów", 
          int(agg["autosub_count"].max()))

add_award("Jeszcze jeden transferek...", 
          agg.sort_values("event_transfers", ascending=False).iloc[0]["entry_name"],
          "Najwięcej wykonanych transferów", 
          int(agg["event_transfers"].max()))

bb = df[df["chip"] == "bboost"]
if not bb.empty:
    best_bb = bb.sort_values("bench", ascending=False).iloc[0]
    add_award("Mykolenko w końcu punktuje", 
              best_bb["entry_name"],
              f"Najwięcej punktów z ławki (GW {int(best_bb['gw'])})", 
              f"{int(best_bb['bench'])} pkt")

tc = df[df["chip"] == "3xc"]
if not tc.empty:
    best_tc = tc.sort_values("captain_points", ascending=False).iloc[0]
    add_award("Salah czy nie Salah?", 
              best_tc["entry_name"],
              f"Najwięcej pkt kapitana z 3xC (GW {int(best_tc['gw'])})", 
              f"{int(best_tc['captain_points']) * 3} pkt")

df["prev_points"] = df.sort_values(["entry_name", "gw"]).groupby("entry_name")["points"].shift(1)
fh = df[df["chip"] == "freehit"]
if not fh.empty:
    best_fh = fh.sort_values("points", ascending=False).iloc[0]
    add_award("Upolowane", 
              best_fh["entry_name"],
              f"Najwięcej punktów z Free Hit (GW {int(best_fh['gw'])})", 
              f"{int(best_fh['points'])} pkt")

df["team_list"] = df["team"].dropna().apply(literal_eval)
all_picked = df["team_list"].explode()
top_player_id = all_picked.value_counts().idxmax()
top_player_name = id_to_name.get(top_player_id, str(top_player_id))
top_count = all_picked.value_counts().max()
add_award("Bez niego ani rusz", 
          top_player_name, 
          "Najczęściej wybierany zawodnik (11 podstawowych)", 
          f"{top_count} razy")

# Lowest and highest scores in a GW
min_row = df.loc[df["points"].idxmin()]
max_row = df.loc[df["points"].idxmax()]
bench_max = df.loc[df["bench"].idxmax()]
add_award("Najniższy wynik w sezonie", min_row["entry_name"], f"GW{min_row['gw']}", f'{min_row["points"]} pkt')
add_award("Najwyższy wynik w sezonie", max_row["entry_name"], f"GW{max_row['gw']}", f'{max_row["points"]} pkt')
add_award("Najwyższy wynik ławki w sezonie", bench_max["entry_name"], f"GW{bench_max["gw"]}", f'{bench_max["bench"]} pkt')

# Top 30 captains choices of season
top_captains = df.groupby(["entry_name", "captain_id"])["captain_points"].max().reset_index()
top_captains = top_captains.sort_values("captain_points", ascending=False).head(30)
top_captains["captain_name"] = top_captains["captain_id"].map(id_to_name).fillna(top_captains["captain_id"].astype(str))
idx = df.groupby(["entry_name", "captain_id"])["captain_points"].idxmax()
top_captain_rows = df.loc[idx, ["entry_name", "captain_id", "captain_points", "gw"]]
top_captains = top_captains.merge(top_captain_rows, on=["entry_name", "captain_id", "captain_points"], how="left")
top_captains["desc"] = (
    top_captains["entry_name"] + " – " +
    top_captains["captain_name"] + " – " +
    top_captains["captain_points"].astype(int).astype(str) + " pkt - " +
    "GW" + top_captains["gw"].astype(str)    
)

# Create output directory if it doesn't exist
os.makedirs("fpl_output", exist_ok=True)

# Generate PDF report
print("🔄 Tworzenie raportu w PDF...")
with PdfPages("fpl_output/fpl_sezon_podsumowanie.pdf") as pdf:
    sns.set(style="whitegrid")
    plt.rcParams.update({'axes.titlesize': 16})

    # Main summary table
    for col, title, palette in [
        ("bench", "Punkty zawodników na ławce I", "rocket"),
        ("total_hits", "Ilość hitów I", "mako"),
        ("captain_points", "Punkty kapitanów I", "flare"),
        ("best_gw_count", "Ilość najlepszych wyników w kolejce I", "crest"),
        ("worst_gw_count", "Ilość najgorszych wyników w kolejce I", "magma"),
        ("avg_gw_points", "Średnia punktowa", "viridis"),
        ("efficiency", "Ranking efektywności", "cividis"),
    ]:
        d = agg.sort_values(col, ascending=False)
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=d, x=col, y="entry_name", hue="entry_name", legend=False, palette=palette)
        for i, v in enumerate(d[col]):
            if not pd.isna(v):
                ax.text(v + 0.5, i, f"{int(v) if title.endswith(' I') else f'{v:.1f}'}", va='center')
        plt.title(title.replace(" I", ""))
        plt.tight_layout()
        pdf.savefig()
        plt.close()

    chip_names = {
        "3xc": "Triple Captain",
        "bboost": "Bench Boost",
        "freehit": "Free Hit",
        "manager": "Assistant Manager",
        "wildcard1": "Wildcard - 1st Round",
        "wildcard2": "Wildcard - 2nd Round"
    }

    # Chips usage
    for chip in ["3xc", "bboost", "freehit", "manager", "wildcard1", "wildcard2"]:
        chip_df = df[df["chip"] == chip]
        if not chip_df.empty:
            agg_chip = chip_df.groupby("entry_name")["points"].mean().reset_index()
            d = agg_chip.sort_values("points", ascending=False)
            plt.figure(figsize=(10, 6))
            ax = sns.barplot(data=d, x="points", y="entry_name", hue="entry_name", legend=False, palette='cubehelix')
            for i, v in enumerate(d["points"]):
                if not pd.isna(v):
                    ax.text(v + 0.5, i, f"{int(v)}", va='center')
            plt.title(f"Najskuteczniejsi gracze z chipem: {chip_names.get(chip, chip)}")
            plt.tight_layout()
            pdf.savefig()
            plt.close()

    # Points distribution
    all_managers = df["entry_name"].unique()
    wc1_df = df[df["chip"] == "wildcard1"]
    wc2_df = df[df["chip"] == "wildcard2"]

    # Summing points for wildcards
    wc1_points = wc1_df.groupby("entry_name")["points"].sum()
    wc2_points = wc2_df.groupby("entry_name")["points"].sum()
    wildcards = pd.DataFrame(index=all_managers)
    wildcards["Wildcard 1"] = wc1_points
    wildcards["Wildcard 2"] = wc2_points
    wildcards = wildcards.fillna(0).astype(int)

    # Plotting wildcards usage
    plt.figure(figsize=(10, 6))
    wildcards_sorted = wildcards.sort_values("Wildcard 1" if wildcards["Wildcard 1"].sum() > wildcards["Wildcard 2"].sum() else "Wildcard 2", ascending=False)
    ax = wildcards_sorted.plot(kind="barh", stacked=False, ax=plt.gca(), colormap="Set2")
    
    # Adding text labels for wildcards
    for i, (index, row) in enumerate(wildcards_sorted.iterrows()):
        wc1 = row["Wildcard 1"]
        wc2 = row["Wildcard 2"]
        if wc1 > 0:
            ax.text(wc1 + 1, i - 0.2, str(wc1), va='center', fontsize=9)
        if wc2 > 0:
            ax.text(wc2 + 1, i + 0.2, str(wc2), va='center', fontsize=9)
    
    plt.title("Wyniki graczy po użyciu Wildcard 1 i 2")
    plt.xlabel("Punkty zdobyte w GW z wildcardem")
    plt.ylabel("Drużyna")
    plt.tight_layout()
    pdf.savefig()
    plt.close()

    # Ligowe Steczki – awards
    for award in awards:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.axis("off")
        ax.set_facecolor("#f9f7f0")  # jasne tło

        # Tytuł nagrody
        ax.text(0.5, 0.85, f"{award['Nagroda']}", fontsize=22, ha='center', weight='bold', color="#333")

        # Treść
        ax.text(0.5, 0.6, f"Drużyna: {award['Drużyna']}", fontsize=16, ha='center')
        ax.text(0.5, 0.45, f"Za co: {award['Za co']}", fontsize=14, ha='center', wrap=True)
        ax.text(0.5, 0.28, f"Wartość: {award['Wartość']}", fontsize=14, ha='center')

        # Ramka dekoracyjna
        rect = plt.Rectangle((0.02, 0.02), 0.96, 0.96, transform=ax.transAxes,
                            fill=False, color="#c9a227", linewidth=4, linestyle="-")
        ax.add_patch(rect)

        plt.tight_layout()
        pdf.savefig()
        plt.close()

    # Captains choices table
    fig, ax = plt.subplots(figsize=(6, 12))
    ax.axis("off")
    table = ax.table(cellText=top_captains[["desc"]].values,
                     colLabels=["TOP 30 wyborów kapitańskich"],
                     loc="center",
                     cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 2)
    pdf.savefig()
    plt.close()

print("✅ Zapisano: fpl_output/fpl_sezon_podsumowanie.pdf")