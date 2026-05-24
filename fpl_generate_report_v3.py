# -*- coding: utf-8 -*-
import argparse
import datetime
import os
from ast import literal_eval
from collections import Counter

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from weasyprint import HTML

from fpl_chips import (
    BENCH_BOOST_CHIPS,
    CHIP_CHART_LABELS,
    COMBINED_HALF_CHART_SPECS,
    FREE_HIT_CHIPS,
    HALF_CHIP_ORDER,
    MAX_CHIPS_PER_SEASON,
    TRIPLE_CAPTAIN_CHIPS,
    format_chip_slots_summary,
    format_unused_chips_summary,
    is_bench_boost_chip,
    normalize_chips_dataframe,
    season_chip_usage_by_entry,
    unused_season_chips,
    used_season_chips,
)


def default_season_label():
    first_half_season_year = int(datetime.datetime.now().strftime("%Y")) - 1
    second_half_season_year = datetime.datetime.now().strftime("%Y")
    return f"{first_half_season_year}/{second_half_season_year}"


def report_project_root():
    """Absolute path to repo root (directory containing css/ and img/)."""
    return os.path.dirname(os.path.abspath(__file__))


# Unicode icons for awards HTML (no external CDN; works offline in WeasyPrint).
_AWARD_ICON_TROPHY = "🏆"
_AWARD_ICON_SHIRT = "👕"
_AWARD_ICON_TARGET = "🎯"
_AWARD_ICON_CHART = "📊"


def build_awards_html(awards, season):
    """Build awards ceremony HTML using only local asset paths (css/, img/)."""
    trophy = (
        f'<span class="emoji-icon" role="img" aria-label="trofeum">{_AWARD_ICON_TROPHY}</span>'
    )
    shirt = (
        f'<span class="emoji-icon" role="img" aria-label="koszulka">{_AWARD_ICON_SHIRT}</span>'
    )
    target = (
        f'<span class="emoji-icon" role="img" aria-label="cel">{_AWARD_ICON_TARGET}</span>'
    )
    chart = (
        f'<span class="emoji-icon" role="img" aria-label="wykres">{_AWARD_ICON_CHART}</span>'
    )

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="css/style.css" />
        <title>Ligowe Steczki - Nagrody</title>
    </head>
    <body>
    <div class="cover">
        {trophy}
        <h1>Ligowe Steczki</h1>
        <h2>Uroczyste Rozdanie Nagród</h2>
        <div class="season">Sezon {season}</div>
    </div>
    """

    for award in awards:
        html += f"""
        <div class="award">
            <div class="title">
                {trophy}
                {award['Nagroda']}
            </div>
            <div class="label">
                {shirt}
                <strong>Drużyna:</strong> {award['Drużyna']}
            </div>
            <div class="label">
                {target}
                <strong>Za co:</strong> {award['Za co']}
            </div>
            <div class="label">
                {chart}
                <strong>Wartość:</strong> {award['Wartość']}
            </div>
            <img class="seal" src="img/seal.png" alt="">
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
    return html


def write_awards_pdf(html, pdf_path, base_url=None):
    """Render awards HTML to PDF using project-root asset resolution (no network)."""
    if base_url is None:
        base_url = report_project_root()
    HTML(string=html, base_url=base_url).write_pdf(pdf_path)


def load_data(csv_path="csv/fpl_season_data.csv", mapping_path="json/player_id_mapped.json"):
    """Load season CSV and player ID mapping. Returns (df, id_to_name)."""
    print(f"🔄 Ładowanie danych z pliku {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Plik {csv_path} nie został znaleziony") from exc
    df = normalize_chips_dataframe(df)
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


