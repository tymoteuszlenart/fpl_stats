"""
FPL Dashboard

This module contains functions for generating interactive visualizations for the FPL season report.
"""

import logging
from typing import Dict, List, Tuple

import pandas as pd
import numpy as np
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

logger = logging.getLogger(__name__)

# Color schemes and plot configurations
PLOT_CONFIGS = [
    ("captain_points", "Punkty kapitanów", "Viridis"),
    ("avg_gw_points", "Średnia punktowa", "Plasma"),
    ("efficiency", "Ranking efektywności", "Cividis"),
    ("bench", "Punkty zawodników na ławce", "Magma"),
    ("avg_bench_points", "Średnia punktów na ławce", "Inferno"),
    ("total_hits", "Ilość hitów", "Turbo"),
    ("best_gw_count", "Ilość najlepszych wyników w kolejce", "Blues"),
    ("worst_gw_count", "Ilość najgorszych wyników w kolejce", "Reds"),
]

def create_statistics_figure(agg: pd.DataFrame) -> go.Figure:
    """Create statistical plots."""
    fig = make_subplots(
        rows=len(PLOT_CONFIGS), 
        cols=1,
        subplot_titles=[title for _, title, _ in PLOT_CONFIGS],
        vertical_spacing=0.05
    )
    
    for idx, (plot_metric, title, colorscale) in enumerate(PLOT_CONFIGS, start=1):
        data = agg.sort_values(plot_metric, ascending=False)  # Sort descending
        
        fig.add_trace(
            go.Bar(
                x=data[plot_metric],
                y=data.index,
                orientation='h',
                name=title,
                text=[f"{val:.1f}" for val in data[plot_metric]],
                textposition='outside',
                marker_color=data[plot_metric],
                marker_colorscale=colorscale,
                hovertemplate=(
                    f"{title}<br>" +
                    "Drużyna: %{y}<br>" +
                    "Wartość: %{x:.1f}<br>" +
                    "<extra></extra>"
                )
            ),
            row=idx, 
            col=1
        )
        
        # Update axes with more space for labels
        fig.update_xaxes(
            title_text=title, 
            row=idx, 
            col=1,
            side='top'  # Move x-axis title to top
        )
        fig.update_yaxes(
            title_text="Drużyna", 
            row=idx, 
            col=1,
            tickfont={'size': 10},  # Smaller font for team names
            ticksuffix="   "  # Add padding after team names
        )
    
    fig.update_layout(
        height=300 * len(PLOT_CONFIGS),
        showlegend=False,
        title={
            'text': "Statystyki sezonu",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24}
        },
        hoverlabel=dict(
            bgcolor="white",
            font_size=14
        ),
        margin=dict(l=150, r=50, t=100, b=50)  # Increase left margin for team names
    )
    
    return fig

def create_form_streaks_figure(streak_data: pd.DataFrame) -> go.Figure:
    """Create team form streaks visualization."""
    data = streak_data.sort_values('longest_good_streak', ascending=False)
    
    fig = go.Figure()
    
    # Add good streaks
    fig.add_trace(go.Bar(
        name='Najdłuższa seria powyżej średniej',
        x=data.index,
        y=data['longest_good_streak'],
        marker_color='green',
        opacity=0.6,
        hovertemplate=(
            "Drużyna: %{x}<br>" +
            "Długość serii: %{y} tygodni<br>" +
            "<extra></extra>"
        )
    ))
    
    # Add bad streaks
    fig.add_trace(go.Bar(
        name='Najdłuższa seria poniżej średniej',
        x=data.index,
        y=-data['longest_bad_streak'],
        marker_color='red',
        opacity=0.6,
        hovertemplate=(
            "Drużyna: %{x}<br>" +
            "Długość serii: %{y} tygodni<br>" +
            "<extra></extra>"
        )
    ))
    
    # Add current streaks as scatter points
    current_pos = data[data['current_streak'] > 0]
    current_neg = data[data['current_streak'] < 0]
    
    if not current_pos.empty:
        fig.add_trace(go.Scatter(
            x=current_pos.index,
            y=current_pos['current_streak'],
            mode='markers',
            marker=dict(color='green', size=15),
            name='Aktualna seria powyżej średniej',
            hovertemplate=(
                "Drużyna: %{x}<br>" +
                "Aktualna seria: %{y} tygodni<br>" +
                "<extra></extra>"
            )
        ))
    
    if not current_neg.empty:
        fig.add_trace(go.Scatter(
            x=current_neg.index,
            y=current_neg['current_streak'],
            mode='markers',
            marker=dict(color='red', size=15),
            name='Aktualna seria poniżej średniej',
            hovertemplate=(
                "Drużyna: %{x}<br>" +
                "Aktualna seria: %{y} tygodni<br>" +
                "<extra></extra>"
            )
        ))
    
    fig.update_layout(
        title={
            'text': 'Serie form drużyn',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24}
        },
        yaxis_title='Długość serii (tygodni)',
        xaxis_title='Drużyna',
        barmode='overlay',
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, t=100, b=100),  # Increase bottom margin
        xaxis=dict(
            tickangle=45,  # Rotate team names
            tickfont=dict(size=10)  # Smaller font for team names
        ),
        annotations=[
            dict(
                x=0.5,
                y=-0.3,  # Move annotation lower
                xref="paper",
                yref="paper",
                text="Zielone słupki pokazują najdłuższe serie punktowania powyżej średniej ligi.<br>" +
                     "Czerwone słupki pokazują najdłuższe serie punktowania poniżej średniej.<br>" +
                     "Kropki pokazują aktualną serię każdej drużyny.",
                showarrow=False,
                align="center"
            )
        ]
    )
    
    return fig

