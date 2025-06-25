import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, html, dcc, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
import calendar
import io
import base64

# Add these imports for Gemini
import google.generativeai as genai
from dash.exceptions import PreventUpdate
import json
import os

# Add these imports for caching
import functools
import time
import traceback  # Add for better error tracking

# Update the Gemini configuration to use the config file
from config import GEMINI_API_KEY, DATABASE_PATH

# Set up Google API key from config
api_key = "AIzaSyBo00GRHkn3OZrp8ESCGgr0rYhRUcIw0ro"
genai.configure(api_key=api_key)

# Simple response cache
response_cache = {}

# Initialize Gemini model with optimized settings
gemini_model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config={
        "temperature": 0.2,
        "top_p": 0.95,
        "max_output_tokens": 1024,
    },
    safety_settings=[
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ],
)

# Connect to the database using the config path
conn = sqlite3.connect(DATABASE_PATH)

# Load the data
products_df = pd.read_sql("SELECT * FROM Products", conn)
inventory_df = pd.read_sql("SELECT * FROM Inventory", conn)

# Convert timestamp to datetime
inventory_df['date'] = pd.to_datetime(inventory_df['date'])

# Merge data for analysis
df = pd.merge(inventory_df, products_df, on='product_name')

# Add time-based columns
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month
df['month_name'] = df['date'].dt.month.apply(lambda x: calendar.month_name[x])
df['month_year'] = df['date'].dt.strftime('%Y-%m')
df['quarter'] = df['date'].dt.quarter
df['season'] = df['date'].dt.month.apply(lambda x: 
                                      'Spring' if x in [3, 4, 5] else
                                      'Summer' if x in [6, 7, 8] else
                                      'Fall' if x in [9, 10, 11] else
                                      'Winter')
df['day_of_week'] = df['date'].dt.day_name()
df['week_number'] = df['date'].dt.isocalendar().week

# Calculate variance as the difference between final and initial counts
df['variance'] = df['final_count'] - df['initial_count']

# Calculate product metrics
product_summary = df.groupby(['product_name', 'category']).agg({
    'id': 'count',
    'initial_count': ['mean', 'std'],
    'final_count': ['mean', 'std'],
    'variance': ['sum', 'mean']
}).reset_index()
product_summary.columns = ['product_name', 'category', 'days_tracked', 'avg_initial', 'std_initial', 
                           'avg_final', 'std_final', 'total_change', 'avg_change']

# Round decimal values for better display
for col in ['avg_initial', 'std_initial', 'avg_final', 'std_final', 'avg_change']:
    product_summary[col] = product_summary[col].round(2)

# Calculate overall metrics
total_days = df['date'].nunique()
avg_daily_change = df.groupby('date')['variance'].sum().mean().round(2)
total_net_change = df['variance'].sum()

# Calculate current inventory based on the latest date's final counts
latest_date = df['date'].max()
current_inventory = df[df['date'] == latest_date].groupby('product_name')['final_count'].sum()
previous_date = latest_date - timedelta(days=1)
previous_inventory = df[df['date'] == previous_date].groupby('product_name')['final_count'].sum()
inventory_change = ((current_inventory.sum() - previous_inventory.sum()) / previous_inventory.sum() * 100).round(2) if previous_inventory.sum() != 0 else 0
total_instock = products_df['instock_items'].sum()

# Create a color map for categories
categories = sorted(df['category'].unique())
category_colors = px.colors.qualitative.Bold[:len(categories)]
category_color_map = dict(zip(categories, category_colors))

# Create a color map for products within each category
product_names = df['product_name'].unique()
product_colors = {}
for cat in categories:
    cat_products = df[df['category'] == cat]['product_name'].unique()
    cat_colors = px.colors.sequential.Plasma[:len(cat_products)]
    for prod, color in zip(cat_products, cat_colors):
        product_colors[prod] = color

# Initialize the Dash app with nicer theme
app = Dash(__name__, 
           external_stylesheets=[dbc.themes.BOOTSTRAP, 
                               'https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&display=swap',
                               'https://use.fontawesome.com/releases/v5.15.4/css/all.css'],
           meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}],
           suppress_callback_exceptions=True)  # Add this parameter