def build_aggregates(df):
    """Build per-manager season aggregates. Returns (agg, num_gw)."""
    num_gw = df["gw"].nunique()

    agg = df.groupby("entry_name").agg({
        "points": "sum",
        "bench": "sum",
        "hits": "sum",
        "captain_points": "sum",
        "transfer_gain": "sum",
        "autosub_count": "sum",
        "event_transfers": "sum"
    }).reset_index()

    agg["avg_gw_points"] = agg["entry_name"].map(
        df.groupby("entry_name")["points"].mean()
    )
    agg["avg_bench_points"] = agg["entry_name"].map(
        df.groupby("entry_name")["bench"].mean()
    )
    agg["efficiency"] = (agg["points"] - agg["hits"]) / num_gw
    agg["transfer_loss"] = df.groupby("entry_name")["transfer_gain"].apply(lambda x: x[x < 0].sum())
    agg["total_hits"] = agg["entry_name"].map(
        df.groupby("entry_name")["hits"].sum().divide(4).astype(int)
    )
    agg["max_bench_points"] = agg["entry_name"].map(
        df[~df["chip"].apply(is_bench_boost_chip)].groupby("entry_name")["bench"].sum()
    ).fillna(0)

    best = df.loc[df.groupby("gw")["points"].idxmax()].entry_name.value_counts()
    worst = df.loc[df.groupby("gw")["points"].idxmin()].entry_name.value_counts()
    agg["best_gw_count"] = agg["entry_name"].map(best).fillna(0).astype(int)
    agg["worst_gw_count"] = agg["entry_name"].map(worst).fillna(0).astype(int)

    first = df[df["gw"] <= 19].groupby("entry_name")["points"].sum()
    second = df[df["gw"] > 19].groupby("entry_name")["points"].sum()
    agg["runda_1"] = agg["entry_name"].map(first)
    agg["runda_2"] = agg["entry_name"].map(second)
    agg["roznica_rund"] = agg["runda_2"] - agg["runda_1"]

    return agg, num_gw