def create_h2h_figure(h2h_data: pd.DataFrame) -> go.Figure:
    """Create head-to-head comparison visualization."""
    teams = sorted(set(h2h_data['team_1'].unique()) | set(h2h_data['team_2'].unique()))
    n_teams = len(teams)
    matrix = np.zeros((n_teams, n_teams), dtype=np.float64)
    games_matrix = np.zeros((n_teams, n_teams), dtype=np.int32)
    
    # Fill the matrix with win ratios and total games
    for _, row in h2h_data.iterrows():
        i = teams.index(row['team_1'])
        j = teams.index(row['team_2'])
        total_games = int(row['wins_1']) + int(row['wins_2'])
        if total_games > 0:
            win_ratio = float(row['wins_1']) / total_games
            matrix[i, j] = win_ratio
            matrix[j, i] = 1.0 - win_ratio
            games_matrix[i, j] = total_games
            games_matrix[j, i] = total_games
    
    hover_text = [[
        f"{row_team} vs {col_team}<br>" +
        f"Wygrane {row_team}: {int(matrix[i,j] * games_matrix[i,j])} ({matrix[i,j]:.0%})<br>" +
        f"Wygrane {col_team}: {int((1-matrix[i,j]) * games_matrix[i,j])} ({1-matrix[i,j]:.0%})<br>" +
        f"Rozegrane kolejki: {games_matrix[i,j]}"
        for j, col_team in enumerate(teams)
    ] for i, row_team in enumerate(teams)]
    
    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=teams,
        y=teams,
        colorscale=[
            [0, '#FF4136'],      # Red for 0% win rate
            [0.5, '#FFDC00'],    # Yellow for 50% win rate
            [1, '#2ECC40']       # Green for 100% win rate
        ],
        text=np.round(matrix * 100, 1),
        texttemplate='%{text}%',
        textfont={"size": 12},
        hoverongaps=False,
        hoverinfo='text',
        hovertext=hover_text,
        colorbar=dict(
            title=dict(
                text='Procent wygranych kolejek',
                side='right'
            ),
            tickformat=',.0%',
            ticks='outside'
        )
    ))
    
    fig.update_layout(
        title={
            'text': 'Bezpośrednie pojedynki w sezonie',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24}
        },
        xaxis_title='Przeciwnik',
        yaxis_title='Drużyna',
        xaxis={
            'side': 'bottom',
            'tickangle': 45,  # Rotate team names
            'tickfont': {'size': 10}  # Smaller font
        },
        yaxis={
            'tickfont': {'size': 10}  # Smaller font
        },
        margin=dict(l=150, r=50, t=100, b=150),  # Increase margins
        annotations=[dict(
            text='Każde pole pokazuje procent wygranych kolejek drużyny z Y-osi przeciwko drużynie z X-osi',
            x=0.5, y=-0.35,  # Move annotation lower
            xref='paper', yref='paper',
            showarrow=False,
            align='center'
        )]
    )
    
    return fig