# Custom CSS for better styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Art & Decor Analytics</title>
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
            .card:hover {
                transform: translateY(-5px);
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
                color: #4361ee;
            }
            .kpi-title {
                font-size: 1rem;
                color: #555;
                margin-top: 5px;
            }
            .filter-section {
                background-color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                margin-bottom: 20px;
            }
            .navbar-brand {
                font-size: 1.5rem;
                font-weight: 600;
            }
            .info-icon {
                cursor: help;
                color: #4361ee;
                margin-left: 5px;
            }
            .tab-content {
                padding-top: 20px;
            }
            .dash-table-container {
                border-radius: 10px;
                overflow: hidden;
            }
            .help-text {
                font-size: 0.9rem;
                color: #666;
                font-style: italic;
                margin-top: 5px;
            }
            .dashboard-title {
                background: linear-gradient(90deg, #4361ee, #3f37c9);
                color: white;
                padding: 15px 30px;
                border-radius: 10px;
                margin-bottom: 25px;
                box-shadow: 0 4px 15px rgba(67, 97, 238, 0.3);
            }
            .filter-card {
                border-left: 5px solid #4361ee;
            }
            .product-metric-card {
                text-align: center;
                padding: 15px;
                margin-bottom: 15px;
                border-radius: 10px;
                background-color: #f8f9fa;
                border-left: 4px solid #4361ee;
                transition: all 0.3s ease;
            }
            .product-metric-card:hover {
                background-color: #e9ecef;
                transform: translateY(-5px);
            }
            .metric-title {
                font-size: 0.9rem;
                color: #555;
                margin-bottom: 5px;
            }
            .metric-value {
                font-size: 1.8rem;
                font-weight: 600;
                color: #3a0ca3;
            }
            .metric-subtext {
                font-size: 0.8rem;
                color: #6c757d;
            }
            .custom-tab {
                padding: 12px 15px;
                font-weight: 500;
            }
            .chat-toggle-btn {
                position: fixed;
                bottom: 20px;
                right: 20px;
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: #4361ee;
                color: white;
                border: none;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
                cursor: pointer;
                z-index: 1000;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
            }

            .chat-toggle-btn:hover {
                transform: scale(1.1);
                background: #3a0ca3;
            }

            .chat-panel {
                position: fixed;
                bottom: 20px;
                right: 20px;
                width: 350px;
                height: 500px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
                z-index: 1001;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                transition: all 0.3s ease;
                transform: translateY(600px);
                opacity: 0;
            }

            .chat-panel.open {
                transform: translateY(0);
                opacity: 1;
            }

            .chat-header {
                background: #4361ee;
                color: white;
                padding: 15px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .close-btn {
                background: transparent;
                border: none;
                color: white;
                cursor: pointer;
            }

            .chat-messages {
                flex: 1;
                padding: 15px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }

            .message {
                max-width: 80%;
                padding: 10px 15px;
                border-radius: 18px;
                word-break: break-word;
                line-height: 1.4;
            }

            .user-message {
                background: #e9ecef;
                align-self: flex-end;
                border-bottom-right-radius: 5px;
            }

            .ai-message {
                background: #4361ee;
                color: white;
                align-self: flex-start;
                border-bottom-left-radius: 5px;
            }

            .chat-input-container {
                display: flex;
                border-top: 1px solid #eaeaea;
                padding: 10px;
            }

            .chat-input {
                flex: 1;
                padding: 12px 15px;
                border: 1px solid #eaeaea;
                border-radius: 30px;
                outline: none;
            }

            .send-btn {
                background: #4361ee;
                color: white;
                border: none;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                margin-left: 10px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .code-block {
                background: #f8f9fa;
                border-radius: 5px;
                padding: 10px;
                margin: 5px 0;
                font-family: monospace;
                overflow-x: auto;
                max-width: 100%;
            }

            .chart-message {
                width: 100%;
                margin: 5px 0;
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

# Define the dashboard layout with improved UI
app.layout = dbc.Container([
    # Dashboard Header with Logo and Title
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1([
                    html.I(className="fas fa-chart-line mr-2", style={"marginRight": "15px"}),
                    "Art & Decor Inventory Analytics Dashboard"
                ], className="mb-0"),
                html.P("Interactive insights for art and decor inventory management", className="text-white mb-0 mt-2")
            ], className="dashboard-title")
        ], width=12)
    ]),
    
    # Introduction Alert
    dbc.Row([
        dbc.Col([
            dbc.Alert([
                html.H5("Welcome to your Art & Decor Analytics Dashboard", className="alert-heading"),
                html.P([
                    "This dashboard provides interactive insights into your inventory performance. ",
                    html.Strong("Use the filters below to explore your data"), 
                    " and hover over the info icons ", 
                    html.I(className="fas fa-info-circle"), 
                    " for additional help."
                ]),
                html.Hr(),
                html.P("Click on chart elements to filter and interact with the data.", className="mb-0")
            ], color="info", dismissable=True, is_open=True, className="mb-4")
        ], width=12)
    ]),
    
    # KPI Cards
    dbc.Row([
        dbc.Col([
            dbc.Card([
                html.Div([
                    html.I(className="fas fa-boxes fa-2x mb-3", style={"color": "#4361ee"}),
                    html.Div(f"{len(products_df)}", className="kpi-value"),
                    html.Div("Total Products", className="kpi-title")
                ], className="kpi-card")
            ])
        ], width=12, lg=3, className="mb-4"),
        
        dbc.Col([
            dbc.Card([
                html.Div([
                    html.I(className="fas fa-exchange-alt fa-2x mb-3", style={"color": "#3a0ca3"}),
                    html.Div(f"{total_days:,}", className="kpi-value"),
                    html.Div("Total Days Tracked", className="kpi-title")
                ], className="kpi-card")
            ])
        ], width=12, lg=3, className="mb-4"),
        
        dbc.Col([
            dbc.Card([
                html.Div([
                    html.I(className="fas fa-layer-group fa-2x mb-3", style={"color": "#7209b7"}),
                    html.Div(f"{avg_daily_change:.2f}", className="kpi-value"),
                    html.Div("Average Daily Change", className="kpi-title")
                ], className="kpi-card")
            ])
        ], width=12, lg=3, className="mb-4"),
        
        dbc.Col([
            dbc.Card([
                html.Div([
                    html.I(className="fas fa-cubes fa-2x mb-3", style={"color": "#48bfe3"}),
                    html.Div(f"{total_instock:,}", className="kpi-value"),
                    html.Div("Total In-Stock Items", className="kpi-title")
                ], className="kpi-card")
            ])
        ], width=12, lg=3, className="mb-4")
    ]),
    
    # Filter Section with better UI
    dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="fas fa-filter mr-2", style={"marginRight": "10px"}),
                "Interactive Filters"
            ]),
        ]),
        dbc.CardBody([
            dbc.Row([
                # Product filters with dropdown menu
                dbc.Col([
                    html.H6([
                        "Filter by Product",
                        html.I(className="fas fa-info-circle ml-2 info-icon", 
                               id="product-filter-info", style={"marginLeft": "5px"})
                    ]),
                    dbc.Tooltip(
                        "Select one or more products to focus your analysis.",
                        target="product-filter-info"
                    ),
                    dcc.Dropdown(
                        id='product-filter',
                        options=[
                            {'label': name, 'value': name} 
                            for name in products_df['product_name']
                        ],
                        value=products_df['product_name'].tolist(),
                        multi=True,
                        placeholder="Select products...",
                        className="pt-2"
                    )
                ], width=12, lg=6, className="mb-3"),
                
                # Date filters with dropdown menus
                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            html.H6([
                                "Time Range",
                                html.I(className="fas fa-info-circle ml-2 info-icon", 
                                       id="time-range-info", style={"marginLeft": "5px"})
                            ]),
                            dbc.Tooltip(
                                "Filter data by specific time periods",
                                target="time-range-info"
                            ),
                            dcc.Dropdown(
                                id='year-filter',
                                options=[
                                    {'label': 'All Years (2022-2023)', 'value': 'all'},
                                    {'label': '2022', 'value': 2022},
                                    {'label': '2023', 'value': 2023}
                                ],
                                value='all',
                                clearable=False,
                                className="pt-2"
                            )
                        ], width=12, sm=6),
                        
                        dbc.Col([
                            html.H6([
                                "View By",
                                html.I(className="fas fa-info-circle ml-2 info-icon", 
                                       id="time-period-info", style={"marginLeft": "5px"})
                            ]),
                            dbc.Tooltip(
                                "Change how data is grouped in visualizations",
                                target="time-period-info"
                            ),
                            dcc.Dropdown(
                                id='time-period',
                                options=[
                                    {'label': 'Monthly View', 'value': 'month'},
                                    {'label': 'Quarterly View', 'value': 'quarter'},
                                    {'label': 'Seasonal View', 'value': 'season'}
                                ],
                                value='month',
                                clearable=False,
                                className="pt-2"
                            )
                        ], width=12, sm=6),
                        
                        html.Div(className="mt-3"),
                        
                        # Category filter
                        dbc.Row([
                            dbc.Col([
                                html.H6([
                                    "Filter by Category",
                                    html.I(className="fas fa-info-circle ml-2 info-icon", 
                                           id="category-filter-info", style={"marginLeft": "5px"})
                                ]),
                                dbc.Tooltip(
                                    "Filter products by their category",
                                    target="category-filter-info"
                                ),
                                dcc.Dropdown(
                                    id='category-filter',
                                    options=[
                                        {'label': 'All Categories', 'value': 'all'},
                                    ] + [
                                        {'label': cat, 'value': cat} for cat in sorted(df['category'].unique())
                                    ],
                                    value='all',
                                    clearable=False,
                                    className="pt-2"
                                )
                            ], width=12)
                        ])
                    ])
                ], width=12, lg=6)
            ])
        ])
    ], className="mb-4 filter-card"),
    
    # Main Dashboard Tabs for better organization
    dbc.Card([
        dbc.CardHeader(
            dbc.Tabs([
                dbc.Tab(label="Overview", tab_id="tab-overview", activeTabClassName="fw-bold", labelClassName="custom-tab"),
                dbc.Tab(label="Time Analysis", tab_id="tab-time", activeTabClassName="fw-bold", labelClassName="custom-tab"),
                dbc.Tab(label="Product Details", tab_id="tab-products", activeTabClassName="fw-bold", labelClassName="custom-tab"),
                dbc.Tab(label="Data Table", tab_id="tab-data", activeTabClassName="fw-bold", labelClassName="custom-tab"),
            ], id="dashboard-tabs", active_tab="tab-overview")
        ),
        dbc.CardBody([
            html.Div(id="tab-content")
        ])
    ]),
    
    # Footer with helpful links and information
    html.Footer([
        html.Hr(),
        html.P([
            "© 2023 Art & Decor Analytics Dashboard | ",
            html.A("How to Use This Dashboard", href="#", className="text-primary", id="help-link"),
            " | ",
            html.A("Export Data", href="#", className="text-primary", id="export-link"),
            " | ",
            html.A("Print Report", href="#", className="text-primary", id="print-link")
        ], className="text-center mt-4 text-muted")
    ]),
    
    # Help modal
    dbc.Modal([
        dbc.ModalHeader("Dashboard Help"),
        dbc.ModalBody([
            html.H5("How to Use This Dashboard"),
            html.Ul([
                html.Li("Use the filters at the top to select products and time periods"),
                html.Li("Click on chart elements to drill down into data"),
                html.Li("Switch between tabs to view different aspects of your inventory"),
                html.Li("Hover over charts for detailed information")
            ]),
            html.H5("Key Features:", className="mt-4"),
            html.Ul([
                html.Li([html.Strong("Overview Tab:"), " See high-level product performance and distribution"]),
                html.Li([html.Strong("Time Analysis Tab:"), " Track inventory trends over time"]),
                html.Li([html.Strong("Product Details Tab:"), " Analyze individual product performance"]),
                html.Li([html.Strong("Data Table Tab:"), " View and search the raw data"])
            ])
        ]),
        dbc.ModalFooter(
            dbc.Button("Close", id="close-help", className="ml-auto")
        ),
    ], id="help-modal"),
    
    # Hidden download component
    html.Div([
        dcc.Download(id="download-dataframe-csv"),
    ], style={"display": "none"}),

    # Chat interface components
    html.Div([
        # Chat toggle button - fixed at bottom right
        html.Button(
            html.I(className="fas fa-comment-dots", style={"fontSize": "24px"}),
            id="chat-toggle-button",
            className="chat-toggle-btn",
            n_clicks=0,
        ),
        
        # Chat panel (initially hidden)
        html.Div([
            html.Div([
                html.H5([
                    html.I(className="fas fa-robot mr-2", style={"marginRight": "10px"}),
                    "AI Analytics Assistant"
                ]),
                html.Button(
                    html.I(className="fas fa-times"),
                    id="close-chat",
                    className="close-btn",
                ),
            ], className="chat-header"),
            
            # Chat messages container
            html.Div(id="chat-messages", className="chat-messages"),
            
            # Chat input
            html.Div([
                dcc.Input(
                    id="chat-input",
                    type="text",
                    placeholder="Ask about your inventory data...",
                    className="chat-input",
                ),
                html.Button(
                    html.I(className="fas fa-paper-plane"),
                    id="send-button",
                    className="send-btn",
                ),
            ], className="chat-input-container"),
            
            # Loading indicator
            dbc.Spinner(html.Div(id="chat-loading"), color="primary", type="grow", size="sm"),
            
        ], id="chat-panel", className="chat-panel")
    ]),
    
    # Add a Store component to maintain chat history
    dcc.Store(id="chat-history", data={"messages": [
        {"sender": "ai", "text": "Hello! I'm your AI analytics assistant. Ask me anything about your inventory data."}
    ]}),
    
], fluid=True)