def build_awards(df, agg, id_to_name):
    """Compute league awards and top-captain table. Returns (awards, top_captains)."""
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
              f'{int(agg["autosub_count"].max())} razy')

    add_award("Jeszcze jeden transferek...",
              agg.sort_values("event_transfers", ascending=False).iloc[0]["entry_name"],
              "Najwięcej wykonanych transferów",
              f'{int(agg["event_transfers"].max())} razy')

    bb = df[df["chip"].isin(BENCH_BOOST_CHIPS)]
    if not bb.empty:
        best_bb = bb.sort_values("bench", ascending=False).iloc[0]
        add_award("Mykolenko w końcu punktuje",
                  best_bb["entry_name"],
                  f"Najlepsze pojedyncze Bench Boost (GW {int(best_bb['gw'])})",
                  f"{int(best_bb['bench'])} pkt")

    tc = df[df["chip"].isin(TRIPLE_CAPTAIN_CHIPS)]
    if not tc.empty:
        best_tc = tc.sort_values("captain_points", ascending=False).iloc[0]
        add_award("Salah czy nie Salah?",
                  best_tc["entry_name"],
                  f"Najlepsze pojedyncze 3xC (GW {int(best_tc['gw'])})",
                  f"{int(best_tc['captain_points']) * 3} pkt")

    df["prev_points"] = df.sort_values(["entry_name", "gw"]).groupby("entry_name")["points"].shift(1)
    fh = df[df["chip"].isin(FREE_HIT_CHIPS)]
    if not fh.empty:
        best_fh = fh.sort_values("points", ascending=False).iloc[0]
        add_award("Upolowane",
                  best_fh["entry_name"],
                  f"Najlepsze pojedyncze Free Hit (GW {int(best_fh['gw'])})",
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

    min_row = df.loc[df["points"].idxmin()]
    max_row = df.loc[df["points"].idxmax()]
    bench_max = df.loc[df["bench"].idxmax()]
    bench_min = df.loc[df["bench"].idxmin()]
    add_award("Najniższy wynik w sezonie", min_row["entry_name"], f"GW{min_row['gw']}", f'{min_row["points"]} pkt')
    add_award("Najwyższy wynik w sezonie", max_row["entry_name"], f"GW{max_row['gw']}", f'{max_row["points"]} pkt')
    add_award("Najwyższy wynik ławki w sezonie", bench_max["entry_name"], f"GW{bench_max['gw']}", f'{bench_max["bench"]} pkt')
    add_award("Najniższy wynik ławki w sezonie", bench_min["entry_name"], f"GW{bench_min['gw']}", f'{bench_min["bench"]} pkt')

    chip_usage = season_chip_usage_by_entry(df)
    chip_rules = (
        f"(max {MAX_CHIPS_PER_SEASON}: po dwa BB, 3xC, FH i WC w 2025/26)"
    )
    min_chips = int(chip_usage.min())
    min_chip_user = chip_usage.idxmin()
    unused = unused_season_chips(df.loc[df["entry_name"] == min_chip_user, "chip"])
    thrift_reason = f"Najmniej aktywacji chipów w sezonie {chip_rules}"
    if unused:
        thrift_reason += f" — nieużywane: {format_unused_chips_summary(unused)}"

    add_award(
        "Najoszczędniejszy gracz",
        min_chip_user,
        thrift_reason,
        f"{min_chips} razy (z {MAX_CHIPS_PER_SEASON})",
    )

    max_chips = int(chip_usage.max())
    if max_chips > 0:
        max_chip_user = chip_usage.idxmax()
        used = used_season_chips(df.loc[df["entry_name"] == max_chip_user, "chip"])
        hoarder_reason = f"Najwięcej aktywacji chipów w sezonie {chip_rules}"
        if used:
            hoarder_reason += f" — użyte: {format_chip_slots_summary(used)}"
        add_award(
            "Bank chipów pusty nie będzie",
            max_chip_user,
            hoarder_reason,
            f"{max_chips} razy (z {MAX_CHIPS_PER_SEASON})",
        )

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

    return awards, top_captains


def _aggregate_chip_chart(chip_df, chip):
    """Per-manager metric for a single half-specific chip (best single GW)."""
    if chip.startswith("3xc"):
        out = chip_df.groupby("entry_name")["captain_points"].max().reset_index()
        out = out.rename(columns={"captain_points": "points"})
        out["points"] *= 3
    elif chip.startswith("bboost"):
        out = chip_df.groupby("entry_name")["bench"].max().reset_index()
        out = out.rename(columns={"bench": "points"})
    else:
        out = chip_df.groupby("entry_name")["points"].max().reset_index()
    return out.sort_values("points", ascending=False)


def _half_combined_series(df, half_chips, value_col, mode):
    chip_df = df[df["chip"].isin(half_chips)]
    if chip_df.empty:
        return pd.Series(dtype=float)
    if mode == "max_triple":
        return chip_df.groupby("entry_name")["captain_points"].max() * 3
    if mode == "sum":
        return chip_df.groupby("entry_name")[value_col].sum()
    return chip_df.groupby("entry_name")[value_col].max()


def _plot_combined_chip_halves(pdf, df, title_prefix, chip_set, value_col, mode):
    """Side-by-side bar chart for 1st/2nd half chip uses (values not mixed)."""
    chips_1 = {c for c in chip_set if c.endswith("1")}
    chips_2 = {c for c in chip_set if c.endswith("2")}
    half1 = _half_combined_series(df, chips_1, value_col, mode)
    half2 = _half_combined_series(df, chips_2, value_col, mode)
    if half1.empty and half2.empty:
        return

    all_managers = df["entry_name"].unique()
    combined = pd.DataFrame(index=all_managers)
    combined[f"{title_prefix} 1"] = half1
    combined[f"{title_prefix} 2"] = half2
    combined = combined.fillna(0).astype(int)

    plt.figure(figsize=(10, 6))
    sort_col = (
        f"{title_prefix} 1"
        if combined[f"{title_prefix} 1"].sum() >= combined[f"{title_prefix} 2"].sum()
        else f"{title_prefix} 2"
    )
    sorted_df = combined.sort_values(sort_col, ascending=False)
    ax = sorted_df.plot(kind="barh", stacked=False, ax=plt.gca(), colormap="Set2")

    for i, (_, row) in enumerate(sorted_df.iterrows()):
        v1 = row[f"{title_prefix} 1"]
        v2 = row[f"{title_prefix} 2"]
        if v1 > 0:
            ax.text(v1 + 1, i - 0.2, str(int(v1)), va="center", fontsize=9)
        if v2 > 0:
            ax.text(v2 + 1, i + 0.2, str(int(v2)), va="center", fontsize=9)

    plt.title(f"{title_prefix} — 1. i 2. połowa (osobno, bez mieszania)")
    plt.tight_layout()
    pdf.savefig()
    plt.close()



def generate_pdfs(df, agg, awards, top_captains, output_dir="fpl_output", season=None, write_output=True):
    """Generate PDF/HTML reports. Set write_output=False to skip file I/O (e.g. tests)."""
    if season is None:
        season = default_season_label()

    if not write_output:
        return

    os.makedirs(output_dir, exist_ok=True)
    summary_pdf = os.path.join(output_dir, "fpl_sezon_podsumowanie.pdf")
    awards_html_path = os.path.join(output_dir, "awards.html")
    awards_pdf_path = os.path.join(output_dir, "awards.pdf")

    print("🔄 Tworzenie raportu w PDF...")
    with PdfPages(summary_pdf) as pdf:
        sns.set(style="whitegrid")
        plt.rcParams.update({'axes.titlesize': 16})

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
            if col == "bench":
                filtered_df = df[~df["chip"].apply(is_bench_boost_chip)]
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

        for chip in HALF_CHIP_ORDER:
            chip_df = df[df["chip"] == chip]
            if chip_df.empty:
                continue
            d = _aggregate_chip_chart(chip_df, chip)
            plt.figure(figsize=(10, 6))
            ax = sns.barplot(data=d, x="points", y="entry_name", hue="entry_name", legend=False, palette="cubehelix")
            for i, v in enumerate(d["points"]):
                if not pd.isna(v):
                    ax.text(v + 0.5, i, f"{int(v)}", va="center")
            plt.title(f"Najskuteczniejsi gracze: {CHIP_CHART_LABELS[chip]}")
            plt.tight_layout()
            pdf.savefig()
            plt.close()

        for title_prefix, chip_set, value_col, mode in COMBINED_HALF_CHART_SPECS:
            _plot_combined_chip_halves(pdf, df, title_prefix, chip_set, value_col, mode)

        _plot_combined_chip_halves(
            pdf,
            df,
            "Wildcard",
            {"wildcard1", "wildcard2"},
            "points",
            "sum",
        )

        print(" 🔄 Generowanie sekcji nagród...")

        html = build_awards_html(awards, season)

        with open(awards_html_path, "w", encoding="utf-8") as f:
            f.write(html)
            print(f" ✅ Sekcja nagród wygenerowana. Zapisano jako {awards_html_path}")

        print(" 🔄 Generowanie PDF z sekcją nagród...")
        write_awards_pdf(html, awards_pdf_path, base_url=report_project_root())
        print(f" ✅ PDF z sekcją nagród zapisany jako {awards_pdf_path}")

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

    print(f"✅ Zapisano: {summary_pdf}")


def run_report(csv_path="csv/fpl_season_data.csv", mapping_path="json/player_id_mapped.json",
               output_dir="fpl_output", season=None, write_output=True):
    """Full pipeline: load data, aggregates, awards, optional PDF generation."""
    df, id_to_name = load_data(csv_path, mapping_path)
    agg, _num_gw = build_aggregates(df)
    awards, top_captains = build_awards(df, agg, id_to_name)
    generate_pdfs(df, agg, awards, top_captains, output_dir=output_dir, season=season, write_output=write_output)
    return {"df": df, "agg": agg, "awards": awards, "top_captains": top_captains, "id_to_name": id_to_name}


def _parse_args():
    parser = argparse.ArgumentParser(description="Generate FPL league season PDF/HTML reports.")
    parser.add_argument("--csv", default="csv/fpl_season_data.csv", help="Input season CSV path")
    parser.add_argument("--output-dir", default="fpl_output", help="Directory for PDF/HTML output")
    parser.add_argument("--season", default=None, help="Season label (default: current football season)")
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Skip writing PDF/HTML files (useful for tests)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    try:
        run_report(
            csv_path=args.csv,
            output_dir=args.output_dir,
            season=args.season,
            write_output=not args.no_write,
        )
    except FileNotFoundError as exc:
        print(f"❌ {exc.args[0]}")
        raise SystemExit(1) from exc