def create_league_positions_figure(df: pd.DataFrame) -> go.Figure:
    """Create league position changes visualization."""
    positions_by_gw = []
    
    # Get unique gameweeks and sort them
    gameweeks = sorted(df['gw'].unique())
    
    # Calculate cumulative points and positions for each gameweek
    for gw in gameweeks:
        # Get data for current and previous gameweeks
        gw_data = df[df['gw'] <= gw].copy()
        
        # Calculate cumulative points for each team up to current gameweek
        team_points = gw_data.groupby('entry_name')['points'].sum().reset_index()
        
        # Get points just for this gameweek
        weekly_points = df[df['gw'] == gw].groupby('entry_name')['points'].first()
        
        # Sort by points to determine positions
        team_points = team_points.sort_values('points', ascending=False)
        team_points['position'] = range(1, len(team_points) + 1)
        
        # Add gameweek number and weekly points
        team_points['gw'] = gw
        team_points['weekly_points'] = team_points['entry_name'].map(weekly_points)
        
        positions_by_gw.append(team_points)
    
    # Combine all gameweek data
    position_df = pd.concat(positions_by_gw)
    
    fig = go.Figure()
    
    # Create a unique color for each team
    colors = px.colors.qualitative.Set3
    team_colors = {team: colors[i % len(colors)] 
                  for i, team in enumerate(position_df['entry_name'].unique())}
    
    # Add trace for each team
    for name in sorted(position_df['entry_name'].unique()):
        team_data = position_df[position_df['entry_name'] == name]
        fig.add_trace(go.Scatter(
            x=team_data['gw'],
            y=team_data['position'],
            mode='lines+markers',
            name=name,
            line=dict(
                color=team_colors[name],
                width=2
            ),
            marker=dict(
                size=8,
                color=team_colors[name],
                line=dict(width=1, color='white')
            ),
            hovertemplate=(
                "<b>%{text}</b><br>" +
                "Kolejka: %{x}<br>" +
                "Pozycja: %{y}<br>" +
                "Punkty w kolejce: %{customdata[1]:.0f}<br>" +
                "Suma punktów: %{customdata[0]:.0f}<br>" +
                "<extra></extra>"
            ),
            text=[name for _ in range(len(team_data))],
            customdata=team_data[['points', 'weekly_points']].values
        ))
    
    fig.update_layout(
        title={
            'text': 'Historia pozycji w lidze',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24}
        },
        xaxis_title='Kolejka',
        yaxis_title='Pozycja',
        yaxis_autorange='reversed',  # Position 1 at the top
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        annotations=[dict(
            text='Wykres pokazuje zmiany pozycji drużyn w kolejnych kolejkach.<br>Pozycja 1 oznacza lidera.',
            x=0.5, y=-0.15,
            xref='paper', yref='paper',
            showarrow=False,
            align='center'
        )],
        margin=dict(l=50, r=50, t=100, b=100),  # Adjust margins
    )
    
    # Update axis properties
    fig.update_xaxes(
        tickmode='linear',
        dtick=1,
        tickangle=0,
        gridcolor='lightgray'
    )
    fig.update_yaxes(
        tickmode='linear',
        dtick=1,
        gridcolor='lightgray'
    )
    
    return fig

def create_what_if_figure(whatif: pd.DataFrame, actual_points: pd.Series) -> go.Figure:
    """Create 'what-if' scenario visualization."""
    scenarios = [
        ('points_with_best_captains', 'Najlepsi kapitanowie', 'Liczba dodatkowych punktów, gdyby drużyna zawsze wybrała najlepszego kapitana w każdej kolejce'),
        ('points_without_hits', 'Bez hitów', 'Liczba punktów straconych na dodatkowych transferach (-4 za każdy dodatkowy transfer)'),
        ('points_with_best_bench', 'Optymalna ławka', 'Liczba punktów utraconych przez nieoptymalne ustawienie składu w każdej kolejce'),
    ]
    
    # Calculate potential gains
    gains = pd.DataFrame(index=whatif.index)
    for col, label, _ in scenarios:
        gains[label] = whatif[col] - actual_points
    
    fig = go.Figure()
    
    colors = {
        'Najlepsi kapitanowie': '#2ECC40',  # Green
        'Bez hitów': '#FF851B',             # Orange
        'Optymalna ławka': '#0074D9'        # Blue
    }
    
    for col, label, description in scenarios:
        hover_text = [
            f"<b>{team}</b><br>" +
            f"{label}:<br>" +
            f"• Aktualne punkty: {actual_points[team]:.0f}<br>" +
            f"• Potencjalne punkty: {whatif.loc[team, col]:.0f}<br>" +
            f"• Różnica: {gains[label][team]:+.0f} pkt"
            for team in gains.index
        ]
        
        fig.add_trace(go.Bar(
            name=label,
            x=gains.index,
            y=gains[label],
            text=gains[label].round(0).astype(int).apply(lambda x: f"{x:+d}"),
            textposition='outside',
            marker_color=colors[label],
            hovertext=hover_text,
            hoverinfo='text'
        ))
    
    fig.update_layout(
        title={
            'text': 'Analiza "Co gdyby?" - Potencjalne zyski punktowe',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24}
        },
        xaxis_title='Drużyna',
        yaxis_title='Różnica punktowa',
        barmode='group',
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Add explanatory annotation
    explanations = "<br>".join([f"• {label}: {desc}" for _, label, desc in scenarios])
    fig.add_annotation(
        text=f"Analiza pokazuje potencjalne zyski punktowe w różnych scenariuszach:<br>{explanations}",
        x=0.5, y=-0.25,
        xref='paper', yref='paper',
        showarrow=False,
        align='left'
    )
    
    return fig

