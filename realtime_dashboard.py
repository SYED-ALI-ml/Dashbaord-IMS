import sqlite3
import pandas as pd
import numpy as np
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import threading
import random

# Initialize the Dash app with nicer theme
app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.BOOTSTRAP, 
                                      'https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&display=swap',
                                      'https://use.fontawesome.com/releases/v5.15.4/css/all.css'],
                meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}],
                suppress_callback_exceptions=True)

# Initialize data
def get_connection():
    """Get a connection to the database"""
    return sqlite3.connect('realtime_inventory.db')

def load_products():
    """Load products data"""
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM Products", conn)
    conn.close()
    return df

def load_recent_movements(minutes=60):
    """Load recent inventory movements"""
    conn = get_connection()
    query = f"""
    SELECT m.movement_id, m.product_name, p.category, 
           m.timestamp, m.movement_type, m.quantity, p.instock_items
    FROM InventoryMovements m
    JOIN Products p ON m.product_name = p.product_name
    WHERE m.timestamp >= datetime('now', '-{minutes} minutes')
    ORDER BY m.timestamp DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    return df

def load_stock_levels():
    """Load current stock levels"""
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM Products", conn)
    conn.close()
    return df

# Function to get summary metrics
def get_summary_metrics(df):
    """Calculate summary metrics from movement data"""
    if df.empty:
        return {
            'total_movements': 0,
            'incoming_count': 0,
            'outgoing_count': 0,
            'incoming_items': 0,
            'outgoing_items': 0,
            'net_change': 0
        }
    
    incoming = df[df['movement_type'] == 'incoming']
    outgoing = df[df['movement_type'] == 'outgoing']
    
    return {
        'total_movements': len(df),
        'incoming_count': len(incoming),
        'outgoing_count': len(outgoing),
        'incoming_items': incoming['quantity'].sum() if not incoming.empty else 0,
        'outgoing_items': outgoing['quantity'].sum() if not outgoing.empty else 0,
        'net_change': (incoming['quantity'].sum() if not incoming.empty else 0) - 
                      (outgoing['quantity'].sum() if not outgoing.empty else 0)
    }

# Custom CSS for better styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Real-Time Inventory Movement Dashboard</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: 'Poppins', sans-serif;
                background-color: #f9f9f9;
            }
            .card {
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                margin-bottom: 20px;
                border: none;
                transition: transform 0.3s ease;
            }
            .card-header {
                background-color: #fff;
                border-bottom: 1px solid #eaeaea;
                font-weight: 600;
                padding: 15px 20px;
                border-radius: 10px 10px 0 0 !important;
            }
            .container-fluid {
                padding: 30px;
            }
            .kpi-card {
                text-align: center;
                padding: 20px;
            }
            .kpi-value {
                font-size: 2rem;
                font-weight: 600;
            }
            .kpi-title {
                font-size: 1rem;
                color: #555;
                margin-top: 5px;
            }
            .positive {
                color: #2e8540;
            }
            .negative {
                color: #d83933;
            }
            .neutral {
                color: #4361ee;
            }
            .dashboard-title {
                background: linear-gradient(90deg, #00b4d8, #0077b6);
                color: white;
                padding: 15px 30px;
                border-radius: 10px;
                margin-bottom: 25px;
                box-shadow: 0 4px 15px rgba(0, 179, 216, 0.3);
            }
            .status-indicator {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
            }
            .status-active {
                background-color: #4cc9f0;
                animation: pulse 1.5s infinite;
            }
            @keyframes pulse {
                0% {
                    transform: scale(0.95);
                    box-shadow: 0 0 0 0 rgba(76, 201, 240, 0.7);
                }
                70% {
                    transform: scale(1);
                    box-shadow: 0 0 0 6px rgba(76, 201, 240, 0);
                }
                100% {
                    transform: scale(0.95);
                    box-shadow: 0 0 0 0 rgba(76, 201, 240, 0);
                }
            }
            .help-text {
                font-size: 0.9rem;
                color: #666;
            }
            .time-filter-card {
                border-left: 5px solid #4361ee;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Define the dashboard layout
app.layout = dbc.Container([
    # Dashboard Header with Logo and Title
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1([
                    html.I(className="fas fa-exchange-alt mr-2", style={"marginRight": "15px"}),
                    "Real-Time Inventory Movement Dashboard"
                ], className="mb-0"),
                html.P([
                    html.Span([
                        html.Span(className="status-indicator status-active"),
                        "LIVE"
                    ], style={"fontWeight": "bold"}),
                    " Tracking inventory inflows and outflows in real-time"
                ], className="text-white mb-0 mt-2")
            ], className="dashboard-title")
        ], width=12)
    ]),
    
    # Time filter card
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        html.I(className="fas fa-clock mr-2", style={"marginRight": "10px"}),
                        "Time Window"
                    ]),
                ]),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.P("Select the time window for displayed data:", className="mb-2"),
                            dcc.RadioItems(
                                id='time-window',
                                options=[
                                    {'label': 'Last 15 minutes', 'value': 15},
                                    {'label': 'Last 30 minutes', 'value': 30},
                                    {'label': 'Last hour', 'value': 60},
                                    {'label': 'Last 3 hours', 'value': 180},
                                    {'label': 'All day', 'value': 1440}
                                ],
                                value=30,
                                labelStyle={'display': 'inline-block', 'marginRight': '15px'},
                                className="mb-0"
                            ),
                        ], width=10),
                        dbc.Col([
                            dbc.Button(
                                html.I(className="fas fa-sync-alt"),
                                id="refresh-data",
                                color="primary",
                                className="float-right"
                            )
                        ], width=2)
                    ])
                ])
            ], className="mb-4 time-filter-card")
        ], width=12)
    ]),
    
    # KPI Cards
    dbc.Row([
        dbc.Col([
            dbc.Card([
                html.Div([
                    html.I(className="fas fa-arrow-circle-right fa-2x mb-3", style={"color": "#2e8540"}),
                    html.Div(id="incoming-value", className="kpi-value positive"),
                    html.Div("Incoming Items", className="kpi-title")
                ], className="kpi-card")
            ])
        ], md=3, sm=6),
        
        dbc.Col([
            dbc.Card([
                html.Div([
                    html.I(className="fas fa-arrow-circle-left fa-2x mb-3", style={"color": "#d83933"}),
                    html.Div(id="outgoing-value", className="kpi-value negative"),
                    html.Div("Outgoing Items", className="kpi-title")
                ], className="kpi-card")
            ])
        ], md=3, sm=6),
        
        dbc.Col([
            dbc.Card([
                html.Div([
                    html.I(className="fas fa-balance-scale fa-2x mb-3", style={"color": "#4361ee"}),
                    html.Div(id="net-change-value", className="kpi-value neutral"),
                    html.Div("Net Inventory Change", className="kpi-title")
                ], className="kpi-card")
            ])
        ], md=3, sm=6),
        
        dbc.Col([
            dbc.Card([
                html.Div([
                    html.I(className="fas fa-boxes fa-2x mb-3", style={"color": "#7209b7"}),
                    html.Div(id="total-movements", className="kpi-value"),
                    html.Div("Total Movements", className="kpi-title")
                ], className="kpi-card")
            ])
        ], md=3, sm=6)
    ], className="mb-4"),
    
    # Main charts section
    dbc.Row([
        # Left column - Movement timeline and Category distribution
        dbc.Col([
            # Movement timeline
            dbc.Card([
                dbc.CardHeader([
                    html.H5("Real-Time Movement Timeline"),
                    html.Small("Incoming and outgoing inventory over time", className="text-muted")
                ]),
                dbc.CardBody([
                    dcc.Graph(id="movement-timeline", style={"height": "350px"})
                ])
            ], className="mb-4"),
            
            # Category breakdown
            dbc.Card([
                dbc.CardHeader([
                    html.H5("Movement by Category"),
                    html.Small("Distribution of inventory movements by product category", className="text-muted")
                ]),
                dbc.CardBody([
                    dcc.Graph(id="category-breakdown", style={"height": "350px"})
                ])
            ])
        ], md=8),
        
        # Right column - Current stock and Recent Activity
        dbc.Col([
            # Current stock levels
            dbc.Card([
                dbc.CardHeader([
                    html.H5("Current Stock Levels"),
                    html.Small("Live inventory by product", className="text-muted")
                ]),
                dbc.CardBody([
                    dcc.Graph(id="stock-levels", style={"height": "350px"})
                ])
            ], className="mb-4"),
            
            # Recent activity
            dbc.Card([
                dbc.CardHeader([
                    html.H5("Recent Movements"),
                    html.Small("Latest inventory transactions", className="text-muted")
                ]),
                dbc.CardBody([
                    dash_table.DataTable(
                        id="recent-movements-table",
                        columns=[
                            {"name": "Time", "id": "time"},
                            {"name": "Product", "id": "product"},
                            {"name": "Type", "id": "type"},
                            {"name": "Quantity", "id": "quantity"}
                        ],
                        style_cell={
                            'textAlign': 'left',
                            'padding': '12px 15px',
                            'fontFamily': '"Poppins", sans-serif'
                        },
                        style_header={
                            'backgroundColor': '#f8f9fa',
                            'fontWeight': 'bold',
                            'border': '1px solid #e9ecef'
                        },
                        style_data_conditional=[
                            {
                                'if': {'row_index': 'odd'},
                                'backgroundColor': '#f9f9f9'
                            },
                            {
                                'if': {
                                    'filter_query': '{type} = "incoming"'
                                },
                                'color': '#2e8540'
                            },
                            {
                                'if': {
                                    'filter_query': '{type} = "outgoing"'
                                },
                                'color': '#d83933'
                            }
                        ],
                        page_size=5
                    )
                ])
            ])
        ], md=4)
    ]),
    
    # Hidden div for storing the data
    html.Div(id='movements-data', style={'display': 'none'}),
    html.Div(id='products-data', style={'display': 'none'}),
    
    # Interval component for updates
    dcc.Interval(
        id='interval-component',
        interval=5000,  # in milliseconds (5 seconds)
        n_intervals=0
    )
], fluid=True)

# Callback to update the data stores
@app.callback(
    [Output('movements-data', 'children'),
     Output('products-data', 'children')],
    [Input('interval-component', 'n_intervals'),
     Input('refresh-data', 'n_clicks'),
     Input('time-window', 'value')]
)
def update_data_stores(n_intervals, n_clicks, time_window):
    # Load the data
    movements_df = load_recent_movements(time_window)
    products_df = load_stock_levels()
    
    # Convert to JSON for storage
    movements_json = movements_df.to_json(date_format='iso', orient='split')
    products_json = products_df.to_json(orient='split')
    
    return movements_json, products_json

# Callback to update KPI values
@app.callback(
    [Output('incoming-value', 'children'),
     Output('outgoing-value', 'children'),
     Output('net-change-value', 'children'),
     Output('net-change-value', 'className'),
     Output('total-movements', 'children')],
    [Input('movements-data', 'children')]
)
def update_kpi_values(movements_json):
    # Parse the data
    if not movements_json:
        return "0", "0", "0", "kpi-value neutral", "0"
    
    movements_df = pd.read_json(movements_json, orient='split')
    metrics = get_summary_metrics(movements_df)
    
    # Format the values
    incoming = f"{metrics['incoming_items']:,}"
    outgoing = f"{metrics['outgoing_items']:,}"
    net_change = metrics['net_change']
    
    # Format net change with sign and determine class
    if net_change > 0:
        net_change_formatted = f"+{net_change:,}"
        net_change_class = "kpi-value positive"
    elif net_change < 0:
        net_change_formatted = f"{net_change:,}"
        net_change_class = "kpi-value negative"
    else:
        net_change_formatted = "0"
        net_change_class = "kpi-value neutral"
    
    total_movements = f"{metrics['total_movements']:,}"
    
    return incoming, outgoing, net_change_formatted, net_change_class, total_movements

# Callback to update movement timeline
@app.callback(
    Output('movement-timeline', 'figure'),
    [Input('movements-data', 'children')]
)
def update_movement_timeline(movements_json):
    if not movements_json:
        # Return empty figure
        return go.Figure().update_layout(
            title="No data available",
            xaxis=dict(title="Time"),
            yaxis=dict(title="Quantity"),
            template="plotly_white"
        )
    
    # Parse the data
    movements_df = pd.read_json(movements_json, orient='split')
    
    if movements_df.empty:
        # Return empty figure
        return go.Figure().update_layout(
            title="No data available in selected time window",
            xaxis=dict(title="Time"),
            yaxis=dict(title="Quantity"),
            template="plotly_white"
        )
    
    # Ensure timestamp is properly formatted
    movements_df['timestamp'] = pd.to_datetime(movements_df['timestamp'])
    
    # Sort by timestamp
    movements_df = movements_df.sort_values('timestamp')
    
    # Prepare data for outgoing (negative values)
    outgoing_df = movements_df[movements_df['movement_type'] == 'outgoing'].copy()
    outgoing_df['quantity'] = -outgoing_df['quantity']  # Make negative for visualization
    
    # Create the figure
    fig = go.Figure()
    
    # Add incoming movements
    fig.add_trace(go.Bar(
        x=movements_df[movements_df['movement_type'] == 'incoming']['timestamp'],
        y=movements_df[movements_df['movement_type'] == 'incoming']['quantity'],
        name='Incoming',
        marker_color='#2e8540',
        hovertemplate='<b>%{x}</b><br>Incoming: %{y}<extra></extra>'
    ))
    
    # Add outgoing movements
    fig.add_trace(go.Bar(
        x=outgoing_df['timestamp'],
        y=outgoing_df['quantity'],
        name='Outgoing',
        marker_color='#d83933',
        hovertemplate='<b>%{x}</b><br>Outgoing: %{y}<extra></extra>'
    ))
    
    # Update layout
    fig.update_layout(
        barmode='relative',
        title="Inventory Movement Timeline",
        xaxis=dict(title="Time"),
        yaxis=dict(title="Quantity"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=40, r=40, t=80, b=40),
        template="plotly_white"
    )
    
    return fig

# Callback to update category breakdown
@app.callback(
    Output('category-breakdown', 'figure'),
    [Input('movements-data', 'children')]
)
def update_category_breakdown(movements_json):
    if not movements_json:
        # Return empty figure
        return go.Figure().update_layout(
            title="No data available",
            template="plotly_white"
        )
    
    # Parse the data
    movements_df = pd.read_json(movements_json, orient='split')
    
    if movements_df.empty:
        # Return empty figure
        return go.Figure().update_layout(
            title="No data available in selected time window",
            template="plotly_white"
        )
    
    # Aggregate by category and movement type
    category_data = movements_df.groupby(['category', 'movement_type'])['quantity'].sum().reset_index()
    
    # Create the figure
    fig = px.bar(
        category_data,
        x='category',
        y='quantity',
        color='movement_type',
        barmode='group',
        color_discrete_map={'incoming': '#2e8540', 'outgoing': '#d83933'},
        labels={'quantity': 'Total Quantity', 'category': 'Category', 'movement_type': 'Movement Type'}
    )
    
    # Update layout
    fig.update_layout(
        title="Movement Volume by Category",
        xaxis=dict(title="Category"),
        yaxis=dict(title="Total Quantity"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=40, r=40, t=80, b=40),
        template="plotly_white"
    )
    
    return fig

# Callback to update stock levels
@app.callback(
    Output('stock-levels', 'figure'),
    [Input('products-data', 'children')]
)
def update_stock_levels(products_json):
    if not products_json:
        # Return empty figure
        return go.Figure().update_layout(
            title="No data available",
            template="plotly_white"
        )
    
    # Parse the data
    products_df = pd.read_json(products_json, orient='split')
    
    if products_df.empty:
        # Return empty figure
        return go.Figure().update_layout(
            title="No stock data available",
            template="plotly_white"
        )
    
    # Create the figure
    fig = px.bar(
        products_df,
        x='product_name',
        y='instock_items',
        color='category',
        labels={'instock_items': 'Current Stock', 'product_name': 'Product', 'category': 'Category'},
        template="plotly_white"
    )
    
    # Update layout
    fig.update_layout(
        title="Current Stock Levels by Product",
        xaxis=dict(title="Product", tickangle=-45),
        yaxis=dict(title="Current Stock"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=80, b=120),
        height=350
    )
    
    return fig

# Callback to update recent movements table
@app.callback(
    Output('recent-movements-table', 'data'),
    [Input('movements-data', 'children')]
)
def update_recent_movements_table(movements_json):
    if not movements_json:
        return []
    
    # Parse the data
    movements_df = pd.read_json(movements_json, orient='split')
    
    if movements_df.empty:
        return []
    
    # Format the data for the table
    movements_df['time'] = movements_df['timestamp'].dt.strftime('%H:%M:%S')
    
    # Get the 10 most recent movements
    recent = movements_df.sort_values('timestamp', ascending=False).head(10)
    
    # Format the table data
    table_data = []
    for _, row in recent.iterrows():
        table_data.append({
            'time': row['time'],
            'product': row['product_name'],
            'type': row['movement_type'],
            'quantity': row['quantity']
        })
    
    return table_data

if __name__ == '__main__':
    app.run(debug=True, port=8050) 