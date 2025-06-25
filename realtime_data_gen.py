import sqlite3
import random
import pandas as pd
from datetime import datetime, timedelta
import time
import argparse
import os

# Create a separate database for real-time inventory movements
def create_database():
    """Create a new database for real-time inventory movement tracking"""
    conn = sqlite3.connect('realtime_inventory.db')
    cursor = conn.cursor()
    
    # Drop existing tables if they exist
    cursor.execute('DROP TABLE IF EXISTS InventoryMovements')
    cursor.execute('DROP TABLE IF EXISTS Products')
    
    # Create Products table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Products (
        product_name VARCHAR(100) PRIMARY KEY,
        category VARCHAR(50),
        instock_items INTEGER DEFAULT 0
    )
    ''')
    
    # Create InventoryMovements table to track real-time movements
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS InventoryMovements (
        movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name VARCHAR(100),
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        movement_type VARCHAR(10) CHECK(movement_type IN ('incoming', 'outgoing')),
        quantity INTEGER NOT NULL,
        FOREIGN KEY (product_name) REFERENCES Products(product_name)
    )
    ''')
    
    # Insert sample products
    products = [
        ('Cylindrical Product', 'Type A', random.randint(50, 100)),
        ('Box Product', 'Type B', random.randint(100, 200))
    ]
    
    cursor.executemany('INSERT INTO Products VALUES (?, ?, ?)', products)
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Real-time inventory database created successfully.")

def check_database():
    """Check if database and tables exist, create them if not"""
    if not os.path.exists('realtime_inventory.db'):
        print("Database doesn't exist. Creating it now...")
        create_database()
        return
    
    try:
        # Check if tables exist
        conn = sqlite3.connect('realtime_inventory.db')
        cursor = conn.cursor()
        
        # Check Products table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Products'")
        if cursor.fetchone() is None:
            print("Products table doesn't exist. Creating database tables...")
            conn.close()
            create_database()
            return
        
        # Check if there are products
        cursor.execute("SELECT COUNT(*) FROM Products")
        product_count = cursor.fetchone()[0]
        if product_count == 0:
            print("No products in database. Reinitializing...")
            conn.close()
            create_database()
            return
            
        print(f"Database ready with {product_count} products.")
        conn.close()
    except sqlite3.Error as e:
        print(f"Database error: {e}. Creating new database...")
        create_database()

def generate_movement(conn, frequency=5):
    """Generate a random inventory movement transaction"""
    try:
        cursor = conn.cursor()
        
        # Get a random product
        cursor.execute("SELECT product_name FROM Products ORDER BY RANDOM() LIMIT 1")
        product_name_result = cursor.fetchone()
        
        if not product_name_result:
            print("No products found in database. Creating database first...")
            conn.close()
            create_database()
            conn = sqlite3.connect('realtime_inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT product_name FROM Products ORDER BY RANDOM() LIMIT 1")
            product_name_result = cursor.fetchone()
        
        product_name = product_name_result[0]
        
        # Determine if this will be incoming or outgoing (higher chance of outgoing)
        movement_type = random.choices(['incoming', 'outgoing'], weights=[0.3, 0.7], k=1)[0]
        
        # Set quantity based on movement type
        if movement_type == 'incoming':
            quantity = random.randint(1, 10) * frequency  # Incoming shipments can be larger
        else:
            quantity = random.randint(1, 3) * frequency  # Outgoing (sales) are typically smaller
        
        # Get current stock
        cursor.execute("SELECT instock_items FROM Products WHERE product_name = ?", (product_name,))
        current_stock = cursor.fetchone()[0]
        
        # Make sure we don't go negative on outgoing movements
        if movement_type == 'outgoing':
            if current_stock < quantity:
                quantity = max(1, current_stock)  # Ensure at least 1 item is moved
        
        # Update current stock
        new_stock = current_stock + quantity if movement_type == 'incoming' else current_stock - quantity
        cursor.execute("UPDATE Products SET instock_items = ? WHERE product_name = ?", (new_stock, product_name))
        
        # Record the movement
        cursor.execute('''
        INSERT INTO InventoryMovements (product_name, timestamp, movement_type, quantity)
        VALUES (?, ?, ?, ?)
        ''', (product_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), movement_type, quantity))
        
        # Commit the transaction
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error generating movement: {e}")
        return False

def simulate_realtime_data(duration=60, interval=2, frequency=1):
    """
    Simulate real-time data for a specified duration
    
    Parameters:
    - duration: duration in seconds to run the simulation
    - interval: seconds between transactions
    - frequency: multiplier for transaction size (1=normal, 5=busy, 10=very busy)
    """
    try:
        # Make sure database exists and has tables
        check_database()
        
        conn = sqlite3.connect('realtime_inventory.db')
        
        start_time = time.time()
        end_time = start_time + duration
        
        print(f"Starting real-time data simulation for {duration} seconds...")
        print(f"Generating a transaction every {interval} seconds with frequency {frequency}")
        
        transaction_count = 0
        
        while time.time() < end_time:
            if generate_movement(conn, frequency):
                transaction_count += 1
                print(f"Generated transaction {transaction_count}", end='\r')
            time.sleep(interval)
        
        print(f"\nSimulation complete. Generated {transaction_count} transactions.")
        conn.close()
    except Exception as e:
        print(f"Error in simulation: {e}")

def main():
    parser = argparse.ArgumentParser(description='Generate real-time inventory data')
    parser.add_argument('--create', action='store_true', help='Create a new database')
    parser.add_argument('--duration', type=int, default=60, help='Duration in seconds')
    parser.add_argument('--interval', type=float, default=2, help='Seconds between transactions')
    parser.add_argument('--frequency', type=int, default=1, choices=[1, 5, 10], 
                        help='Transaction frequency (1=normal, 5=busy, 10=very busy)')
    
    args = parser.parse_args()
    
    if args.create:
        create_database()
        return
    
    simulate_realtime_data(args.duration, args.interval, args.frequency)

if __name__ == "__main__":
    main() 