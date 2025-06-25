import json
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
from config import DATABASE_PATH

def get_graph_data_context():
    """
    Get all relevant graph data to provide context to Gemini for question answering.
    Returns a dictionary containing various graph data points and metrics.
    """
    try:
        # Connect to the database
        db_conn = sqlite3.connect(DATABASE_PATH)
        
        # Get the last 30 days of data for analysis
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Read data from database
        df = pd.read_sql_query("""
            SELECT * FROM inventory_movements 
            WHERE timestamp BETWEEN ? AND ?
        """, db_conn, params=[start_date, end_date])
        
        if df.empty:
            return {"error": "No data available for analysis"}
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Calculate various metrics and data points
        context = {
            "time_period": {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            },
            "summary_metrics": {
                "total_transactions": len(df),
                "total_incoming": df[df['movement_type'] == 'incoming']['quantity'].sum(),
                "total_outgoing": df[df['movement_type'] == 'outgoing']['quantity'].sum(),
                "net_change": df[df['movement_type'] == 'incoming']['quantity'].sum() - 
                             df[df['movement_type'] == 'outgoing']['quantity'].sum()
            },
            "category_metrics": df.groupby('category').agg({
                'quantity': ['sum', 'mean', 'count']
            }).to_dict(),
            "product_metrics": df.groupby('product_name').agg({
                'quantity': ['sum', 'mean', 'count']
            }).to_dict(),
            "time_series": {
                "daily": df.groupby([df['timestamp'].dt.date, 'movement_type'])['quantity'].sum().to_dict(),
                "hourly": df.groupby([df['timestamp'].dt.hour, 'movement_type'])['quantity'].sum().to_dict()
            },
            "busiest_periods": {
                "days": df.groupby(df['timestamp'].dt.date)['quantity'].sum().nlargest(5).to_dict(),
                "hours": df.groupby(df['timestamp'].dt.hour)['quantity'].sum().nlargest(5).to_dict()
            }
        }
        
        # Close database connection
        db_conn.close()
        
        return context
        
    except Exception as e:
        return {"error": f"Error getting graph context: {str(e)}"}

def format_context_for_gemini(context):
    """
    Format the context data into a natural language description for Gemini.
    """
    if "error" in context:
        return f"Error: {context['error']}"
    
    description = f"""
    Here is the inventory movement data for the period {context['time_period']['start_date']} to {context['time_period']['end_date']}:

    Summary:
    - Total transactions: {context['summary_metrics']['total_transactions']}
    - Total incoming inventory: {context['summary_metrics']['total_incoming']}
    - Total outgoing inventory: {context['summary_metrics']['total_outgoing']}
    - Net inventory change: {context['summary_metrics']['net_change']}

    Category Analysis:
    """
    
    # Add category metrics
    for category, metrics in context['category_metrics'].items():
        description += f"\n{category}:"
        description += f"\n  - Total quantity: {metrics['quantity']['sum']}"
        description += f"\n  - Average quantity per transaction: {metrics['quantity']['mean']:.2f}"
        description += f"\n  - Number of transactions: {metrics['quantity']['count']}"
    
    # Add busiest periods
    description += "\n\nBusiest Days:"
    for date, quantity in context['busiest_periods']['days'].items():
        description += f"\n- {date}: {quantity} units"
    
    description += "\n\nBusiest Hours:"
    for hour, quantity in context['busiest_periods']['hours'].items():
        description += f"\n- {hour:02d}:00: {quantity} units"
    
    return description

def get_graph_context_for_gemini():
    """
    Main function to get formatted graph context for Gemini.
    Returns a string containing natural language description of the graph data.
    """
    context = get_graph_data_context()
    return format_context_for_gemini(context)

if "max initial count" in user_input.lower():
    data_result = run_sql_query("SELECT product_name, MAX(initial_count) as max_initial_count FROM Inventory")
    data_context = "\n\nQuery results:\n" + json.dumps(data_result, indent=2)
else:
    data_result = gemini_safe_query('top_products_by_change')
    data_context = ""
    if data_result and len(data_result) > 0:
        data_context = "\n\nQuery results:\n" + json.dumps(data_result, indent=2) 