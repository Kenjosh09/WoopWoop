"""
Constants used throughout the Ganja Paraiso bot.
"""
import os
import sys
from typing import Dict, List, Any, Union

# Bot states for conversation handlers
CATEGORY, STRAIN_TYPE, BROWSE_BY, PRODUCT_SELECTION, QUANTITY, CONFIRM, DETAILS, CONFIRM_DETAILS, PAYMENT, TRACKING = range(10)
ADMIN_SEARCH, ADMIN_TRACKING = 10, 11

# Define conversation states
TRACK_ORDER = 1

# Support admin user ID (the Telegram user ID that will receive support requests)
SUPPORT_ADMIN_ID = os.getenv("SUPPORT_ADMIN_ID", "123456789")
SUPPORT_ADMIN_USERNAME = os.getenv("SUPPORT_ADMIN_USERNAME", "your_support_username")

# Get configuration from environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN environment variable not set")
    sys.exit(1)
    
ADMIN_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "5167750837"))
GCASH_NUMBER = os.getenv("GCASH_NUMBER", "09171234567")
GCASH_QR_CODE_URL = os.getenv("GCASH_QR_CODE_URL", "https://example.com/gcash_qr.jpg")

# Google API configuration
GOOGLE_SHEET_NAME = "Telegram Orders"
GOOGLE_CREDENTIALS_FILE = "woop-woop-project-2ba60593fd8d.json"
PAYMENT_SCREENSHOTS_FOLDER_ID = "1hIanVMnTFSnKvHESoK7mgexn_QwlmF69"

# ----- Credentials File Configuration -----
# Default location (for backward compatibility)
DEFAULT_CREDENTIALS_FILE = "woop-woop-project-2ba60593fd8d.json"

# Known locations to try in order if default isn't found
CREDENTIALS_LOCATIONS = [
    # Exact path you provided
    r"C:\Users\Kenneth\OneDrive\Documents\Telegram Bot\woop-woop-project-2ba60593fd8d.json",
    
    # Current directory
    DEFAULT_CREDENTIALS_FILE,
    
    # Environment variable (if set)
    os.environ.get("GOOGLE_CREDENTIALS_FILE", "")
]

# Google Sheets Column Mappings
SHEET_COLUMNS = {
    "order_id": "Order ID",
    "telegram_id": "Telegram ID",
    "name": "Customer Name",
    "address": "Address",
    "contact": "Contact",
    "product": "Product",
    "quantity": "Quantity",
    "price": "Price",
    "status": "Status",
    "payment_url": "Payment URL",
    "order_date": "Order Date",
    "notes": "Notes",
    "tracking_link": "Tracking Link"
}

# Default headers for orders sheet
SHEET_HEADERS = [
    SHEET_COLUMNS["order_id"],
    SHEET_COLUMNS["telegram_id"],
    SHEET_COLUMNS["name"],
    SHEET_COLUMNS["address"],
    SHEET_COLUMNS["contact"],
    SHEET_COLUMNS["product"],
    SHEET_COLUMNS["quantity"],
    SHEET_COLUMNS["price"],
    SHEET_COLUMNS["status"],
    SHEET_COLUMNS["payment_url"],
    SHEET_COLUMNS["order_date"],
    SHEET_COLUMNS["notes"],
    SHEET_COLUMNS["tracking_link"]
]

# Mapping of sheet column names to their index (1-based for gspread API)
SHEET_COLUMN_INDICES = {name: idx+1 for idx, name in enumerate(SHEET_HEADERS)}

# Regular expressions used for validation
REGEX = {
    "shipping_details": r"^(.+?)\s*\/\s*(.+?)\s*\/\s*(\+?[\d\s\-]{10,15})$",
    "quantity": r"(\d+)"
}

# Rate limiting configuration
RATE_LIMITS = {
    "order": 10,    # Max 10 orders per hour
    "payment": 15,  # Max 15 payment uploads per hour
    "track": 30,    # Max 30 tracking requests per hour
    "admin": 50,     # Max 50 admin actions per hour
    "checkout": {"limit": 10, "window": 3600},  # 10 checkouts per hour
    "verify": {"limit": 20, "window": 3600},  # 20 verifications per hour
    "global": {"limit": 100, "window": 3600},  # 100 actions per hour
}

# Cache expiration times in seconds
CACHE_EXPIRY = {
    "inventory": 300,     # 5 minutes
    "orders": 60,   # 1 minute
    "customer_info": 600,  # 10 minutes
    "sheets": 120,     # 2 minutes
    "drive": 600,      # 10 minutes
}

# Function to find the first valid credentials file
def find_credentials_file():
    """Find the first valid Google credentials file from known locations"""
    for location in CREDENTIALS_LOCATIONS:
        if location and os.path.isfile(location):
            print(f"✅ Found credentials file: {location}")
            return location
            
    # If no valid file found, use the default and warn
    print(f"⚠️ WARNING: Could not locate credentials file in known locations")
    print(f"  Will try with default: {DEFAULT_CREDENTIALS_FILE}")
    return DEFAULT_CREDENTIALS_FILE

# Set the credentials file path
GOOGLE_CREDENTIALS_FILE = find_credentials_file()

# Log the selected path
print(f"Using Google credentials from: {GOOGLE_CREDENTIALS_FILE}")

# Default inventory for fallback
DEFAULT_INVENTORY = [
    {"Name": "Unknown Indica", "Type": "indica", "Tag": "buds", "Price": 2000, "Stock": 5},
    {"Name": "Unknown Sativa", "Type": "sativa", "Tag": "buds", "Price": 2000, "Stock": 5},
    {"Name": "Unknown Hybrid", "Type": "hybrid", "Tag": "buds", "Price": 2000, "Stock": 5},
    {"Name": "Local BG", "Type": "", "Tag": "local", "Price": 1000, "Stock": 10},
    {"Name": "Basic Cart", "Type": "", "Tag": "carts", "Brand": "Generic", "Weight": "1g", "Price": 1500, "Stock": 3},
    {"Name": "Basic Edible", "Type": "hybrid", "Tag": "edibs", "Price": 500, "Stock": 5}
]