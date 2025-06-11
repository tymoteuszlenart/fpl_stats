"""
FPL Plotting Functions

This module contains functions for generating plots and visualizations for the FPL season report.
"""

import logging
from typing import Dict, List, Tuple

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from matplotlib.backends.backend_pdf import PdfPages
from weasyprint import HTML
from io import BytesIO

logger = logging.getLogger(__name__)

# Color schemes and plot configurations
PLOT_CONFIGS = [
    ("captain_points", "Punkty kapitanów I", "flare"),
    ("avg_gw_points", "Średnia punktowa", "viridis"),
    ("efficiency", "Ranking efektywności", "cividis"),
    ("bench", "Punkty zawodników na ławce I", "rocket"),
    ("avg_bench_points", "Średnia punktów na ławce", "plasma"),
    ("total_hits", "Ilość hitów I", "mako"),
    ("best_gw_count", "Ilość najlepszych wyników w kolejce I", "crest"),
    ("worst_gw_count", "Ilość najgorszych wyników w kolejce I", "magma"),
]

CHIP_NAMES = {
    "3xc": "Triple Captain",
    "bboost": "Bench Boost",
    "freehit": "Free Hit",
    "manager": "Assistant Manager",
    "wildcard1": "Wildcard - 1st Round",
    "wildcard2": "Wildcard - 2nd Round"
}

def plot_statistics(pdf: PdfPages, df: pd.DataFrame, agg: pd.DataFrame) -> None:
    """Generate statistical plots and save them to the PDF.
    
    Args:
        pdf: PdfPages object to save plots to
        df: DataFrame with raw season data
        agg: DataFrame with aggregated statistics
    """
    try:
        for plot_metric, title, palette_name in PLOT_CONFIGS:
            plt.figure(figsize=(10, 6))
            data = agg.sort_values(plot_metric, ascending=False)
            
            ax = sns.barplot(
                data=data, 
                x=plot_metric, 
                y="entry_name", 
                hue="entry_name", 
                legend=False, 
                palette=palette_name
            )
            
            # Add value labels
            for i, v in enumerate(data[plot_metric]):
                if pd.notna(v):  # Check for NaN values
                    value = str(int(v)) if not isinstance(v, float) else f'{v:.1f}'
                    ax.text(v + 0.5, i, value, va='center')
            
            plt.title(title.replace(" I", ""))
            plt.tight_layout()
            pdf.savefig()
            plt.close()
            logger.info(f"Generated plot for {title}")
            
    except Exception as e:
        logger.error(f"Error generating statistics plots: {str(e)}")
        raise

def plot_chip_statistics(pdf: PdfPages, chip: str, chip_df: pd.DataFrame, manager_df: pd.DataFrame) -> None:
    """Generate statistics plot for a specific chip usage."""
    try:
        if chip == "manager":
            agg_chip = manager_df.groupby("entry_name")["manager_points"].sum() \
                .reset_index().rename(columns={"manager_points": "points"})
        elif chip == "3xc":
            agg_chip = chip_df.groupby("entry_name")["captain_points"].max() \
                .reset_index().rename(columns={"captain_points": "points"})
            agg_chip["points"] *= 3
        elif chip == "bboost":
            agg_chip = chip_df.groupby("entry_name")["bench"].sum() \
                .reset_index().rename(columns={"bench": "points"})
        else:
            agg_chip = chip_df.groupby("entry_name")["points"].sum().reset_index()

        d = agg_chip.sort_values("points", ascending=False)
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=d, x="points", y="entry_name", hue="entry_name", 
                        legend=False, palette='cubehelix')
        
        for i, v in enumerate(d["points"]):
            if not pd.isna(v):
                ax.text(v + 0.5, i, str(int(v)), va='center')
                
        plt.title(f"Najskuteczniejsi gracze z chipem: {CHIP_NAMES.get(chip, chip)}")
        plt.tight_layout()
        pdf.savefig()
        plt.close()
        
    except Exception as e:
        logger.error(f"Error generating chip statistics plot for {chip}: {str(e)}")
        raise