# Helper functions for creating charts and visualizations
def create_product_performance_chart(filtered_df):
    # Group data by product for the chart
    product_summary_df = filtered_df.groupby('product_name').agg({
        'initial_count': ['mean', 'std'],
        'final_count': ['mean', 'std'],
        'variance': ['sum', 'mean']
    }).reset_index()
    product_summary_df.columns = ['product_name', 'avg_initial', 'std_initial', 'avg_final', 'std_final', 'total_change', 'avg_change']
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add bars for avg initial and final counts
    fig.add_trace(
        go.Bar(
            x=product_summary_df['product_name'],
            y=product_summary_df['avg_initial'],
            name='Avg Initial Count',
            marker_color='#4361ee',
            hovertemplate='<b>%{x}</b><br>Avg Initial: %{y}<extra></extra>'
        ),
        secondary_y=False
    )
    fig.add_trace(
        go.Bar(
            x=product_summary_df['product_name'],
            y=product_summary_df['avg_final'],
            name='Avg Final Count',
            marker_color='#3a0ca3',
            hovertemplate='<b>%{x}</b><br>Avg Final: %{y}<extra></extra>'
        ),
        secondary_y=False
    )
    # Add line for average change
    fig.add_trace(
        go.Scatter(
            x=product_summary_df['product_name'],
            y=product_summary_df['avg_change'],
            name='Average Change',
            mode='markers',
            marker=dict(size=10, color='#f72585', symbol='circle'),
            line=dict(color='#f72585', width=2, dash='dot'),
            hovertemplate='<b>%{x}</b><br>Average Change: %{y:.2f}<extra></extra>'
        ),
        secondary_y=True
    )
    fig.update_layout(
        title_text="Product Performance Analysis",
        title_x=0.5,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        height=450,
        hovermode="x unified",
        margin=dict(l=40, r=40, t=80, b=40)
    )
    fig.update_xaxes(title_text="Product")
    fig.update_yaxes(title_text="Count", secondary_y=False)
    fig.update_yaxes(title_text="Change", secondary_y=True)
    return fig

