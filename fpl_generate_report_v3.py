# -*- coding: utf-8 -*-
import argparse
import datetime
import os
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from weasyprint import HTML

from aggregates import build_aggregates
from awards import build_awards, player_display_name
from data_loader import load_data
from fpl_chips import (
    CHIP_CHART_LABELS,
    COMBINED_HALF_CHART_SPECS,
    HALF_CHIP_ORDER,
    is_bench_boost_chip,
)

__all__ = [
    "build_aggregates",
    "build_awards",
    "build_awards_html",
    "load_data",
    "player_display_name",
    "report_project_root",
    "run_report",
    "write_awards_pdf",
]


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


def _aggregate_chip_chart(chip_df, chip):
    """Per-manager metric for a single half-specific chip (best single GW)."""
    if chip.startswith("3xc"):
        out = chip_df.groupby("entry_name")["captain_contribution_points"].max().reset_index()
        out = out.rename(columns={"captain_contribution_points": "points"})
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
            ("captain_contribution_points", "Punkty kapitanów (2×/3×) I", "flare"),
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
