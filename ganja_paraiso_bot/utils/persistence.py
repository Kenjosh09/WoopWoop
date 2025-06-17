"""
Functions for managing persistence and data storage.
"""
import os
import pickle
import shutil
import time
from datetime import datetime
from typing import Dict, Any

def get_persistence_file_size():
    """
    Get the size of the persistence file in megabytes.
    
    Returns:
        float: Size of the persistence file in MB, or 0 if file doesn't exist
    """
    try:
        # Check if the file exists
        if not os.path.exists("bot_persistence"):
            return 0
            
        # Get file size in bytes and convert to MB
        size_in_bytes = os.path.getsize("bot_persistence")
        size_in_mb = size_in_bytes / (1024 * 1024)
        
        return size_in_mb
    except Exception:
        # If there's an error, return 0
        return 0

def check_context_data_size(user_data, key, max_size_kb=512):
    """
    Check if a data structure in user_data is getting too large and should be trimmed.
    
    Args:
        user_data (dict): User data dictionary
        key (str): Key of the data structure to check
        max_size_kb (int): Maximum size in kilobytes
        
    Returns:
        bool: True if data is too large, False otherwise
    """
    if key not in user_data:
        return False
    
    try:
        # Estimate size by pickling
        data_size = len(pickle.dumps(user_data[key])) / 1024  # size in KB
        
        return data_size > max_size_kb
    except Exception:
        # If there's an error in size calculation, assume it's not too large
        return False

def trim_large_data_structures(user_data, loggers=None):
    """
    Monitor and trim large data structures in user_data to prevent memory issues.
    
    Args:
        user_data (dict): User data dictionary
        loggers (dict, optional): Dictionary of logger instances
        
    Returns:
        int: Number of items trimmed
    """
    trim_count = 0
    
    # Check and trim oversized message history
    if check_context_data_size(user_data, "message_history", max_size_kb=256):
        # If present and too large, keep only the 20 most recent messages
        if isinstance(user_data["message_history"], list):
            user_data["message_history"] = user_data["message_history"][-20:]
            trim_count += 1
            if loggers and "main" in loggers:
                loggers["main"].info("Trimmed large message history to last 20 messages")
            else:
                print("Trimmed large message history to last 20 messages")
    
    # Check and clean up any large cached data
    for key in list(user_data.keys()):
        if key.startswith("cached_") and check_context_data_size(user_data, key, max_size_kb=128):
            # Remove oversized cache entries
            del user_data[key]
            trim_count += 1
            if loggers and "main" in loggers:
                loggers["main"].info(f"Removed oversized cached data: {key}")
            else:
                print(f"Removed oversized cached data: {key}")
    
    return trim_count

def cleanup_persistence_file(context, loggers=None):
    """
    Create a backup of the persistence file and rebuild it with only essential data.
    This helps prevent the pickle file from growing too large over time.
    
    Args:
        context: The conversation context
        loggers (dict, optional): Dictionary of logger instances
        
    Returns:
        tuple: (success, old_size, new_size)
    """
    try:
        # Check current file size
        current_size = get_persistence_file_size()
        
        # If file is smaller than 10MB, no need to clean up
        if current_size < 10:
            return True, current_size, current_size
        
        # Create a backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"bot_persistence_backup_{timestamp}"
        
        # Copy the file
        if os.path.exists("bot_persistence"):
            shutil.copy2("bot_persistence", backup_filename)
            if loggers and "main" in loggers:
                loggers["main"].info(f"Created persistence backup: {backup_filename}")
            else:
                print(f"Created persistence backup: {backup_filename}")
        
        # Clean up the context data before saving
        # Note: We don't modify context directly, as that would change the running state
        
        # We need to manually write a new persistence file with cleaned data
        # This approach keeps the running context intact but creates a cleaner file
        
        # First, create a clean copy of essential data
        essential_data = {
            "user_data": {},
            "chat_data": {},
            "bot_data": {
                "start_time": context.bot_data.get("start_time", time.time()),
                "sessions": context.bot_data.get("sessions", {})
            },
            "callback_data": context.bot_data.get("callback_data", {})
        }
        
        # Copy only active user data (last 30 days)
        now = time.time()
        for user_id, user_data in context.user_data.items():
            last_activity = user_data.get("last_activity_time", 0)
            
            # If active in the last 30 days, keep their data
            if now - last_activity < 2592000:  # 30 days in seconds
                # Scrub sensitive data before persistence
                scrubbed_data = scrub_sensitive_data(user_data)
                essential_data["user_data"][user_id] = scrubbed_data
        
        # Use pickle to save the essential data
        with open("bot_persistence_clean", "wb") as f:
            pickle.dump(essential_data, f)
        
        # Get the new file size
        new_size = os.path.getsize("bot_persistence_clean") / (1024 * 1024)
        
        # Rename the clean file to replace the original
        try:
            if os.path.exists("bot_persistence_clean"):
                # On Windows, we need to make sure the target doesn't exist
                if os.path.exists("bot_persistence"):
                    os.remove("bot_persistence")
                os.rename("bot_persistence_clean", "bot_persistence")
        except Exception as e:
            if loggers and "errors" in loggers:
                loggers["errors"].error(f"Error replacing persistence file: {e}")
            else:
                print(f"Error replacing persistence file: {e}")
            return False, current_size, current_size
        
        return True, current_size, new_size
        
    except Exception as e:
        if loggers and "errors" in loggers:
            loggers["errors"].error(f"Error cleaning up persistence file: {e}")
        else:
            print(f"Error cleaning up persistence file: {e}")
        return False, current_size, current_size

def scrub_sensitive_data(data_dict):
    """
    Recursively remove sensitive data from dictionaries before persistence.
    
    Args:
        data_dict (dict): Dictionary to scrub
        
    Returns:
        dict: Scrubbed dictionary
    """
    if not isinstance(data_dict, dict):
        return data_dict
    
    scrubbed_dict = {}
    
    for key, value in data_dict.items():
        # Skip sensitive keys entirely
        if key in ['password', 'credit_card', 'token', 'secret']:
            continue
        
        # Recursively scrub nested dictionaries
        if isinstance(value, dict):
            scrubbed_dict[key] = scrub_sensitive_data(value)
        # Scrub sensitive data in lists
        elif isinstance(value, list):
            scrubbed_dict[key] = [
                scrub_sensitive_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        # Special handling for potentially sensitive fields
        elif isinstance(value, str) and key in ['address', 'contact', 'phone', 'email']:
            # Don't actually store the sensitive data in persistence
            scrubbed_dict[key] = f"{value[:3]}***(masked for security)"
        else:
            scrubbed_dict[key] = value
    
    return scrubbed_dict