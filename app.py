"""
Ergo-dash: A dashboard app to display videos and statistics using Dash.
"""
import os
from dash import Dash, html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime

# Initialize the Dash app with Bootstrap theme
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Sample data for statistics
def generate_sample_data():
    """Generate sample statistics data for demonstration."""
    dates = pd.date_range(start='2025-01-01', periods=30, freq='D')
    data = pd.DataFrame({
        'date': dates,
        'ergonomic_score': [70 + i * 0.5 + (i % 5) * 2 for i in range(30)],
        'posture_incidents': [10 - i * 0.2 + (i % 3) for i in range(30)],
        'activity_level': [50 + i * 0.8 + (i % 4) * 3 for i in range(30)]
    })
    return data

# Get sample data
df = generate_sample_data()

# Create sample videos directory structure
VIDEO_DIR = os.path.join(os.path.dirname(__file__), 'videos')
SAMPLE_VIDEOS = [
    {
        'name': 'Sample Ergonomic Assessment 1',
        'url': 'https://www.w3schools.com/html/mov_bbb.mp4',  # Sample video for demo
        'description': 'Proper sitting posture demonstration'
    },
    {
        'name': 'Sample Ergonomic Assessment 2',
        'url': 'https://www.w3schools.com/html/movie.mp4',  # Sample video for demo
        'description': 'Workspace setup best practices'
    }
]

# Create statistics figures
def create_ergonomic_score_chart():
    """Create an ergonomic score trend chart."""
    fig = px.line(df, x='date', y='ergonomic_score', 
                  title='Ergonomic Score Trend',
                  labels={'ergonomic_score': 'Score', 'date': 'Date'})
    fig.update_traces(line_color='#2E86AB', line_width=3)
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        hovermode='x unified'
    )
    return fig

def create_posture_incidents_chart():
    """Create a posture incidents chart."""
    fig = px.bar(df, x='date', y='posture_incidents',
                 title='Posture Incidents Over Time',
                 labels={'posture_incidents': 'Incidents', 'date': 'Date'})
    fig.update_traces(marker_color='#A23B72')
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        hovermode='x unified'
    )
    return fig

def create_activity_gauge():
    """Create an activity level gauge."""
    current_activity = df['activity_level'].iloc[-1]
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current_activity,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Current Activity Level"},
        delta={'reference': 70},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': "#F18F01"},
            'steps': [
                {'range': [0, 30], 'color': "#FFE5D9"},
                {'range': [30, 70], 'color': "#FFC2A1"},
                {'range': [70, 100], 'color': "#FFA07A"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    fig.update_layout(
        paper_bgcolor='white',
        font={'size': 12}
    )
    return fig

# App layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("Ergo-dash Dashboard", className="text-center text-primary mb-4"),
            html.P("Ergonomic Assessment and Video Analysis Dashboard", 
                   className="text-center text-muted mb-4")
        ])
    ]),
    
    # Video Section
    dbc.Row([
        dbc.Col([
            html.H3("Video Library", className="mb-3"),
            dcc.Dropdown(
                id='video-selector',
                options=[{'label': v['name'], 'value': i} 
                        for i, v in enumerate(SAMPLE_VIDEOS)],
                value=0,
                clearable=False,
                className="mb-3"
            ),
            html.Div(id='video-description', className="mb-3 text-muted"),
            html.Div([
                html.Video(
                    id='video-player',
                    controls=True,
                    style={'width': '100%', 'maxHeight': '500px'}
                )
            ], className="mb-4")
        ], width=12, lg=6),
        
        # Statistics Summary Cards
        dbc.Col([
            html.H3("Statistics Summary", className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Avg Ergonomic Score", className="card-title"),
                            html.H2(f"{df['ergonomic_score'].mean():.1f}", 
                                   className="text-primary"),
                            html.P("Last 30 days", className="text-muted")
                        ])
                    ], className="mb-3")
                ], width=12),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Total Incidents", className="card-title"),
                            html.H2(f"{int(df['posture_incidents'].sum())}", 
                                   className="text-danger"),
                            html.P("Last 30 days", className="text-muted")
                        ])
                    ], className="mb-3")
                ], width=12),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Avg Activity", className="card-title"),
                            html.H2(f"{df['activity_level'].mean():.1f}%", 
                                   className="text-success"),
                            html.P("Last 30 days", className="text-muted")
                        ])
                    ], className="mb-3")
                ], width=12)
            ])
        ], width=12, lg=6)
    ], className="mb-4"),
    
    # Charts Section
    dbc.Row([
        dbc.Col([
            dcc.Graph(
                id='ergonomic-score-chart',
                figure=create_ergonomic_score_chart()
            )
        ], width=12, lg=6, className="mb-4"),
        
        dbc.Col([
            dcc.Graph(
                id='posture-incidents-chart',
                figure=create_posture_incidents_chart()
            )
        ], width=12, lg=6, className="mb-4")
    ]),
    
    dbc.Row([
        dbc.Col([
            dcc.Graph(
                id='activity-gauge',
                figure=create_activity_gauge()
            )
        ], width=12, lg=6, className="mb-4"),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Data Summary", className="card-title mb-3"),
                    html.Div([
                        html.Strong("Date Range: "),
                        f"{df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}"
                    ], className="mb-2"),
                    html.Div([
                        html.Strong("Total Records: "),
                        f"{len(df)}"
                    ], className="mb-2"),
                    html.Div([
                        html.Strong("Best Score: "),
                        f"{df['ergonomic_score'].max():.1f}",
                        html.Span(f" (on {df.loc[df['ergonomic_score'].idxmax(), 'date'].strftime('%Y-%m-%d')})", 
                                 className="text-muted")
                    ], className="mb-2"),
                    html.Div([
                        html.Strong("Lowest Incidents: "),
                        f"{int(df['posture_incidents'].min())}",
                        html.Span(f" (on {df.loc[df['posture_incidents'].idxmin(), 'date'].strftime('%Y-%m-%d')})", 
                                 className="text-muted")
                    ])
                ])
            ])
        ], width=12, lg=6, className="mb-4")
    ]),
    
    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(),
            html.P("Ergo-dash © 2025 - Ergonomic Assessment Dashboard", 
                   className="text-center text-muted")
        ])
    ])
], fluid=True, className="p-4")

# Callbacks
@callback(
    [Output('video-player', 'src'),
     Output('video-description', 'children')],
    [Input('video-selector', 'value')]
)
def update_video(selected_index):
    """Update video player source when selection changes."""
    if selected_index is not None and selected_index < len(SAMPLE_VIDEOS):
        video = SAMPLE_VIDEOS[selected_index]
        return video['url'], html.P([html.Strong("Description: "), video['description']])
    return "", ""

# Run the app
if __name__ == '__main__':
    print("\n" + "="*50)
    print("Ergo-dash Dashboard Starting...")
    print("="*50)
    print("Access the dashboard at: http://localhost:8050")
    print("Press Ctrl+C to stop the server")
    print("="*50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=8050)
