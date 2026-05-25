# -*- coding: utf-8 -*-
"""League awards and top-captain table logic for FPL season reports."""

from collections import Counter

import pandas as pd

from fpl_chips import (
    BENCH_BOOST_CHIPS,
    FREE_HIT_CHIPS,
    MAX_CHIPS_PER_SEASON,
    TRIPLE_CAPTAIN_CHIPS,
    ensure_captain_columns,
    format_chip_slots_summary,
    format_unused_chips_summary,
    season_chip_efficiency_by_entry,
    season_chip_total_return_by_entry,
    season_chip_usage_by_entry,
    unused_season_chips,
    used_season_chips,
)
from fpl_season_storage import team_lists_series


def player_display_name(player_id, id_to_name):
    """Resolve FPL element id to display name; unknown ids get a stable fallback."""
    if player_id in id_to_name:
        return id_to_name[player_id]
    return f"Gracz #{player_id}"


def build_awards(df, agg, id_to_name):
    """Compute league awards and top-captain table. Returns (awards, top_captains)."""
    df = ensure_captain_columns(df)
    awards = []

    def add_award(title, team, reason, value):
        awards.append({"Nagroda": title, "Drużyna": team, "Za co": reason, "Wartość": value})

    add_award("Kto na kapitanie?",
              agg.sort_values("captain_contribution_points", ascending=False).iloc[0]["entry_name"],
              "Najwięcej punktów z kapitana (z bonusem 2×/3×)",
              f'{int(agg["captain_contribution_points"].max())} pkt')

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
        best_tc = tc.sort_values("captain_contribution_points", ascending=False).iloc[0]
        add_award("Salah czy nie Salah?",
                  best_tc["entry_name"],
                  f"Najlepsze pojedyncze 3xC (GW {int(best_tc['gw'])})",
                  f"{int(best_tc['captain_contribution_points'])} pkt")

    df["prev_points"] = df.sort_values(["entry_name", "gw"]).groupby("entry_name")["points"].shift(1)
    fh = df[df["chip"].isin(FREE_HIT_CHIPS)]
    if not fh.empty:
        best_fh = fh.sort_values("points", ascending=False).iloc[0]
        add_award("Upolowane",
                  best_fh["entry_name"],
                  f"Najlepsze pojedyncze Free Hit (GW {int(best_fh['gw'])})",
                  f"{int(best_fh['points'])} pkt")

    all_picked = team_lists_series(df).dropna().explode()
    picked_starting = all_picked[all_picked.apply(lambda p: p["multiplier"] > 0 if isinstance(p, dict) else False)]
    counts = Counter([p["player_id"] for p in picked_starting])
    top_player_id, top_count = counts.most_common(1)[0]
    top_player_name = player_display_name(top_player_id, id_to_name)

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

    chip_returns = season_chip_total_return_by_entry(df)
    chip_efficiency = season_chip_efficiency_by_entry(df)
    eligible = chip_usage[chip_usage >= 1]
    if not eligible.empty:
        eff_eligible = chip_efficiency.loc[eligible.index]
        best_eff_val = eff_eligible.max()
        best_candidates = eff_eligible[eff_eligible == best_eff_val].index
        best_eff_idx = chip_usage.loc[best_candidates].idxmin()
        best_usage = int(chip_usage.loc[best_eff_idx])
        best_return = int(chip_returns.loc[best_eff_idx])
        add_award(
            "Chipy się zwracają",
            best_eff_idx,
            (
                f"Najwyższy zwrot z chipów w sezonie {chip_rules} "
                f"(suma pkt z aktywacji / liczba aktywacji; remis → mniej aktywacji)"
            ),
            f"{chip_efficiency.loc[best_eff_idx]:.1f} pkt/aktywacja ({best_return} pkt, {best_usage} aktyw.)",
        )

        worst_eff_val = eff_eligible.min()
        worst_candidates = eff_eligible[eff_eligible == worst_eff_val].index
        worst_eff_idx = chip_usage.loc[worst_candidates].idxmax()
        worst_usage = int(chip_usage.loc[worst_eff_idx])
        worst_return = int(chip_returns.loc[worst_eff_idx])
        if worst_eff_idx != best_eff_idx or chip_efficiency.loc[worst_eff_idx] < chip_efficiency.loc[best_eff_idx]:
            add_award(
                "Złoty chip, miedziany wynik",
                worst_eff_idx,
                (
                    f"Najniższy zwrot z chipów w sezonie {chip_rules} "
                    f"(tylko gracze z ≥1 aktywacją; remis → więcej aktywacji)"
                ),
                f"{chip_efficiency.loc[worst_eff_idx]:.1f} pkt/aktywacja ({worst_return} pkt, {worst_usage} aktyw.)",
            )

    top_captains = df.groupby(["entry_name", "captain_id"])["captain_contribution_points"].max().reset_index()
    top_captains = top_captains.sort_values("captain_contribution_points", ascending=False).head(30)
    top_captains["captain_name"] = top_captains["captain_id"].apply(
        lambda pid: player_display_name(pid, id_to_name)
    )
    idx = df.groupby(["entry_name", "captain_id"])["captain_contribution_points"].idxmax()
    top_captain_rows = df.loc[idx, ["entry_name", "captain_id", "captain_contribution_points", "gw"]]
    top_captains = top_captains.merge(
        top_captain_rows,
        on=["entry_name", "captain_id", "captain_contribution_points"],
        how="left",
    )
    top_captains["desc"] = (
        top_captains["entry_name"] + " – " +
        top_captains["captain_name"] + " – " +
        top_captains["captain_contribution_points"].astype(int).astype(str) + " pkt - " +
        "GW" + top_captains["gw"].astype(str)
    )

    return awards, top_captains