def plot_wildcards_comparison(pdf: PdfPages, df: pd.DataFrame) -> None:
    """Generate comparison plot for wildcard usage."""
    try:
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

        plt.figure(figsize=(10, 6))
        sort_col = "Wildcard 1" if wildcards_points["Wildcard 1"].sum() > wildcards_points["Wildcard 2"].sum() else "Wildcard 2"
        wildcards_sorted = wildcards_points.sort_values(sort_col, ascending=False)
        
        ax = wildcards_sorted.plot(kind="barh", stacked=False, ax=plt.gca(), colormap="Set2")
        for i, (index, row) in enumerate(wildcards_sorted.iterrows()):
            wc1, wc2 = row["Wildcard 1"], row["Wildcard 2"]
            if wc1 > 0:
                ax.text(wc1 + 1, i - 0.2, str(wc1), va='center', fontsize=9)
            if wc2 > 0:
                ax.text(wc2 + 1, i + 0.2, str(wc2), va='center', fontsize=9)
        
        plt.title("Wyniki graczy po użyciu Wildcard 1 i 2")
        plt.tight_layout()
        pdf.savefig()
        plt.close()
        
    except Exception as e:
        logger.error(f"Error generating wildcards comparison plot: {str(e)}")
        raise

def plot_top_captains(pdf: PdfPages, df: pd.DataFrame, id_to_name: Dict[int, str]) -> None:
    """Generate table with top captain choices."""
    try:
        # Calculate top captain choices
        top_captains = df.groupby(["entry_name", "captain_id"])["captain_points"].max().reset_index()
        top_captains = top_captains.sort_values("captain_points", ascending=False).head(30)
        top_captains["captain_name"] = top_captains["captain_id"].map(id_to_name) \
            .fillna(top_captains["captain_id"].astype(str))
        
        idx = df.groupby(["entry_name", "captain_id"])["captain_points"].idxmax()
        top_captain_rows = df.loc[idx, ["entry_name", "captain_id", "captain_points", "gw"]]
        top_captains = top_captains.merge(
            top_captain_rows, 
            on=["entry_name", "captain_id", "captain_points"], 
            how="left"
        )
        
        # Format description for each captain choice
        top_captains["desc"] = (
            top_captains["entry_name"] + " – " +
            top_captains["captain_name"] + " – " +
            top_captains["captain_points"].astype(int).astype(str) + " pkt - " +
            "GW" + top_captains["gw"].astype(str)    
        )

        # Create table plot
        fig, ax = plt.subplots(figsize=(6, 12))
        ax.axis("off")
        # Convert to nested list for proper table format
        cell_data = [[x] for x in top_captains["desc"].values]
        table = ax.table(
            cellText=cell_data,
            colLabels=["TOP 30 wyborów kapitańskich"],
            loc="center",
            cellLoc="center"
        )
        table.auto_set_font_size(False)
        table.set_fontsize(12)
        table.scale(1.2, 2)
        pdf.savefig()
        plt.close()
        
    except Exception as e:
        logger.error(f"Error generating top captains plot: {str(e)}")
        raise

def plot_streaks_and_form(pdf: PdfPages, streak_data: pd.DataFrame) -> None:
    """Plot team form streaks analysis."""
    plt.figure(figsize=(12, 6))
    
    # Plot good vs bad streaks
    data = streak_data.sort_values('longest_good_streak', ascending=False)
    x = np.arange(len(data))
    
    plt.bar(x, np.array(data['longest_good_streak']), color='green', alpha=0.6, label='Najlepsza seria')
    plt.bar(x, -np.array(data['longest_bad_streak']), color='red', alpha=0.6, label='Najgorsza seria')
    
    # Add current streak indicators
    for i, row in enumerate(data.itertuples()):
        if pd.notnull(row.current_streak):
            streak = float(row.current_streak)
            if streak > 0:
                plt.scatter(i, streak, color='green', s=100, zorder=5)
            elif streak < 0:
                plt.scatter(i, streak, color='red', s=100, zorder=5)
    
    plt.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    plt.xticks(x, list(data.index), rotation=45, ha='right')
    plt.ylabel('Długość serii (tygodnie)')
    plt.title('Serie form drużyn')
    plt.legend()
    plt.tight_layout()
    pdf.savefig()
    plt.close()