def create_team_correlation_figure(corr_data: pd.DataFrame) -> go.Figure:
    """Create team correlation network visualization."""
    # Create network layout
    G = nx.Graph()
    
    # Add edges with normalized weights
    max_sim = corr_data['squad_similarity'].max()
    min_sim = corr_data['squad_similarity'].min()
    edge_x = []
    edge_y = []
    edge_colors = []
    edge_widths = []
    edge_hover = []
    
    # Create color scale
    def get_color(value):
        """Convert similarity value to color."""
        return f'rgba(99, 110, {int(255*value)}, 0.6)'
    
    for _, row in corr_data.iterrows():
        team1 = str(row['team_1'])
        team2 = str(row['team_2'])
        try:
            squad_sim = float(row['squad_similarity'])
            # Normalize similarity to 0-1 range
            norm_sim = (squad_sim - min_sim) / (max_sim - min_sim) if max_sim != min_sim else 0.5
            G.add_edge(team1, team2, weight=squad_sim, norm_weight=norm_sim)
            edge_colors.append(get_color(norm_sim))
            edge_widths.append(1 + 3 * norm_sim)
            edge_hover.append(f"{team1} - {team2}<br>Podobieństwo: {squad_sim:.1%}")
        except (ValueError, TypeError):
            continue
    
    # Use spring layout with weights for better spacing
    pos = nx.spring_layout(G, k=1/np.sqrt(len(G.nodes())), iterations=50)
    
    # Create edge traces with dummy trace for colorbar
    edge_traces = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        norm_weight = G.edges[edge]['norm_weight']
        edge_trace = go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            line=dict(
                width=1 + 3 * norm_weight,
                color=get_color(norm_weight)
            ),
            hoverinfo='text',
            text=[f"{edge[0]} - {edge[1]}<br>Podobieństwo: {G.edges[edge]['weight']:.1%}"],
            mode='lines',
            showlegend=False
        )
        edge_traces.append(edge_trace)
    
    # Create node trace
    node_x = []
    node_y = []
    node_text = []
    node_sizes = []
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
        # Node size based on average similarity
        avg_sim = np.mean([G.edges[edge]['weight'] 
                          for edge in G.edges(node)])
        node_sizes.append(20 + 30 * avg_sim)
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=node_text,
        textposition="top center",
        marker=dict(
            showscale=True,
            colorscale='Viridis',
            size=node_sizes,
            color=node_sizes,
            line=dict(width=2, color='white'),
            colorbar=dict(
                title=dict(
                    text='Średnie podobieństwo',
                    side='right'
                ),
                thickness=15,
                xanchor='left'
            )
        )
    )
    
    # Combine all traces
    traces = edge_traces + [node_trace]
    
    fig = go.Figure(data=traces,
                   layout=go.Layout(
                       title={
                           'text': 'Sieć podobieństw składów drużyn',
                           'x': 0.5,
                           'xanchor': 'center',
                           'font': {'size': 24}
                       },
                       showlegend=False,
                       hovermode='closest',
                       margin=dict(l=50, r=50, t=100, b=150),  # Increase bottom margin
                       annotations=[
                           dict(
                               text=(
                                   "Wykres pokazuje podobieństwa między składami drużyn:<br>" +
                                   "• Grubość linii oznacza stopień podobieństwa składów<br>" +
                                   "• Wielkość węzłów pokazuje średnie podobieństwo do innych drużyn<br>" +
                                   "• Kolory węzłów i linii reprezentują siłę powiązań"
                               ),
                               x=0.5, y=-0.35,  # Move annotation lower
                               xref='paper', yref='paper',
                               showarrow=False,
                               align='center',
                               bgcolor='rgba(255, 255, 255, 0.9)',  # Add semi-transparent background
                               bordercolor='rgba(0, 0, 0, 0.3)',
                               borderwidth=1,
                               borderpad=4
                           )
                       ],
                       xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       plot_bgcolor='rgba(255,255,255,0.8)',
                       paper_bgcolor='rgba(255,255,255,0.8)'
                   ))
    
    return fig