def create_product_distribution_chart(filtered_df):
    # Group data by product and calculate total change (variance)
    product_totals = filtered_df.groupby('product_name').agg({
        'variance': 'sum'
    }).reset_index()
    fig = px.pie(
        product_totals, 
        values='variance', 
        names='product_name',
        color='product_name',
        color_discrete_map=product_colors,
        hole=0.4,
        labels={'variance': 'Total Change', 'product_name': 'Product'}
    )
    fig.update_traces(
        textposition='inside', 
        textinfo='percent+label',
        hoverinfo='label+percent+value',
        marker=dict(line=dict(color='#fff', width=2))
    )
    fig.update_layout(
        title_text="Product Distribution by Total Change",
        title_x=0.5,
        showlegend=False,
        height=450,
        margin=dict(l=20, r=20, t=80, b=20)
    )
    return fig

def create_value_analysis_chart(filtered_df):
    product_value = filtered_df.groupby('product_name').agg({
        'initial_count': 'mean',
        'final_count': 'mean',
        'variance': 'sum'
    }).reset_index()
    
    product_value['total_value'] = product_value['initial_count'] * product_value['initial_count']
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add bars for initial and final counts
    fig.add_trace(
        go.Bar(
            x=product_value['product_name'],
            y=product_value['initial_count'],
            name='Avg Initial Count',
            marker_color='#4361ee',
            hovertemplate='<b>%{x}</b><br>Avg Initial Count: %{y}<extra></extra>'
        ),
        secondary_y=False
    )
    
    fig.add_trace(
        go.Bar(
            x=product_value['product_name'],
            y=product_value['final_count'],
            name='Avg Final Count',
            marker_color='#3a0ca3',
            hovertemplate='<b>%{x}</b><br>Avg Final Count: %{y}<extra></extra>'
        ),
        secondary_y=False
    )
    
    # Add line for daily change
    fig.add_trace(
        go.Scatter(
            x=product_value['product_name'],
            y=product_value['variance'],
            name='Total Daily Change',
            mode='markers',
            marker=dict(size=12, color='#f72585', symbol='diamond'),
            hovertemplate='<b>%{x}</b><br>Total Daily Change: %{y:.2f}<extra></extra>'
        ),
        secondary_y=True
    )
    
    # Update layout
    fig.update_layout(
        title_text="Product Value Analysis",
        title_x=0.5,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        height=400,
        hovermode="x unified",
        margin=dict(l=40, r=40, t=80, b=40)
    )
    
    # Update axes
    fig.update_xaxes(title_text="Product")
    fig.update_yaxes(title_text="Count", secondary_y=False)
    fig.update_yaxes(title_text="Daily Change", secondary_y=True)
    
    return fig

def create_time_series_chart(df, time_period='month'):
    """Create a time series chart showing inventory trends"""
    if time_period == 'month':
        group_col = 'month_year'
        title = 'Monthly Inventory Trends'
    elif time_period == 'quarter':
        group_col = 'quarter'
        title = 'Quarterly Inventory Trends'
    else:  # year
        group_col = 'year'
        title = 'Yearly Inventory Trends'
    
    # Group data by time period and product
    time_series = df.groupby([group_col, 'product_name'])['final_count'].mean().reset_index()
    
    # Create the figure
    fig = px.line(time_series, 
                  x=group_col, 
                  y='final_count',
                  color='product_name',
                  title=title,
                  labels={'final_count': 'Final Count', group_col: 'Time Period'},
                  markers=True)
    
    # Update layout
    fig.update_layout(
        xaxis_title='Time Period',
        yaxis_title='Final Count',
        hovermode='x unified',
        showlegend=True,
        legend_title='Products',
        template='plotly_white'
    )
    
    # Update traces
    fig.update_traces(
        mode='lines+markers',
        marker=dict(size=8),
        line=dict(width=2)
    )
    
    return fig

