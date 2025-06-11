"""
FPL Data Processing Functions

This module contains functions for processing and analyzing FPL season data.
"""

import logging
from typing import Dict, List, Tuple, Any
from ast import literal_eval
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

def get_season_years() -> Tuple[int, str]:
    """Get the current FPL season years."""
    import datetime
    current_year = datetime.datetime.now().year
    first_half_season_year = current_year - 1
    second_half_season_year = str(current_year)
    return first_half_season_year, second_half_season_year

def load_data(csv_path: str, player_mapping_path: str) -> Tuple[pd.DataFrame, Dict[int, str]]:
    """Load FPL season data and player mapping from files.
    
    Args:
        csv_path: Path to the CSV data file
        player_mapping_path: Path to the player mapping JSON file
    
    Returns:
        Tuple[pd.DataFrame, Dict[int, str]]: DataFrame with season data and ID to name mapping
        
    Raises:
        FileNotFoundError: If required data files are not found
        ValueError: If data format is invalid
    """
    logger.info("Loading FPL season data...")
    
    # Check if files exist
    if not Path(csv_path).exists():
        logger.error(f"CSV data file not found: {csv_path}")
        raise FileNotFoundError(f"Required data file not found: {csv_path}")
        
    try:
        df = pd.read_csv(csv_path)
        if df.empty:
            logger.error("CSV file is empty")
            raise pd.errors.EmptyDataError("CSV file contains no data")
            
        required_columns = {
            "points", "bench", "hits", "captain_points", "team", 
            "chip", "gw", "entry_name", "captain_id", "transfer_gain"
        }
        
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            raise ValueError(f"CSV file is missing required columns: {missing_columns}")
            
        logger.info(f"Successfully loaded {len(df)} records from CSV")
        
    except pd.errors.ParserError as e:
        logger.error(f"Error parsing CSV file: {str(e)}")
        raise ValueError(f"Invalid CSV format: {str(e)}")
        
    # Load player mapping
    id_to_name: Dict[int, str] = {}
    try:
        if Path(player_mapping_path).exists():
            mapping = pd.read_json(player_mapping_path)
            id_to_name = dict(zip(mapping["id"], mapping["name"]))
            logger.info(f"Successfully loaded {len(id_to_name)} player mappings")
        else:
            logger.warning(f"Player mapping file not found: {player_mapping_path}")
            
    except Exception as e:
        logger.error(f"Error loading player mappings: {str(e)}")
        logger.warning("Continuing without player mappings")
        
    return df, id_to_name

def calculate_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate main aggregated statistics for each team."""
    try:
        num_gw = df["gw"].nunique()
        
        # Main aggregation
        agg = df.groupby("entry_name").agg({
            "points": "sum",
            "bench": "sum",
            "hits": "sum",
            "captain_points": "sum",
            "transfer_gain": "sum",
            "event_transfers": "sum"
        }).reset_index()

        # Adding calculated columns
        agg["avg_gw_points"] = df.groupby("entry_name")["points"].mean().values
        agg["avg_bench_points"] = df.groupby("entry_name")["bench"].mean().values
        agg["efficiency"] = (agg["points"] - agg["hits"]) / num_gw
        
        # Calculate transfer losses (ensure no NaN values)
        transfer_losses = df[df["transfer_gain"] < 0].groupby("entry_name")["transfer_gain"].sum()
        agg["transfer_loss"] = agg["entry_name"].map(transfer_losses).fillna(0)
        
        agg["total_hits"] = agg["hits"].div(4).astype(int)
        agg["max_bench_points"] = df[df["chip"] != "bboost"].groupby("entry_name")["bench"].sum().values

        # Best and worst gameweeks counts
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

        return agg
        
    except Exception as e:
        logger.error(f"Error calculating aggregates: {str(e)}")
        raise

def process_manager_data(df: pd.DataFrame) -> pd.DataFrame:
    """Process manager chip data."""
    try:
        manager_df = df[df["chip"] == "manager"].copy()
        manager_df["team_list"] = manager_df["team"].dropna().apply(literal_eval)
        manager_df["manager_points"] = manager_df["team_list"].apply(
            lambda x: x[-1].get("points", 0) if isinstance(x, list) and len(x) > 0 else 0
        )
        return manager_df
        
    except Exception as e:
        logger.error(f"Error processing manager data: {str(e)}")
        raise

def extract_manager_points(team_list: List[Dict[str, Any]]) -> int:
    """Extract points from the manager chip team list."""
    if isinstance(team_list, list) and len(team_list) > 0:
        last_player = team_list[-1]
        return last_player.get("points", 0)
    return 0

def validate_data(df: pd.DataFrame) -> None:
    """Validate the input DataFrame for required columns and data quality."""
    required_columns = {
        "points", "bench", "hits", "captain_points", "team", 
        "chip", "gw", "entry_name", "captain_id", "transfer_gain"
    }
    
    # Check for required columns
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
        
    # Check for empty DataFrame
    if df.empty:
        raise ValueError("DataFrame is empty")
        
    # Check for minimum required data
    if df["gw"].nunique() < 1:
        raise ValueError("No gameweeks found in data")
        
    if df["entry_name"].nunique() < 1:
        raise ValueError("No team entries found in data")

def analyze_streaks(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze winning and losing streaks for each team.
    
    Returns DataFrame with columns:
    - longest_good_streak: Longest streak of above average points
    - longest_bad_streak: Longest streak of below average points
    - current_streak: Current streak (positive for good, negative for bad)
    """
    # Calculate average points per GW
    avg_points = df.groupby('gw')['points'].mean()
    
    streaks = pd.DataFrame()
    for name, team_df in df.groupby('entry_name'):
        good_streak = 0
        bad_streak = 0
        max_good = 0
        max_bad = 0
        current = 0
        
        for gw in sorted(team_df['gw'].unique()):
            points = team_df[team_df['gw'] == gw]['points'].iloc[0]
            if points > avg_points[gw]:
                if current >= 0:
                    current += 1
                else:
                    current = 1
                good_streak = max(good_streak, current)
            else:
                if current <= 0:
                    current -= 1
                else:
                    current = -1
                bad_streak = min(bad_streak, current)
                
        max_good = max(max_good, good_streak)
        max_bad = max(max_bad, abs(bad_streak))
        
        streaks.loc[name, 'longest_good_streak'] = max_good
        streaks.loc[name, 'longest_bad_streak'] = max_bad
        streaks.loc[name, 'current_streak'] = current
    
    return streaks

