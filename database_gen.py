import sqlite3
import random
from datetime import datetime, timedelta

# Create SQLite database
conn = sqlite3.connect('artdeco_inventory.db')
cursor = conn.cursor()

# Drop existing tables if they exist
cursor.execute('DROP TABLE IF EXISTS Inventory')
cursor.execute('DROP TABLE IF EXISTS Products')

# Create simplified tables for product tracking
cursor.execute('''
CREATE TABLE IF NOT EXISTS Products (
    product_name VARCHAR(100) PRIMARY KEY,
    category VARCHAR(50),
    instock_items INTEGER NOT NULL DEFAULT 0
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name VARCHAR(100),
    date DATE NOT NULL,
    initial_count INTEGER NOT NULL,
    final_count INTEGER NOT NULL,
    FOREIGN KEY (product_name) REFERENCES Products(product_name)
)
''')

# Insert art and decor product data with categories
products = [
    ('Cylindrical Product', 'Type A', random.randint(50, 100)),
    ('Box Product', 'Type B', random.randint(100, 200))
]

cursor.executemany('INSERT INTO Products VALUES (?, ?, ?)', products)

# Generate inventory data with morning and night counts
inventory_data = []
id_counter = 1

# Set date range (last 30 days)
end_date = datetime.now()
start_date = end_date - timedelta(days=30)
date_range = (end_date - start_date).days

# Initial inventory for each product
current_inventory = {
    'Cylindrical Product': random.randint(150, 200),
    'Box Product': random.randint(300, 400)
}

# Generate inventory records for each day
for day in range(date_range):
    current_date = start_date + timedelta(days=day)
    formatted_date = current_date.strftime('%Y-%m-%d')
    
    # Weekend vs weekday factor (higher sales on weekends)
    is_weekend = current_date.weekday() >= 5  # 5, 6 = Saturday, Sunday
    weekend_factor = 1.5 if is_weekend else 1.0
    
    for product in products:
        product_name = product[0]  # First element is product_name
        
        # Initial count is the previous day's final count
        initial_count = current_inventory[product_name]
        
        # Daily changes - simulate real-world activity
        # Higher-priced items (Cylindrical Product) tend to move slower
        if product_name == 'Cylindrical Product':
            change = int(random.randint(-8, 12) * weekend_factor)
        else:  # Box Product
            change = int(random.randint(-15, 20) * weekend_factor)
        
        # Ensure inventory doesn't go below a minimum threshold
        final_count = max(initial_count + change, 5)
        
        # Update current inventory for next day's initial count
        current_inventory[product_name] = final_count
        
        inventory_data.append((id_counter, product_name, formatted_date, initial_count, final_count))
        id_counter += 1

# Insert the inventory data
cursor.executemany('INSERT INTO Inventory (id, product_name, date, initial_count, final_count) VALUES (?, ?, ?, ?, ?)', inventory_data)

# Update the instock_items with the most recent counts
for product_name, final_count in current_inventory.items():
    cursor.execute('UPDATE Products SET instock_items = ? WHERE product_name = ?', (final_count, product_name))

# Commit changes and close connection
conn.commit()
conn.close()

print(f"Art & Decor inventory database created successfully with {len(inventory_data)} records.")
print(f"Tracking {len(products)} products over {date_range} days.")
print("Each record includes date, initial count, and final count.")
print("Date range: Last 30 days")
