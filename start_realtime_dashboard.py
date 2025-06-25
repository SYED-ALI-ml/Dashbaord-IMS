import subprocess
import time
import os
import threading
import argparse
import sqlite3

def check_database_exists():
    """Check if the realtime inventory database exists and has the required tables"""
    if not os.path.exists('realtime_inventory.db'):
        return False
    
    try:
        # Try to connect and query the Products table
        conn = sqlite3.connect('realtime_inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Products'")
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except:
        return False

def run_data_generator(initial_setup=True, duration=None, frequency=1):
    """Run the data generator script"""
    # Always create the database if it doesn't exist or tables are missing
    if initial_setup or not check_database_exists():
        print("Creating new real-time inventory database...")
        setup_cmd = ["python", "realtime_data_gen.py", "--create"]
        subprocess.run(setup_cmd)
    else:
        print("Using existing database (tables already exist)...")
        
    # Start data generator as background process
    print(f"Starting data generator (frequency={frequency})...")
    
    # Build command based on parameters
    cmd = ["python", "realtime_data_gen.py", "--frequency", str(frequency)]
    
    if duration:
        cmd.extend(["--duration", str(duration)])
    
    # Start the process
    return subprocess.Popen(cmd)

def run_dashboard():
    """Run the dashboard"""
    print("Starting real-time inventory dashboard...")
    dashboard_proc = subprocess.Popen(["python", "realtime_dashboard.py"])
    return dashboard_proc

def main():
    """Main function to start both services"""
    parser = argparse.ArgumentParser(description='Start the real-time inventory system')
    parser.add_argument('--no-reset', action='store_true', help='Do not reset the database')
    parser.add_argument('--frequency', type=int, choices=[1, 5, 10], default=1, 
                        help='Transaction frequency (1=normal, 5=busy, 10=very busy)')
    parser.add_argument('--duration', type=int, help='Duration to run data generator (in seconds)')
    
    args = parser.parse_args()
    
    try:
        # Start data generator
        generator_proc = run_data_generator(
            initial_setup=not args.no_reset, 
            duration=args.duration,
            frequency=args.frequency
        )
        
        # Allow the database to populate with some initial data
        time.sleep(5)
        
        # Start dashboard
        dashboard_proc = run_dashboard()
        
        print("\nReal-time inventory system started!")
        print("-------------------------------------")
        print("Data generator and dashboard are now running.")
        print("Open your browser at http://127.0.0.1:8050 to view the dashboard.")
        print("Press Ctrl+C to stop all services.")
        
        # Wait for user to press Ctrl+C
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down services...")
        
        # Terminate processes
        if 'generator_proc' in locals():
            generator_proc.terminate()
        if 'dashboard_proc' in locals():
            dashboard_proc.terminate()
        
        print("Services stopped. Goodbye!")

if __name__ == "__main__":
    main() 