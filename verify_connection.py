import sqlite3
from config import DATABASE_PATH
import sys

def verify_database():
    """Verify database connection and schema"""
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("❌ No tables found in the database")
            return False
            
        print("✅ Database connection successful")
        print("📊 Found tables:", ", ".join([table[0] for table in tables]))
        
        # Check table schemas
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"\nTable '{table_name}' columns:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        return False

def main():
    print("🔍 Verifying database connection...\n")
    
    # Verify database
    db_ok = verify_database()
    
    # Summary
    print("\n📋 Connection Summary:")
    print(f"Database: {'✅ Connected' if db_ok else '❌ Failed'}")
    
    # Exit with appropriate status code
    sys.exit(0 if db_ok else 1)

if __name__ == "__main__":
    main() 