def create_dashboard(df: pd.DataFrame, agg: pd.DataFrame, streak_data: pd.DataFrame, 
                    h2h_data: pd.DataFrame, whatif: pd.DataFrame, 
                    corr_data: pd.DataFrame) -> dash.Dash:
    """Create the main dashboard."""
    app = dash.Dash(__name__)
    
    app.layout = html.Div([
        # Header
        html.Div([
            html.H1('Analiza sezonu Fantasy Premier League', 
                   style={'textAlign': 'center', 'marginBottom': '20px'}),
            html.P('To interaktywne podsumowanie pokazuje szczegółową analizę wyników drużyn w sezonie.',
                  style={'textAlign': 'center', 'fontSize': '16px'})
        ], style={'marginBottom': '40px'}),
        
        # Main Statistics Section
        html.Div([
            html.H2('Statystyki ogólne', style={'textAlign': 'center'}),
            html.P('Kluczowe wskaźniki dla każdej drużyny w sezonie, w tym punkty, efektywność i wybory kapitanów.',
                  style={'textAlign': 'center', 'marginBottom': '20px'}),
            dcc.Graph(id='statistics-plot', figure=create_statistics_figure(agg))
        ], style={'marginBottom': '40px'}),
        
        # Form Streaks Section
        html.Div([
            html.H2('Serie i forma', style={'textAlign': 'center'}),
            html.P('Analiza okresów dobrej i słabej formy każdej drużyny w trakcie sezonu.',
                  style={'textAlign': 'center', 'marginBottom': '20px'}),
            dcc.Graph(id='streaks-plot', figure=create_form_streaks_figure(streak_data))
        ], style={'marginBottom': '40px'}),
        
        # Head to Head Section
        html.Div([
            html.H2('Pojedynki bezpośrednie', style={'textAlign': 'center'}),
            html.P('Macierz wyników bezpośrednich spotkań między wszystkimi drużynami.',
                  style={'textAlign': 'center', 'marginBottom': '20px'}),
            dcc.Graph(id='h2h-plot', figure=create_h2h_figure(h2h_data))
        ], style={'marginBottom': '40px'}),
        
        # League Positions Section
        html.Div([
            html.H2('Historia pozycji', style={'textAlign': 'center'}),
            html.P('Śledzenie zmian pozycji drużyn w tabeli w trakcie sezonu.',
                  style={'textAlign': 'center', 'marginBottom': '20px'}),
            dcc.Graph(id='positions-plot', figure=create_league_positions_figure(df))
        ], style={'marginBottom': '40px'}),
        
        # What If Analysis Section
        html.Div([
            html.H2('Analiza "Co gdyby?"', style={'textAlign': 'center'}),
            html.P('Porównanie rzeczywistych wyników z potencjalnymi w różnych scenariuszach.',
                  style={'textAlign': 'center', 'marginBottom': '20px'}),
            dcc.Graph(id='whatif-plot', 
                     figure=create_what_if_figure(whatif, df.groupby('entry_name')['points'].sum()))
        ], style={'marginBottom': '40px'}),
        
        # Team Correlations Section
        html.Div([
            html.H2('Podobieństwa drużyn', style={'textAlign': 'center'}),
            html.P('Wizualizacja podobieństw między składami drużyn w formie sieci powiązań.',
                  style={'textAlign': 'center', 'marginBottom': '20px'}),
            dcc.Graph(id='correlation-plot', figure=create_team_correlation_figure(corr_data))
        ], style={'marginBottom': '40px'}),
        
        # Footer
        html.Div([
            html.Hr(),
            html.P('Dashboard aktualizowany automatycznie na podstawie danych z Fantasy Premier League.',
                  style={'textAlign': 'center', 'fontSize': '12px', 'color': '#666'})
        ])
    ], style={
        'maxWidth': '1200px',
        'margin': '0 auto',
        'padding': '20px',
        'fontFamily': 'Arial, sans-serif'
    })
    
    return app

def run_dashboard(df: pd.DataFrame, agg: pd.DataFrame, streak_data: pd.DataFrame,
                 h2h_data: pd.DataFrame, whatif: pd.DataFrame,
                 corr_data: pd.DataFrame, debug: bool = True) -> None:
    """Run the dashboard application."""
    app = create_dashboard(df, agg, streak_data, h2h_data, whatif, corr_data)
    app.run(debug=debug)
