import sqlite3

# Connect to the database
conn = sqlite3.connect('artdeco_inventory.db')
cursor = conn.cursor()

# Print Products table
print("\n=== ART & DECOR PRODUCTS ===\n")
print(f"{'Product ID':<10} {'Product Name':<35} {'Category':<20}")
print("-" * 65)

cursor.execute("SELECT * FROM Products")
for product in cursor.fetchall():
    print(f"{product[0]:<10} {product[1]:<35} {product[2]:<20}")

# Print Inventory sample
print("\n=== INVENTORY RECORDS (SAMPLE) ===\n")
print(f"{'ID':<5} {'Product ID':<10} {'Date':<12} {'Initial Count':<15} {'Final Count':<15} {'Variance':<10}")
print("-" * 72)

cursor.execute("SELECT COUNT(*) FROM Inventory")
total_records = cursor.fetchone()[0]
print(f"Total Records: {total_records}\n")

cursor.execute("SELECT * FROM Inventory ORDER BY date DESC LIMIT 20")
for item in cursor.fetchall():
    print(f"{item[0]:<5} {item[1]:<10} {item[2]:<12} {item[3]:<15} {item[4]:<15} {item[5]:<+10}")

# Print inventory summary
print("\n=== INVENTORY SUMMARY BY PRODUCT ===\n")
cursor.execute("""
    SELECT 
        p.product_id, 
        p.product_name,
        p.category,
        COUNT(i.id) as records_count,
        AVG(i.initial_count) as avg_initial,
        AVG(i.final_count) as avg_final,
        AVG(i.variance) as avg_variance,
        SUM(i.variance) as total_variance
    FROM 
        Products p
    JOIN 
        Inventory i ON p.product_id = i.product_id
    GROUP BY 
        p.product_id
    ORDER BY 
        total_variance DESC
""")

print(f"{'Product ID':<10} {'Product Name':<35} {'Category':<15} {'Avg Initial':<12} {'Avg Final':<12} {'Avg Change':<12} {'Total Change':<12}")
print("-" * 110)

for row in cursor.fetchall():
    print(f"{row[0]:<10} {row[1]:<35} {row[2]:<15} {row[4]:<12.2f} {row[5]:<12.2f} {row[6]:<+12.2f} {row[7]:<+12.0f}")

# Show daily trends
print("\n=== DAILY INVENTORY TRENDS ===\n")
cursor.execute("""
    SELECT 
        date,
        SUM(variance) as total_daily_change
    FROM 
        Inventory
    GROUP BY 
        date
    ORDER BY 
        date DESC
    LIMIT 10
""")

print(f"{'Date':<12} {'Net Change':<12}")
print("-" * 25)

for row in cursor.fetchall():
    print(f"{row[0]:<12} {row[1]:<+12}")

# Print products with significant changes
print("\n=== SIGNIFICANT INVENTORY CHANGES (Last 7 Days) ===\n")
cursor.execute("""
    SELECT 
        p.product_id,
        p.product_name,
        i.date,
        i.initial_count,
        i.final_count,
        i.variance
    FROM 
        Inventory i
    JOIN
        Products p ON i.product_id = p.product_id
    WHERE 
        i.date >= date('now', '-7 days')
        AND ABS(i.variance) > 15
    ORDER BY 
        ABS(i.variance) DESC,
        i.date DESC
    LIMIT 10
""")

print(f"{'Product ID':<10} {'Product Name':<35} {'Date':<12} {'Initial':<10} {'Final':<10} {'Change':<10}")
print("-" * 90)

for row in cursor.fetchall():
    print(f"{row[0]:<10} {row[1]:<35} {row[2]:<12} {row[3]:<10} {row[4]:<10} {row[5]:<+10}")

# Close connection
conn.close()