def analyze_h2h(df: pd.DataFrame) -> pd.DataFrame:
    """Generate head-to-head comparisons between all teams.
    
    Returns DataFrame with:
    - team_1, team_2: Team names
    - wins_1, wins_2: Number of GWs where each team scored more points
    - avg_margin: Average points difference
    """
    teams = df['entry_name'].unique()
    h2h_data = []
    
    for i, team1 in enumerate(teams):
        for team2 in teams[i+1:]:
            team1_data = df[df['entry_name'] == team1]
            team2_data = df[df['entry_name'] == team2]
            
            merged = pd.merge(
                team1_data[['gw', 'points']], 
                team2_data[['gw', 'points']], 
                on='gw', 
                suffixes=('_1', '_2')
            )
            
            wins_1 = (merged['points_1'] > merged['points_2']).sum()
            wins_2 = (merged['points_2'] > merged['points_1']).sum()
            margin = (merged['points_1'] - merged['points_2']).mean()
            
            h2h_data.append({
                'team_1': team1,
                'team_2': team2,
                'wins_1': wins_1,
                'wins_2': wins_2,
                'avg_margin': margin
            })
    
    return pd.DataFrame(h2h_data)

def analyze_chip_timing(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze chip usage timing and effectiveness.
    
    Returns DataFrame with:
    - chip: Chip name
    - avg_points_early: Average points when used in GW1-19
    - avg_points_late: Average points when used in GW20-38
    - best_gw: Gameweek where the chip was most effective
    """
    chip_stats = []
    
    for chip in ['3xc', 'bboost', 'freehit', 'wildcard1', 'wildcard2']:
        chip_df = df[df['chip'] == chip]
        if len(chip_df) == 0:
            continue
            
        early = chip_df[chip_df['gw'] <= 19]['points'].mean()
        late = chip_df[chip_df['gw'] > 19]['points'].mean()
        best_gw = chip_df.loc[chip_df['points'].idxmax(), 'gw']
        
        chip_stats.append({
            'chip': chip,
            'avg_points_early': early,
            'avg_points_late': late,
            'best_gw': best_gw
        })
    
    return pd.DataFrame(chip_stats)

def analyze_player_loyalty(df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
    """Analyze which players stayed longest in each team.
    
    Returns dictionary with team names as keys and lists of:
    - player_id: Player ID
    - weeks_owned: Number of consecutive weeks owned
    - avg_points: Average points while owned
    """
    loyalty_data = {}
    
    for name, team_df in df.groupby('entry_name'):
        player_history = {}
        loyal_players = []
        
        for _, row in team_df.sort_values('gw').iterrows():
            current_team = {p['player_id']: p['points'] for p in literal_eval(row['team'])}
            
            # Update player histories
            for pid, points in current_team.items():
                if pid not in player_history:
                    player_history[pid] = {'weeks': 1, 'points': [points], 'current_streak': 1}
                else:
                    if player_history[pid]['current_streak'] > 0:
                        player_history[pid]['current_streak'] += 1
                        player_history[pid]['weeks'] = max(
                            player_history[pid]['weeks'],
                            player_history[pid]['current_streak']
                        )
                    else:
                        player_history[pid]['current_streak'] = 1
                    player_history[pid]['points'].append(points)
            
            # Check for removed players
            for pid in player_history:
                if pid not in current_team:
                    player_history[pid]['current_streak'] = 0
        
        # Create final list of loyal players
        for pid, data in player_history.items():
            if data['weeks'] >= 5:  # Min 5 weeks to be considered loyal
                loyal_players.append({
                    'player_id': pid,
                    'weeks_owned': data['weeks'],
                    'avg_points': sum(data['points']) / len(data['points'])
                })
        
        loyalty_data[name] = sorted(loyal_players, key=lambda x: x['weeks_owned'], reverse=True)
    
    return loyalty_data

def analyze_transfer_timing(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze transfer timing effectiveness.
    
    Returns DataFrame with:
    - total_transfers: Total number of transfers made
    - avg_points_per_transfer: Average points gained from transfers
    """
    timing_stats = pd.DataFrame()
    
    for name, team_df in df.groupby('entry_name'):
        timing_stats.loc[name, 'total_transfers'] = team_df['event_transfers'].sum()
        timing_stats.loc[name, 'avg_points_per_transfer'] = (
            team_df['transfer_gain'].sum() / 
            max(team_df['event_transfers'].sum(), 1)  # Avoid division by zero
        )
    
    return timing_stats

def predict_performance(df: pd.DataFrame, weeks_ahead: int = 5) -> pd.DataFrame:
    """Predict team performance for upcoming gameweeks using historical data.
    
    Uses a simple moving average model weighted by:
    - Recent form (last 5 GWs)
    - Season average
    - Historical performance in similar GWs
    
    Returns DataFrame with:
    - predicted_points: Expected points for next GWs
    - form_trend: Trend direction (positive/negative)
    - confidence: Prediction confidence score
    """
    predictions = pd.DataFrame()
    current_gw = df['gw'].max()
    
    for name, team_df in df.groupby('entry_name'):
        # Recent form (last 5 GWs)
        recent_form = team_df[team_df['gw'] > current_gw - 5]['points'].mean()
        
        # Season average
        season_avg = team_df['points'].mean()
        
        # Historical performance in similar GWs
        historical = []
        for week in range(current_gw + 1, current_gw + weeks_ahead + 1):
            similar_gw = week % 38 if week > 38 else week
            hist_points = team_df[team_df['gw'] == similar_gw]['points'].values
            if len(hist_points) > 0:
                historical.append(hist_points[0])
        hist_avg = sum(historical) / len(historical) if historical else season_avg
        
        # Weight the factors
        predicted = (0.5 * recent_form) + (0.3 * season_avg) + (0.2 * hist_avg)
        
        # Calculate trend
        trend = 'positive' if recent_form > season_avg else 'negative'
        
        # Calculate confidence based on consistency
        consistency = 1 - (team_df['points'].std() / team_df['points'].mean())
        confidence = min(max(consistency * 100, 0), 100)
        
        predictions.loc[name, 'predicted_points'] = predicted
        predictions.loc[name, 'form_trend'] = trend
        predictions.loc[name, 'confidence'] = confidence
    
    return predictions

def analyze_team_correlation(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze similarities between team structures and strategies.
    
    Returns DataFrame with:
    - team_1, team_2: Team names
    - squad_similarity: % of shared players
    - captain_similarity: % of same captain choices
    - transfer_correlation: Correlation in transfer patterns
    - chip_similarity: % of chips used in same GWs
    """
    teams = df['entry_name'].unique()
    correlations = []
    
    for i, team1 in enumerate(teams):
        for team2 in teams[i+1:]:
            team1_df = df[df['entry_name'] == team1]
            team2_df = df[df['entry_name'] == team2]
            
            # Calculate squad similarity
            squad_similarity = []
            captain_same_gws = 0
            chip_same_gws = 0
            
            for gw in df['gw'].unique():
                t1_gw = team1_df[team1_df['gw'] == gw]
                t2_gw = team2_df[team2_df['gw'] == gw]
                
                if len(t1_gw) == 0 or len(t2_gw) == 0:
                    continue
                
                # Squad similarity
                t1_players = {p['player_id'] for p in literal_eval(t1_gw['team'].iloc[0])}
                t2_players = {p['player_id'] for p in literal_eval(t2_gw['team'].iloc[0])}
                similarity = len(t1_players & t2_players) / len(t1_players | t2_players)
                squad_similarity.append(similarity)
                
                # Captain similarity
                if t1_gw['captain_id'].iloc[0] == t2_gw['captain_id'].iloc[0]:
                    captain_same_gws += 1
                    
                # Chip similarity
                if t1_gw['chip'].iloc[0] == t2_gw['chip'].iloc[0] and t1_gw['chip'].iloc[0]:
                    chip_same_gws += 1
            
            # Transfer correlation
            merged_transfers = pd.merge(
                team1_df[['gw', 'event_transfers']],
                team2_df[['gw', 'event_transfers']],
                on='gw'
            )
            transfer_corr = merged_transfers['event_transfers_x'].corr(merged_transfers['event_transfers_y'])
            
            correlations.append({
                'team_1': team1,
                'team_2': team2,
                'squad_similarity': sum(squad_similarity) / len(squad_similarity),
                'captain_similarity': captain_same_gws / len(df['gw'].unique()),
                'transfer_correlation': transfer_corr,
                'chip_similarity': chip_same_gws / max(1, len(df[df['chip'] != '']))
            })
    
    return pd.DataFrame(correlations)

def track_league_positions(df: pd.DataFrame) -> pd.DataFrame:
    """Track team positions throughout the season.
    
    Returns DataFrame with:
    - highest_position: Best position achieved
    - lowest_position: Worst position achieved
    - weeks_at_top: Number of weeks at position 1
    - avg_position: Average position throughout season
    - position_changes: Number of position changes
    - current_streak: Current number of weeks at same position
    """
    positions = pd.DataFrame()
    position_history = {}
    num_teams = len(df['entry_name'].unique())
    
    # Calculate cumulative points and positions for each gameweek
    for gw in sorted(df['gw'].unique()):
        gw_data = df[df['gw'] == gw].copy()
        gw_data['cum_points'] = df[df['gw'] <= gw].groupby('entry_name')['points'].sum()
        gw_data = gw_data.sort_values('cum_points', ascending=False)
        gw_data['position'] = range(1, len(gw_data) + 1)
        
        for _, row in gw_data.iterrows():
            team = row['entry_name']
            pos = row['position']
            
            if team not in position_history:
                position_history[team] = {
                    'positions': [pos],
                    'highest': pos,
                    'lowest': pos,
                    'weeks_at_top': 1 if pos == 1 else 0,
                    'current_streak': 1
                }
            else:
                hist = position_history[team]
                hist['positions'].append(pos)
                hist['highest'] = min(hist['highest'], pos)
                hist['lowest'] = max(hist['lowest'], pos)
                hist['weeks_at_top'] += 1 if pos == 1 else 0
                
                if pos == hist['positions'][-2]:
                    hist['current_streak'] += 1
                else:
                    hist['current_streak'] = 1
    
    # Compile final statistics
    for team, hist in position_history.items():
        positions.loc[team, 'highest_position'] = hist['highest']
        positions.loc[team, 'lowest_position'] = hist['lowest']
        positions.loc[team, 'weeks_at_top'] = hist['weeks_at_top']
        positions.loc[team, 'avg_position'] = sum(hist['positions']) / len(hist['positions'])
        positions.loc[team, 'position_changes'] = sum(
            1 for i in range(1, len(hist['positions']))
            if hist['positions'][i] != hist['positions'][i-1]
        )
        positions.loc[team, 'current_streak'] = hist['current_streak']
    
    return positions

def analyze_what_if(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze alternative scenarios and their potential impact.
    
    Returns DataFrame with various 'what-if' scenarios:
    - points_with_best_captains: Points if always picked best captain
    - points_without_hits: Points if never took transfer hits
    - points_with_best_bench: Points if always had optimal bench
    - optimal_chip_gains: Points gained if used chips in optimal GWs
    """
    whatif = pd.DataFrame()
    
    for name, team_df in df.groupby('entry_name'):
        actual_points = team_df['points'].sum()
        
        # Best possible captains
        max_captain_points = team_df.groupby('gw')['captain_points'].max()
        best_captain_total = actual_points - team_df['captain_points'].sum() + max_captain_points.sum()
        
        # No transfer hits
        no_hits_total = actual_points + team_df['hits'].sum()
        
        # Optimal bench usage
        bench_points = team_df['bench'].sum()
        optimal_bench = team_df[team_df['chip'] != 'bboost']['bench'].sort_values(ascending=False)
        optimal_bench = optimal_bench[:11].sum()  # Best 11 bench decisions
        
        # Optimal chip usage
        chip_gains = {}
        for chip in ['3xc', 'bboost', 'freehit']:
            if chip in team_df['chip'].values:
                actual_gw = team_df[team_df['chip'] == chip]['points'].iloc[0]
                best_gw = df[df['chip'] == chip]['points'].max()
                chip_gains[chip] = best_gw - actual_gw
        
        whatif.loc[name, 'points_with_best_captains'] = best_captain_total
        whatif.loc[name, 'points_without_hits'] = no_hits_total
        whatif.loc[name, 'points_with_best_bench'] = actual_points + (optimal_bench - bench_points)
        whatif.loc[name, 'optimal_chip_gains'] = sum(chip_gains.values())
        
    return whatif
