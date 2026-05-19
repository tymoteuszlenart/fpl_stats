# -*- coding: utf-8 -*-
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import os
from collections import Counter
from ast import literal_eval
from weasyprint import HTML
import datetime

# Set season dates
first_half_season_year = int(datetime.datetime.now().strftime("%Y")) - 1
second_half_season_year = datetime.datetime.now().strftime("%Y")
season = str(first_half_season_year) + "/" + second_half_season_year

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

# Adding additional columns
agg["avg_gw_points"] = df.groupby("entry_name")["points"].mean().values
agg["avg_bench_points"] = df.groupby("entry_name")["bench"].mean().values
agg["efficiency"] = (agg["points"] - agg["hits"]) / num_gw
agg["transfer_loss"] = df.groupby("entry_name")["transfer_gain"].apply(lambda x: x[x < 0].sum())
agg["total_hits"] = agg["entry_name"].map(
    df.groupby("entry_name")["hits"].sum().divide(4).astype(int)
)
agg["max_bench_points"] = df[df["chip"] != "bboost"].groupby("entry_name")["bench"].sum().values

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
          f'{int(agg["captain_points"].max())} pkt')

add_award("Mykolenko pierwsza asysta w życiu a ja...",
          agg.sort_values("max_bench_points", ascending=False).iloc[0]["entry_name"],
          "Najwięcej punktów na ławce",
          f'{int(agg["max_bench_points"].max())} pkt')

add_award("-4, -8 czy -12... A kto by to liczył?",
          agg.sort_values("hits", ascending=False).iloc[0]["entry_name"],
          "Najwięcej punktów z hitów -4",
          f'{int(agg["hits"].max())} pkt')

add_award("Słuchaj mam czutkę!",
          agg.sort_values("transfer_gain", ascending=False).iloc[0]["entry_name"],
          "Najwięcej punktów z transferów",
          f'{int(agg["transfer_gain"].max())} pkt')

add_award("WSZYSCY SĄ W TYLE!!! NA CZELE",
          agg.sort_values("best_gw_count", ascending=False).iloc[0]["entry_name"],
          "Najwięcej razy najlepszy w kolejce",
          f'{int(agg["best_gw_count"].max())} razy')

add_award("Pierwsze sezony takie są",
          agg.sort_values("worst_gw_count", ascending=False).iloc[0]["entry_name"],
          "Najwięcej razy najgorszy w kolejce",
          f'{int(agg["worst_gw_count"].max())} razy')

add_award("Budzi się jak City",
          agg.sort_values("roznica_rund", ascending=False).iloc[0]["entry_name"],
          "Największy progres między pierwszą a drugą rundą",
          f'{int(agg["roznica_rund"].max())} pkt')

add_award("Pomylił sprint z maratonem",
          agg.sort_values("roznica_rund", ascending=True).iloc[0]["entry_name"],
          "Największy regres między pierwszą a drugą rundą",
          f'{int(agg["roznica_rund"].min())} pkt')

add_award("Steczek Roku",
          agg.sort_values("efficiency", ascending=False).iloc[0]["entry_name"],
          "Najwyższa efektywność",
          f'{agg["efficiency"].max():.2f} pkt/gw')

add_award("Jak to mówią: super sub!", 
          agg.sort_values("autosub_count", ascending=False).iloc[0]["entry_name"],
          "Najwięcej trafionych autosubów", 
          f'{int(agg["autosub_count"].max())} pkt')

add_award("Jeszcze jeden transferek...", 
          agg.sort_values("event_transfers", ascending=False).iloc[0]["entry_name"],
          "Najwięcej wykonanych transferów", 
          f'{int(agg["event_transfers"].max())} pkt')

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
picked_starting = all_picked[all_picked.apply(lambda p: p["multiplier"] > 0 if isinstance(p, dict) else False)]
counts = Counter([p["player_id"] for p in picked_starting])
top_player_id, top_count = counts.most_common(1)[0]
top_player_name = id_to_name.get(top_player_id, str(top_player_id))

add_award("Bez niego ani rusz", 
          top_player_name, 
          "Najczęściej wybierany zawodnik (11 podstawowych)", 
          f"{top_count} razy")

# Lowest and highest scores in a GW
min_row = df.loc[df["points"].idxmin()]
max_row = df.loc[df["points"].idxmax()]
bench_max = df.loc[df["bench"].idxmax()]
bench_min = df.loc[df["bench"].idxmin()]
add_award("Najniższy wynik w sezonie", min_row["entry_name"], f"GW{min_row['gw']}", f'{min_row["points"]} pkt')
add_award("Najwyższy wynik w sezonie", max_row["entry_name"], f"GW{max_row['gw']}", f'{max_row["points"]} pkt')
add_award("Najwyższy wynik ławki w sezonie", bench_max["entry_name"], f"GW{bench_max['gw']}", f'{bench_max["bench"]} pkt')
add_award("Najniższy wynik ławki w sezonie", bench_min["entry_name"], f"GW{bench_min['gw']}", f'{bench_min["bench"]} pkt')

chips_used = df[df["chip"].notna()].groupby("entry_name")["chip"].count()
min_chips = chips_used.min()
min_chip_user = chips_used.idxmin()

