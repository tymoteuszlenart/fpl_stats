# -*- coding: utf-8 -*-
"""Per-manager season aggregates for FPL league reports."""

import pandas as pd

from fpl_stats.chips import ensure_captain_columns, is_bench_boost_chip


def build_aggregates(df):
    """Build per-manager season aggregates. Returns (agg, num_gw)."""
    df = ensure_captain_columns(df)
    num_gw = df["gw"].nunique()

    agg = (
        df.groupby("entry_name")
        .agg(
            {
                "points": "sum",
                "bench": "sum",
                "hits": "sum",
                "captain_contribution_points": "sum",
                "transfer_gain": "sum",
                "autosub_count": "sum",
                "event_transfers": "sum",
            }
        )
        .reset_index()
    )

    agg["avg_gw_points"] = agg["entry_name"].map(df.groupby("entry_name")["points"].mean())
    agg["avg_bench_points"] = agg["entry_name"].map(df.groupby("entry_name")["bench"].mean())
    agg["efficiency"] = (agg["points"] - agg["hits"]) / num_gw
    agg["transfer_loss"] = df.groupby("entry_name")["transfer_gain"].apply(lambda x: x[x < 0].sum())
    agg["total_hits"] = agg["entry_name"].map(
        df.groupby("entry_name")["hits"].sum().divide(4).astype(int)
    )
    agg["max_bench_points"] = (
        agg["entry_name"]
        .map(df[~df["chip"].apply(is_bench_boost_chip)].groupby("entry_name")["bench"].sum())
        .fillna(0)
    )

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