def create_seasonal_chart(filtered_df):
    # Group by season for the chart
    season_data = filtered_df.groupby(['season', 'product_name'])['initial_count'].sum().reset_index()
    
    # Ensure seasons are in correct order
    season_order = ['Winter', 'Spring', 'Summer', 'Fall']
    season_data['season'] = pd.Categorical(season_data['season'], categories=season_order, ordered=True)
    season_data = season_data.sort_values('season')
    
    # Create the chart
    fig = px.bar(
        season_data, 
        x='season', 
        y='initial_count', 
        color='product_name',
        color_discrete_map=product_colors,
        barmode='group',
        labels={'initial_count': 'Total Initial Count', 'season': 'Season', 'product_name': 'Product'}
    )
    
    fig.update_layout(
        title_text="Seasonal Product Distribution",
        title_x=0.5,
        xaxis_title="Season",
        yaxis_title="Total Initial Count",
        legend_title="Product",
        height=450,
        margin=dict(l=40, r=40, t=80, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def create_growth_chart(filtered_df):
    # Calculate month-over-month growth
    monthly_data = filtered_df.groupby('month_year')['initial_count'].sum().reset_index()
    monthly_data['month_year'] = pd.to_datetime(monthly_data['month_year'])
    monthly_data = monthly_data.sort_values('month_year')
    
    # Calculate percentage change
    monthly_data['previous'] = monthly_data['initial_count'].shift(1)
    monthly_data['pct_change'] = ((monthly_data['initial_count'] - monthly_data['previous']) / monthly_data['previous'] * 100).round(1)
    monthly_data = monthly_data.dropna()
    monthly_data['formatted_date'] = monthly_data['month_year'].dt.strftime('%b %Y')
    
    # Create colors based on growth direction
    colors = ['#4cc9f0' if x >= 0 else '#f72585' for x in monthly_data['pct_change']]
    
    # Create the chart
    fig = go.Figure()
    
    fig.add_trace(
        go.Bar(
            x=monthly_data['formatted_date'],
            y=monthly_data['pct_change'],
            marker_color=colors,
            text=monthly_data['pct_change'].apply(lambda x: f"{x}%"),
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Growth: %{y:.1f}%<extra></extra>'
        )
    )
    
    fig.update_layout(
        title_text="Month-over-Month Inventory Growth",
        title_x=0.5,
        xaxis_title="Month",
        yaxis_title="% Change",
        height=450,
        margin=dict(l=40, r=40, t=80, b=60),
        xaxis=dict(tickangle=-45),
        yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='#ddd')
    )
    
    # Add a horizontal line at y=0
    fig.add_shape(
        type="line",
        x0=0,
        x1=1,
        xref="paper",
        y0=0,
        y1=0,
        line=dict(color="#999", width=2, dash="dot")
    )
    
    return fig

def create_product_metrics_cards(filtered_df):
    # Calculate metrics by product
    product_metrics = filtered_df.groupby('product_name').agg({
        'initial_count': ['mean'],
        'final_count': ['mean'],
        'variance': ['sum', 'mean']
    }).reset_index()
    product_metrics.columns = ['product_name', 'avg_initial', 'avg_final', 'total_change', 'avg_change']
    # Get latest instock items for each product from products_df
    instock_items = products_df[['product_name', 'instock_items']].set_index('product_name').to_dict()['instock_items']
    cards = []
    for _, product in product_metrics.iterrows():
        product_name = product['product_name']
        current_stock = instock_items.get(product_name, 0)
        card = dbc.Card([
            dbc.CardHeader(html.H5(product_name, className="text-center")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-cubes mb-2", style={"color": "#48bfe3", "fontSize": "24px"}),
                            html.Div(f"{current_stock:,}", className="metric-value"),
                            html.Div("Current In-Stock", className="metric-title")
                        ], className="product-metric-card")
                    ], width=12, sm=6, md=4),
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-bars mb-2", style={"color": "#4361ee", "fontSize": "24px"}),
                            html.Div(f"{product['avg_initial']:.2f}", className="metric-value"),
                            html.Div("Avg Initial Count", className="metric-title")
                        ], className="product-metric-card")
                    ], width=12, sm=6, md=4),
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-bars mb-2", style={"color": "#3a0ca3", "fontSize": "24px"}),
                            html.Div(f"{product['avg_final']:.2f}", className="metric-value"),
                            html.Div("Avg Final Count", className="metric-title")
                        ], className="product-metric-card")
                    ], width=12, sm=6, md=4),
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-chart-line mb-2", style={"color": "#f72585", "fontSize": "24px"}),
                            html.Div(f"{product['avg_change']:.2f}", className="metric-value"),
                            html.Div("Average Change", className="metric-title")
                        ], className="product-metric-card")
                    ], width=12, sm=6, md=4),
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-chart-line mb-2", style={"color": "#f72585", "fontSize": "24px"}),
                            html.Div(f"{product['total_change']:.2f}", className="metric-value"),
                            html.Div("Total Change", className="metric-title")
                        ], className="product-metric-card")
                    ], width=12, sm=6, md=4)
                ])
            ])
        ], className="mb-4")
        cards.append(card)
    return cards