def plot_h2h_matrix(pdf: PdfPages, h2h_data: pd.DataFrame) -> None:
    """Plot head-to-head comparison matrix."""
    teams = sorted(set(h2h_data['team_1'].unique()) | set(h2h_data['team_2'].unique()))
    n_teams = len(teams)
    matrix = np.zeros((n_teams, n_teams))
    
    # Fill the matrix with win ratios
    for _, row in h2h_data.iterrows():
        i = teams.index(row['team_1'])
        j = teams.index(row['team_2'])
        total_games = float(row['wins_1']) + float(row['wins_2'])
        if total_games > 0:
            win_ratio = float(row['wins_1']) / total_games
            matrix[i, j] = win_ratio
            matrix[j, i] = 1.0 - win_ratio
    
    plt.figure(figsize=(12, 8))
    sns.heatmap(matrix, annot=True, fmt='.2f', cmap='RdYlGn',
                xticklabels=teams, yticklabels=teams)
    plt.title('Bezpośrednie pojedynki (% wygranych GW)')
    plt.tight_layout()
    pdf.savefig()
    plt.close()

def plot_league_positions(pdf: PdfPages, df: pd.DataFrame) -> None:
    """Plot league position changes over time."""
    # Calculate positions for each gameweek
    positions_by_gw = []
    for gw in sorted(df['gw'].unique()):
        gw_data = df[df['gw'] == gw].copy()
        gw_data['cum_points'] = df[df['gw'] <= gw].groupby('entry_name')['points'].sum()
        gw_data = gw_data.sort_values('cum_points', ascending=False)
        gw_data['position'] = np.arange(1, len(gw_data) + 1)
        positions_by_gw.append(gw_data[['entry_name', 'position', 'gw']])
    
    position_df = pd.concat(positions_by_gw)
    
    plt.figure(figsize=(15, 8))
    for name in position_df['entry_name'].unique():
        team_data = position_df[position_df['entry_name'] == name]
        plt.plot(team_data['gw'].values, team_data['position'].values, 
                marker='o', label=name, linestyle='-', markersize=4)
    
    plt.gca().invert_yaxis()  # Invert y-axis so position 1 is at the top
    plt.xlabel('Gameweek')
    plt.ylabel('Pozycja')
    plt.title('Pozycje w lidze w trakcie sezonu')
    plt.grid(True, alpha=0.3)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    pdf.savefig()
    plt.close()

def plot_what_if_analysis(pdf: PdfPages, whatif: pd.DataFrame, actual_points: pd.Series) -> None:
    """Plot 'what-if' scenario analysis."""
    scenarios = [
        ('points_with_best_captains', 'Najlepsi kapitanowie'),
        ('points_without_hits', 'Bez hitów'),
        ('points_with_best_bench', 'Optymalna ławka'),
    ]
    
    # Calculate potential gains for each scenario
    gains = pd.DataFrame(index=whatif.index)
    for col, label in scenarios:
        gains[label] = whatif[col] - actual_points
    
    # Create the plot using plotly
    fig = go.Figure()
    
    for col in gains.columns:
        fig.add_trace(go.Bar(x=gains.index, y=gains[col], name=col))
    
    fig.update_layout(
        title='Potencjalne zyski punktowe w różnych scenariuszach',
        xaxis_title='Drużyna',
        yaxis_title='Dodatkowe punkty',
        barmode='group',
        showlegend=True
    )
    
    # Convert plotly figure to PNG and create a BytesIO object
    img_bytes_io = BytesIO(fig.to_image(format="png"))
    
    # Create matplotlib figure and show the image
    plt.figure(figsize=(12, 6))
    plt.imshow(plt.imread(img_bytes_io))
    plt.axis('off')
    pdf.savefig()
    plt.close()

def plot_team_correlation_network(pdf: PdfPages, corr_data: pd.DataFrame) -> None:
    """Plot team correlation network visualization."""
    # Create network graph
    G = nx.Graph()
    
    # Add edges with weights based on squad similarity
    for _, row in corr_data.iterrows():
        team1 = str(row['team_1'])
        team2 = str(row['team_2'])
        try:
            squad_sim = float(row['squad_similarity'])
            captain_sim = float(row['captain_similarity'])
            G.add_edge(team1, team2, weight=squad_sim, captain_sim=captain_sim)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert similarity values for {team1}-{team2}")
            continue

    plt.figure(figsize=(12, 8))
    
    # Position nodes using spring layout
    pos = nx.spring_layout(G)
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_size=1000, node_color='lightblue')
    nx.draw_networkx_labels(G, pos)
    
    # Draw edges with varying thickness
    for (u, v, d) in G.edges(data=True):
        nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], 
                             width=d['weight'] * 3,
                             edge_color='gray', alpha=0.5)
    
    plt.title('Sieć podobieństw między drużynami')
    plt.axis('off')
    plt.tight_layout()
    pdf.savefig()
    plt.close()
