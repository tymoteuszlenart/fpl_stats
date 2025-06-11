#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FPL Season Report Generator - Main Script

This script coordinates the generation of reports for Fantasy Premier League data
including statistics, awards, and visualizations.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages

from fpl_data import (
    get_season_years,
    load_data,
    calculate_aggregates,
    process_manager_data,
    analyze_streaks,
    analyze_h2h,
    analyze_chip_timing,
    analyze_player_loyalty,
    analyze_transfer_timing,
    track_league_positions,
    analyze_what_if,
    analyze_team_correlation,
    predict_performance
)
from fpl_dashboard import run_dashboard
from fpl_html import generate_awards_documents

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fpl_report_generator.log')
    ]
)
logger = logging.getLogger(__name__)

# Constants
OUTPUT_DIR = "fpl_output"
CSV_DATA_PATH = "csv/fpl_season_data.csv"
PLAYER_MAPPING_PATH = "json/player_id_mapped.json"
AWARDS_HTML_PATH = os.path.join(OUTPUT_DIR, "awards.html")
AWARDS_PDF_PATH = os.path.join(OUTPUT_DIR, "awards.pdf")
REPORT_PDF_PATH = os.path.join(OUTPUT_DIR, "fpl_sezon_podsumowanie.pdf")

def main() -> None:
    """Main function to generate the FPL season report."""
    try:
        logger.info("Starting FPL report generation")
        
        # Create output directory if it doesn't exist
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        
        # Load and process data
        df, id_to_name = load_data(CSV_DATA_PATH, PLAYER_MAPPING_PATH)
        logger.info("Data loaded successfully")

        # Process manager chip data
        manager_df = process_manager_data(df)
        logger.info("Manager chip data processed")
        
        # Calculate aggregated statistics
        season_years = get_season_years()
        agg_stats = calculate_aggregates(df)
        logger.info("Aggregated statistics calculated")
        
        # Advanced analytics
        logger.info("Performing advanced analytics...")
        streak_data = analyze_streaks(df)
        h2h_data = analyze_h2h(df)
        chip_timing = analyze_chip_timing(df)
        player_loyalty = analyze_player_loyalty(df)
        transfer_timing = analyze_transfer_timing(df)
        league_positions = track_league_positions(df)
        whatif_data = analyze_what_if(df)
        team_correlations = analyze_team_correlation(df)
        
        # Add predictions
        logger.info("Generating predictions...")
        predictions = predict_performance(df, weeks_ahead=5)
        
        # Generate awards based on all statistics
        awards = [
            {
                'Nagroda': 'Najlepszy menedżer',
                'Drużyna': agg_stats.loc[agg_stats['points'].idxmax(), 'entry_name'],
                'Za co': 'Najwięcej punktów w sezonie',
                'Wartość': str(int(agg_stats['points'].max()))
            },
            {
                'Nagroda': 'Król efektywności',
                'Drużyna': agg_stats.loc[agg_stats['efficiency'].idxmax(), 'entry_name'],
                'Za co': 'Najlepsza średnia punktowa po odjęciu hitów',
                'Wartość': f"{agg_stats['efficiency'].max():.1f} pkt/GW"
            },
            {
                'Nagroda': 'Kapitan Punktualny',
                'Drużyna': agg_stats.loc[agg_stats['captain_points'].idxmax(), 'entry_name'],
                'Za co': 'Najlepsze wybory kapitanów',
                'Wartość': str(int(agg_stats['captain_points'].max()))
            },
            {
                'Nagroda': 'Król ławki',
                'Drużyna': agg_stats.loc[agg_stats['max_bench_points'].idxmax(), 'entry_name'],
                'Za co': 'Najwięcej punktów na ławce',
                'Wartość': str(int(agg_stats['max_bench_points'].max()))
            },
            {
                'Nagroda': 'Król pierwszej rundy',
                'Drużyna': agg_stats.loc[agg_stats['runda_1'].idxmax(), 'entry_name'],
                'Za co': 'Najwięcej punktów w pierwszej rundzie',
                'Wartość': str(int(agg_stats['runda_1'].max()))
            },
            {
                'Nagroda': 'Król drugiej rundy',
                'Drużyna': agg_stats.loc[agg_stats['runda_2'].idxmax(), 'entry_name'],
                'Za co': 'Najwięcej punktów w drugiej rundzie',
                'Wartość': str(int(agg_stats['runda_2'].max()))
            },
            {
                'Nagroda': 'Największy progres',
                'Drużyna': agg_stats.loc[agg_stats['roznica_rund'].idxmax(), 'entry_name'],
                'Za co': 'Największa poprawa formy w drugiej rundzie',
                'Wartość': f"+{int(agg_stats['roznica_rund'].max())} pkt"
            },
            {
                'Nagroda': 'Król kolejek',
                'Drużyna': agg_stats.loc[agg_stats['best_gw_count'].idxmax(), 'entry_name'],
                'Za co': 'Najwięcej najlepszych wyników w kolejkach',
                'Wartość': f"{int(agg_stats['best_gw_count'].max())} GW"
            },
            {
                'Nagroda': 'Król transferów',
                'Drużyna': agg_stats.loc[agg_stats['transfer_gain'].idxmax(), 'entry_name'],
                'Za co': 'Najlepszy bilans transferowy',
                'Wartość': f"+{int(agg_stats['transfer_gain'].max())} pkt"
            },
            {
                'Nagroda': 'Anty-król transferów',
                'Drużyna': agg_stats.sort_values('transfer_loss', ascending=True).iloc[0]['entry_name'],
                'Za co': 'Największe straty na transferach',
                'Wartość': f"{int(agg_stats['transfer_loss'].min())} pkt"
            },
            {
                'Nagroda': 'Hitman',
                'Drużyna': agg_stats.loc[agg_stats['total_hits'].idxmax(), 'entry_name'],
                'Za co': 'Najwięcej punktów odjętych za transfery',
                'Wartość': f"-{int(agg_stats['total_hits'].max() * 4)} pkt"
            },
            {
                'Nagroda': 'Anty-król kolejek',
                'Drużyna': agg_stats.loc[agg_stats['worst_gw_count'].idxmax(), 'entry_name'],
                'Za co': 'Najwięcej najgorszych wyników w kolejkach',
                'Wartość': f"{int(agg_stats['worst_gw_count'].max())} GW"
            },
            {
                'Nagroda': 'Król średniej',
                'Drużyna': agg_stats.loc[agg_stats['avg_gw_points'].idxmax(), 'entry_name'],
                'Za co': 'Najwyższa średnia punktowa w kolejce',
                'Wartość': f"{agg_stats['avg_gw_points'].max():.1f} pkt"
            }
        ]

        # Generate awards documents
        season_str = f"{season_years[0]}/{season_years[1]}"
        generate_awards_documents(awards, season_str, AWARDS_HTML_PATH, AWARDS_PDF_PATH)
        logger.info(f"Awards documents generated: {AWARDS_HTML_PATH}, {AWARDS_PDF_PATH}")
        
        # Run interactive dashboard
        logger.info("Starting interactive dashboard")
        run_dashboard(
            df=df,
            agg=agg_stats,
            streak_data=streak_data,
            h2h_data=h2h_data,
            whatif=whatif_data,
            corr_data=team_correlations,
            debug=True
        )
        logger.info("Dashboard completed")
        
        logger.info("FPL report generation completed successfully")
        
    except Exception as e:
        logger.error("Error generating FPL report", exc_info=True)
        raise

if __name__ == "__main__":
    main()