def create_transaction_size_chart(filtered_df):
    fig = px.box(
        filtered_df, 
        x='product_name', 
        y='initial_count',
        color='product_name',
        color_discrete_map=product_colors,
        points="all",
        labels={'initial_count': 'Initial Count', 'product_name': 'Product'}
    )
    
    fig.update_traces(
        boxmean=True,
        jitter=0.3,
        pointpos=-1.8,
        marker=dict(size=5, opacity=0.6)
    )
    
    fig.update_layout(
        title_text="Transaction Size Distribution by Product",
        title_x=0.5,
        xaxis_title="Product",
        yaxis_title="Initial Count",
        showlegend=False,
        height=450,
        margin=dict(l=40, r=40, t=80, b=40)
    )
    
    return fig

def create_busy_days_chart(filtered_df):
    # Find the busiest days by transaction count
    busy_days = filtered_df.groupby(['date', 'product_name']).size().reset_index()
    busy_days.columns = ['date', 'product_name', 'transaction_count']
    
    # Get top 10 days
    top_days = busy_days.sort_values('transaction_count', ascending=False).head(10)
    top_days['formatted_date'] = top_days['date'].dt.strftime('%Y-%m-%d')
    
    fig = px.bar(
        top_days,
        x='formatted_date',
        y='transaction_count',
        color='product_name',
        color_discrete_map=product_colors,
        labels={'transaction_count': 'Number of Transactions', 'formatted_date': 'Date', 'product_name': 'Product'},
        text='transaction_count'
    )
    
    fig.update_traces(
        textposition='outside',
        texttemplate='%{text}'
    )
    
    fig.update_layout(
        title_text="Top 10 Busiest Transaction Days",
        title_x=0.5,
        xaxis_title="Date",
        yaxis_title="Transaction Count",
        height=450,
        margin=dict(l=40, r=40, t=80, b=80),
        xaxis=dict(tickangle=-45),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def prepare_table_data(filtered_df):
    table_df = filtered_df.copy()
    table_df['date'] = table_df['date'].dt.strftime('%Y-%m-%d')
    # Add instock_items column from products_df
    product_instock = products_df[['product_name', 'instock_items']].set_index('product_name').to_dict()['instock_items']
    table_df['instock_items'] = table_df['product_name'].map(product_instock)
    return table_df[['id', 'product_name', 'category', 'date', 'initial_count', 'final_count', 'instock_items']].to_dict('records')

# Callback for tab content
@app.callback(
    Output("tab-content", "children"),
    [Input("dashboard-tabs", "active_tab"),
     Input("product-filter", "value"),
     Input("year-filter", "value"),
     Input("time-period", "value"),
     Input("category-filter", "value")]
)
def render_tab_content(active_tab, selected_products, selected_year, time_period, selected_category):
    # Filter data based on selections
    filtered_df = df.copy()
    
    # Apply filters only if they are not None and not empty
    if selected_products and len(selected_products) > 0:
        filtered_df = filtered_df[filtered_df['product_name'].isin(selected_products)]
    
    if selected_year and selected_year != 'all':
        filtered_df = filtered_df[filtered_df['year'] == int(selected_year)]
    
    if selected_category and selected_category != 'all':
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    
    # Check if we have data after filtering
    if filtered_df.empty:
        return dbc.Alert(
            "No data available for the selected filters. Please adjust your filter criteria.",
            color="warning",
            className="mt-3"
        )
    
    # Overview Tab
    if active_tab == "tab-overview":
        return [
            dbc.Row([
                # Product Performance Chart
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("Product Performance"),
                            html.Small("Quantity and change analysis by product", className="text-muted")
                        ]),
                        dbc.CardBody([
                            dcc.Graph(
                                figure=create_product_performance_chart(filtered_df),
                                config={'displayModeBar': True, 'scrollZoom': True}
                            )
                        ])
                    ])
                ], width=12, lg=8),
                
                # Product Distribution Chart
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("Product Distribution"),
                            html.Small("Quantity distribution by product", className="text-muted")
                        ]),
                        dbc.CardBody([
                            dcc.Graph(
                                figure=create_product_distribution_chart(filtered_df),
                                config={'displayModeBar': False}
                            )
                        ])
                    ])
                ], width=12, lg=4)
            ], className="mb-4"),
            
            dbc.Row([
                # Value Analysis
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("Product Value Analysis"),
                            html.Small("Quantity and change analysis by product", className="text-muted")
                        ]),
                        dbc.CardBody([
                            dcc.Graph(
                                figure=create_value_analysis_chart(filtered_df),
                                config={'displayModeBar': False}
                            )
                        ])
                    ])
                ], width=12)
            ])
        ]
    
    # Time Analysis Tab
    elif active_tab == "tab-time":
        return [
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("Inventory Trends Over Time"),
                            html.Small(f"Viewing by: {time_period.capitalize()}", className="text-muted")
                        ]),
                        dbc.CardBody([
                            dcc.Graph(
                                figure=create_time_series_chart(filtered_df, time_period),
                                config={'displayModeBar': True}
                            )
                        ])
                    ])
                ], width=12)
            ], className="mb-4"),
            
            dbc.Row([
                # Seasonal Analysis
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("Seasonal Patterns"),
                            html.Small("Quantity distribution across seasons", className="text-muted")
                        ]),
                        dbc.CardBody([
                            dcc.Graph(
                                figure=create_seasonal_chart(filtered_df),
                                config={'displayModeBar': False}
                            )
                        ])
                    ])
                ], width=12, lg=6),
                
                # Month-over-Month Change
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("Inventory Growth Analysis"),
                            html.Small("Monthly changes in inventory levels", className="text-muted")
                        ]),
                        dbc.CardBody([
                            dcc.Graph(
                                figure=create_growth_chart(filtered_df),
                                config={'displayModeBar': False}
                            )
                        ])
                    ])
                ], width=12, lg=6)
            ])
        ]
    
    # Product Details Tab
    elif active_tab == "tab-products":
        return [
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("Product Performance Metrics"),
                            html.Small("Detailed statistics for each product", className="text-muted")
                        ]),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Div(
                                        children=create_product_metrics_cards(filtered_df)
                                    )
                                ])
                            ])
                        ])
                    ])
                ], width=12)
            ], className="mb-4"),
            
            dbc.Row([
                # Transaction Size Distribution
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("Transaction Size Distribution"),
                            html.Small("Distribution of quantities per transaction", className="text-muted")
                        ]),
                        dbc.CardBody([
                            dcc.Graph(
                                figure=create_transaction_size_chart(filtered_df),
                                config={'displayModeBar': False}
                            )
                        ])
                    ])
                ], width=12, lg=6),
                
                # Top Transaction Days
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("Busiest Transaction Days"),
                            html.Small("Days with highest transaction volumes", className="text-muted")
                        ]),
                        dbc.CardBody([
                            dcc.Graph(
                                figure=create_busy_days_chart(filtered_df),
                                config={'displayModeBar': False}
                            )
                        ])
                    ])
                ], width=12, lg=6)
            ])
        ]
    
    # Data Table Tab
    elif active_tab == "tab-data":
        return [
            dbc.Card([
                dbc.CardHeader([
                    html.H5("Inventory Data"),
                    html.Small("Raw transaction data with filtering and sorting", className="text-muted")
                ]),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.P("Search and filter the data using the controls below each column header.", className="mb-3"),
                                html.P([
                                    html.I(className="fas fa-info-circle mr-2", style={"color": "#4361ee"}),
                                    "Tip: Click on column headers to sort the data."
                                ], className="help-text mb-3")
                            ])
                        ], width=12)
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dash_table.DataTable(
                                id='inventory-table',
                                columns=[
                                    {'name': 'ID', 'id': 'id'},
                                    {'name': 'Product Name', 'id': 'product_name'},
                                    {'name': 'Category', 'id': 'category'},
                                    {'name': 'Date', 'id': 'date'},
                                    {'name': 'Initial Count', 'id': 'initial_count', 'type': 'numeric'},
                                    {'name': 'Final Count', 'id': 'final_count', 'type': 'numeric'},
                                    {'name': 'In-Stock Items', 'id': 'instock_items', 'type': 'numeric'}
                                ],
                                data=prepare_table_data(filtered_df),
                                filter_action="native",
                                sort_action="native",
                                sort_mode="multi",
                                page_size=15,
                                style_table={'overflowX': 'auto'},
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
                                    }
                                ],
                                export_format="csv"
                            )
                        ], width=12)
                    ]),
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                dbc.Button("Export to CSV", id="export-csv-btn", color="primary", className="mt-3 mr-2"),
                                dbc.Button("Print Data", id="print-data-btn", color="secondary", className="mt-3"),
                            ])
                        ], width=12)
                    ])
                ])
            ])
        ]
    
    return dbc.Alert(
        "Please select a valid tab",
        color="info",
        className="mt-3"
    )