add_award(
    "Najoszczędniejszy gracz",
    min_chip_user,
    "Najmniej użytych chipów w sezonie",
    f"{min_chips} chip/-ów"
)

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
        ("captain_points", "Punkty kapitanów I", "flare"),
        ("avg_gw_points", "Średnia punktowa", "viridis"),
        ("efficiency", "Ranking efektywności", "cividis"),
        ("bench", "Punkty zawodników na ławce I", "rocket"),
        ("avg_bench_points", "Średnia punktów na ławce", "plasma"),
        ("total_hits", "Ilość hitów I", "mako"),
        ("best_gw_count", "Ilość najlepszych wyników w kolejce I", "crest"),
        ("worst_gw_count", "Ilość najgorszych wyników w kolejce I", "magma"),
    ]:
        # Filter out gameweeks with Bench Boost and recalculate bench points sum
        if col == "bench":
            filtered_df = df[df["chip"] != "bboost"]
            bench_points = filtered_df.groupby("entry_name")["bench"].sum().reset_index()
            d = bench_points.sort_values("bench", ascending=False)
        elif col == "avg_bench_points":
            d = df.groupby("entry_name")["bench"].mean().reset_index().rename(columns={"bench": "avg_bench_points"}).sort_values("avg_bench_points", ascending=False)
        else:
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
            # Aggregate points for manager chip through 3 gameweeks
            if chip == "manager":
                agg_chip = manager_df.groupby("entry_name")["manager_points"].sum().reset_index().rename(columns={"manager_points": "points"})
            elif chip == "3xc":
                agg_chip = chip_df.groupby("entry_name")["captain_points"].max().reset_index().rename(columns={"captain_points": "points"})
                agg_chip["points"] *= 3  # Triple Captain multiplies points by 3
            elif chip == "bboost":
                agg_chip = chip_df.groupby("entry_name")["bench"].sum().reset_index().rename(columns={"bench": "points"})
            else:
                agg_chip = chip_df.groupby("entry_name")["points"].sum().reset_index()
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

    # Summing points for wildcards
    wc1_df = df[df["chip"] == "wildcard1"]
    wc2_df = df[df["chip"] == "wildcard2"]
    wc1_points = wc1_df.groupby("entry_name")["points"].sum()
    wc2_points = wc2_df.groupby("entry_name")["points"].sum()
    wildcards_points = pd.DataFrame(index=all_managers)
    wildcards_points["Wildcard 1"] = wc1_points
    wildcards_points["Wildcard 2"] = wc2_points
    wildcards_points = wildcards_points.fillna(0).astype(int)

    # Plotting wildcards usage
    plt.figure(figsize=(10, 6))
    sort_col = "Wildcard 1" if wildcards_points["Wildcard 1"].sum() > wildcards_points["Wildcard 2"].sum() else "Wildcard 2"
    wildcards_sorted = wildcards_points.sort_values(sort_col, ascending=False)
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
    plt.tight_layout()
    pdf.savefig()
    plt.close()

    # Awards section
    print(" 🔄 Generowanie sekcji nagród...")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="../css/style.css" />
        <title>Ligowe Steczki - Nagrody</title>
    </head>
    <body>
    <div class="cover">
        <img class="emoji-icon" src="https://em-content.zobj.net/source/apple/391/trophy_1f3c6.png" alt="trophy">
        <h1>Ligowe Steczki</h1>
        <h2>Uroczyste Rozdanie Nagród</h2>
        <div class="season">Sezon {season}</div>
    </div>
    """

    for award in awards:
        html += f"""
        <div class="award">
            <div class="title">
                <img class="emoji-icon" src="https://em-content.zobj.net/source/apple/391/trophy_1f3c6.png" alt="trophy">
                {award['Nagroda']}
            </div>
            <div class="label">
                <img class="emoji-icon" src="https://em-content.zobj.net/source/apple/391/t-shirt_1f455.png" alt="shirt">
                <strong>Drużyna:</strong> {award['Drużyna']}
            </div>
            <div class="label">
                <img class="emoji-icon" src="https://em-content.zobj.net/source/apple/391/direct-hit_1f3af.png" alt="target">
                <strong>Za co:</strong> {award['Za co']}
            </div>
            <div class="label">
                <img class="emoji-icon" src="https://em-content.zobj.net/source/apple/391/bar-chart_1f4ca.png" alt="chart">
                <strong>Wartość:</strong> {award['Wartość']}
            </div>
            <img class="seal" src="../img/seal.png">
            <div class="signature">
                <div class="sig-line">_________________________</div>
                <div class="sig-title">Przewodniczący Komisji</div>
                <div class="sig-sub">ds. Nagród Ligowych</div>
                <div class="sig-org">FPL Steczek La Liga</div>
            </div>
            <div class="footer">Sezon {season}</div>
        </div>
        """

    html += "</body></html>"


    with open("fpl_output/awards.html", "w", encoding="utf-8") as f:
        f.write(html)
        print(" ✅ Sekcja nagród wygenerowana. Zapisano jako fpl_output/awards.html")

    # Save awards.html as PDF
    print(" 🔄 Generowanie PDF z sekcją nagród...")
    HTML("fpl_output/awards.html").write_pdf("fpl_output/awards.pdf")
    print(" ✅ PDF z sekcją nagród zapisany jako fpl_output/awards.pdf")

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