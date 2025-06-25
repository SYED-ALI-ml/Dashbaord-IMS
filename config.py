import os
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# Gemini API configuration
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyBo00GRHkn3OZrp8ESCGgr0rYhRUcIw0ro')

# Database configuration
DATABASE_PATH = os.environ.get('DATABASE_PATH', str(PROJECT_ROOT / 'artdeco_inventory.db'))

# Ensure database directory exists
db_dir = Path(DATABASE_PATH).parent
db_dir.mkdir(parents=True, exist_ok=True)

# Dashboard configuration
DASHBOARD_TITLE = "Art Deco Inventory Dashboard"
DASHBOARD_THEME = "plotly_white"

# Logging configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FILE = os.environ.get('LOG_FILE', str(PROJECT_ROOT / 'dashboard.log')) 