# Callback for help modal
@app.callback(
    Output("help-modal", "is_open"),
    [Input("help-link", "n_clicks"), Input("close-help", "n_clicks")],
    [State("help-modal", "is_open")],
)
def toggle_help_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

# Callback for data export
@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("export-csv-btn", "n_clicks"),
    [State("product-filter", "value"),
     State("year-filter", "value"),
     State("category-filter", "value")]
)
def export_data(n_clicks, selected_products, selected_year, selected_category):
    if n_clicks:
        # Filter data based on selections
        filtered_df = df[df['product_name'].isin(selected_products)]
        
        if selected_year != 'all':
            filtered_df = filtered_df[filtered_df['year'] == int(selected_year)]
            
        if selected_category != 'all':
            filtered_df = filtered_df[filtered_df['category'] == selected_category]
        
        # Prepare for export
        export_df = filtered_df[['id', 'product_name', 'category', 'date', 'initial_count', 'final_count']]
        export_df['date'] = export_df['date'].dt.strftime('%Y-%m-%d')
        
        # Add instock_items column from products_df
        product_instock = products_df[['product_name', 'instock_items']].set_index('product_name').to_dict()['instock_items']
        export_df['instock_items'] = export_df['product_name'].map(product_instock)
        
        return dcc.send_data_frame(export_df.to_csv, "art_decor_inventory_data.csv")

# Toggle chat panel visibility - Optimized to prevent rerenders
@app.callback(
    [Output("chat-panel", "className"),
     Output("chat-toggle-button", "style")],
    [Input("chat-toggle-button", "n_clicks"),
     Input("close-chat", "n_clicks")],
    [State("chat-panel", "className")],
    prevent_initial_call=True
)
def toggle_chat_panel(open_clicks, close_clicks, current_class):
    triggered_id = ctx.triggered_id
    
    if triggered_id == "chat-toggle-button" and open_clicks:
        return "chat-panel open", {"display": "none"}
    elif triggered_id == "close-chat" and close_clicks:
        return "chat-panel", {"display": "flex"}
    
    return current_class, {"display": "flex"}

# Function to run SQL queries for AI assistant
def run_sql_query(query, params=None):
    """Run a SQL query and return results as a list of dictionaries"""
    try:
        # Connect to the database using the config path
        db_conn = sqlite3.connect(DATABASE_PATH)
        
        # Execute the query
        if params:
            results = pd.read_sql_query(query, db_conn, params=params)
        else:
            results = pd.read_sql_query(query, db_conn)
        
        # Close connection
        db_conn.close()
        
        # Convert to dictionaries
        if len(results) > 0:
            return results.to_dict('records')
        else:
            return []
    except Exception as e:
        print(f"SQL query error: {str(e)}")
        print(f"Query: {query}")
        print(traceback.format_exc())
        return [{"error": str(e)}]

# Function to get database schema for AI context
def get_database_schema():
    """Get the database schema to provide context to the AI"""
    try:
        # Connect to the database using the config path
        db_conn = sqlite3.connect(DATABASE_PATH)
        cursor = db_conn.cursor()
        
        # Get table information
        tables = {}
        table_list = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        
        for table in table_list:
            table_name = table[0]
            # Get column information
            columns = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
            tables[table_name] = [col[1] for col in columns]
        
        # Close connection
        db_conn.close()
        
        return tables
    except Exception as e:
        print(f"Error getting schema: {str(e)}")
        return {}

