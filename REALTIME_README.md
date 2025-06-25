# Real-Time Inventory Movement Dashboard

This dashboard tracks real-time inventory movements (incoming and outgoing) across all products without focusing on specific items. It visualizes the flow of inventory through your system as it happens.

## Features

- **Live Updates**: Automatically refreshes every 5 seconds
- **Real-Time Movement Tracking**: Monitors both incoming and outgoing inventory
- **Category Analysis**: Shows movement distribution by product category
- **Current Stock Levels**: Displays up-to-date inventory counts by product
- **Recent Activity Feed**: Shows the latest transactions in real-time
- **Time Window Selection**: Filter data by different time periods (15 min, 30 min, 1 hour, etc.)

## Getting Started

### Prerequisites

Ensure you have the following Python packages installed:

```bash
pip install dash dash-bootstrap-components plotly pandas sqlite3
```

### Running the Dashboard

There are two main ways to run the system:

#### 1. Using the Start Script (Recommended)

The easiest way to start everything is to use the starter script:

```bash
python start_realtime_dashboard.py
```

This will:
1. Create a new real-time inventory database
2. Start generating random inventory movements
3. Launch the dashboard

Additional options:
- `--no-reset`: Use the existing database without resetting
- `--frequency 5`: Increase transaction frequency (1=normal, 5=busy, 10=very busy)
- `--duration 3600`: Set a time limit in seconds for data generation (optional)

Example for a busy store with existing data:
```bash
python start_realtime_dashboard.py --no-reset --frequency 5
```

#### 2. Running Components Manually

If you prefer to run each component separately:

1. Create the initial database:
```bash
python realtime_data_gen.py --create
```

2. Start generating inventory movements:
```bash
python realtime_data_gen.py --frequency 1
```

3. In a separate terminal, run the dashboard:
```bash
python realtime_dashboard.py
```

### Accessing the Dashboard

Once running, open your web browser and go to:
```
http://127.0.0.1:8050
```

## Using the Dashboard

- **Time Window**: Select different time periods to view data (15 minutes to all day)
- **Refresh Button**: Manually refresh data if needed (automatic refresh happens every 5 seconds)
- **Movement Timeline**: Shows incoming and outgoing movements over time
- **Category Breakdown**: Displays movement distribution by product category
- **Current Stock**: Shows current inventory levels by product
- **Recent Movements**: Lists the latest transactions with timestamps

## System Components

- **realtime_data_gen.py**: Generates random inventory movements
- **realtime_dashboard.py**: The Dash dashboard application
- **start_realtime_dashboard.py**: Helper script to run everything together

## Database Structure

The system uses an SQLite database (`realtime_inventory.db`) with two tables:

1. **Products**: Stores product information and current stock levels
   - product_id, product_name, category, current_stock

2. **InventoryMovements**: Records all inventory transactions
   - movement_id, product_id, timestamp, movement_type, quantity 