# Handle user messages and Gemini response - Optimized for performance
@app.callback(
    [Output("chat-messages", "children"),
     Output("chat-history", "data"),
     Output("chat-input", "value"),
     Output("chat-loading", "children")],
    [Input("send-button", "n_clicks"),
     Input("chat-input", "n_submit")],
    [State("chat-input", "value"),
     State("chat-history", "data"),
     State("product-filter", "value"),
     State("year-filter", "value"),
     State("category-filter", "value")],
    prevent_initial_call=True
)
def process_user_message(send_clicks, enter_clicks, user_input, history, selected_products, selected_year, selected_category):
    if not user_input or (not send_clicks and not enter_clicks):
        raise PreventUpdate
    
    # Create filtered dataframe based on current selections
    try:
        filtered_df = df[df['product_name'].isin(selected_products)]
        if selected_year != 'all':
            filtered_df = filtered_df[filtered_df['year'] == int(selected_year)]
        if selected_category != 'all':
            filtered_df = filtered_df[filtered_df['category'] == selected_category]
    except Exception as e:
        print(f"Error filtering dataframe: {str(e)}")
        filtered_df = df  # Fallback to full dataset
    
    # Append user message to history
    if history is None:
        history = {"messages": []}
    elif "messages" not in history:
        history["messages"] = []
    
    history["messages"].append({"sender": "user", "text": user_input})
    
    # Run multiple key queries for every question
    data_queries = {
        "max_initial_count": "SELECT product_name, MAX(initial_count) as max_initial_count FROM Inventory",
        "min_initial_count": "SELECT product_name, MIN(initial_count) as min_initial_count FROM Inventory",
        "max_final_count": "SELECT product_name, MAX(final_count) as max_final_count FROM Inventory",
        "min_final_count": "SELECT product_name, MIN(final_count) as min_final_count FROM Inventory",
        "avg_initial_count": "SELECT product_name, AVG(initial_count) as avg_initial_count FROM Inventory GROUP BY product_name",
        "avg_final_count": "SELECT product_name, AVG(final_count) as avg_final_count FROM Inventory GROUP BY product_name",
        "top_products_by_change": """
            SELECT p.product_name, p.category, 
            SUM(i.final_count - i.initial_count) as total_change 
            FROM Products p
            JOIN Inventory i ON p.product_name = i.product_name
            GROUP BY p.product_name
            ORDER BY total_change DESC
            LIMIT 5
        """,
        "category_performance": """
            SELECT p.category, 
            SUM(i.final_count - i.initial_count) as total_change,
            AVG(i.final_count - i.initial_count) as avg_change
            FROM Products p
            JOIN Inventory i ON p.product_name = i.product_name
            GROUP BY p.category
            ORDER BY total_change DESC
        """,
        "trends_over_time": """
            SELECT date, SUM(final_count - initial_count) as daily_change
            FROM Inventory
            GROUP BY date
            ORDER BY date DESC
            LIMIT 10
        """,
        "product_counts_by_date": "SELECT product_name, date, initial_count, final_count FROM Inventory ORDER BY date DESC"
    }
    all_data_context = ""
    for key, query in data_queries.items():
        result = run_sql_query(query)
        if result and len(result) > 0:
            all_data_context += f"\n\n[{key}]\n" + json.dumps(result, indent=2)
    
    # Get database schema for context
    db_schema = get_database_schema()
    schema_info = "Database tables: " + ", ".join(db_schema.keys()) + ". "
    for table, columns in db_schema.items():
        schema_info += f"Table '{table}' has columns: {', '.join(columns)}. "
    db_context = (
        f"{schema_info}\n\n"
        f"Dataset has {len(filtered_df['product_name'].unique())} products in categories: "
        f"{', '.join(filtered_df['category'].unique())}. "
        f"Date range: {filtered_df['date'].min().strftime('%Y-%m-%d')} to {filtered_df['date'].max().strftime('%Y-%m-%d')}. "
        f"Products include: {', '.join(filtered_df['product_name'].unique()[:5])}"
    )
    
    prompt = f"""You are an analytics assistant for Art & Decor inventory.\n\nYou have live access to the latest inventory data via the query results provided below. \nYou do not have direct SQL access, but you always see up-to-date data.\n\nDatabase context:\n{db_context}\n{all_data_context}\n\nQuestion: {user_input}\n\nProvide a concise, direct answer using the data provided. If the answer is not in the data, say so."""
    
    # Generate response from Gemini
    try:
        response = gemini_model.generate_content(prompt)
        ai_response = response.text
    except Exception as e:
        print(f"Gemini API error: {str(e)}")
        print(traceback.format_exc())
        ai_response = "I encountered an error processing your request. Please try a more specific question about your inventory data."
    
    # Append AI response to history
    history["messages"].append({"sender": "ai", "text": ai_response})
    
    # Build chat messages UI
    messages_ui = []
    for msg in history["messages"]:
        if msg["sender"] == "user":
            messages_ui.append(html.Div(msg["text"], className="message user-message"))
        else:
            if "```" in msg["text"]:
                parts = msg["text"].split("```")
                message_parts = []
                for i, part in enumerate(parts):
                    if i % 2 == 0 and part.strip():
                        message_parts.append(html.Div(part, style={"whiteSpace": "pre-line"}))
                    elif i % 2 == 1:
                        message_parts.append(html.Div(part, className="code-block"))
                messages_ui.append(html.Div(message_parts, className="message ai-message"))
            else:
                messages_ui.append(html.Div(msg["text"], className="message ai-message", style={"whiteSpace": "pre-line"}))
    
    return messages_ui, history, "", ""

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
