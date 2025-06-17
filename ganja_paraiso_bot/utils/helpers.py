"""
Helper functions used across the application.
"""
import asyncio
import json
import os
import pickle
import random
import string
import time
from datetime import datetime
from typing import Dict, Any, Set, Tuple, Union

from telegram.ext import ContextTypes

from ganja_paraiso_bot.config.emoji import EMOJI
from ganja_paraiso_bot.config.status import STATUS

def generate_order_id():
    """
    Generate a short, unique order ID.
    Format: WW-[last 4 digits of timestamp]-[3 random letters]
    
    Returns:
        str: Unique order ID
    """
    timestamp = int(time.time())
    last_4_digits = str(timestamp)[-4:]
    # Excluding confusing letters I, O
    random_letters = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ', k=3))
    return f"WW-{last_4_digits}-{random_letters}"

def get_status_message(status_key, tracking_link=None):
    """
    Get a formatted status message based on status key.
    
    Args:
        status_key (str): Status key
        tracking_link (str, optional): Tracking link if available
        
    Returns:
        tuple: (emoji, formatted_message)
    """
    # Convert from Google Sheet format to status dictionary key if needed
    status_key = status_key.lower().replace(' ', '_')
    
    # Handle special case for payment confirmed (different format in sheet vs dict)
    if "payment_confirmed" in status_key:
        status_key = "payment_confirmed"
    
    # Get status info from dictionary, or use fallback
    status_info = STATUS.get(status_key, {
        "label": status_key.replace('_', ' ').title(),
        "description": f"Your order is currently marked as: {status_key.replace('_', ' ').title()}",
        "emoji": EMOJI.get("info")
    })
    
    emoji = status_info.get("emoji", EMOJI.get("info"))
    description = status_info.get("description", "")
    
    # Handle tracking link for booked status
    if status_key == "booked" and tracking_link:
        description = status_info.get("with_tracking", description)
        
    return emoji, description

def get_user_orders(user_id):
    """
    Get a list of orders for a specific user.
    
    Note: This is currently a stub that returns an empty list. 
    In a real implementation, this would query the database or Google Sheets.
    
    Args:
        user_id (int): User's Telegram ID
        
    Returns:
        list: List of order dictionaries sorted by date (newest first)
    """
    # In a real implementation, this would query the database/Google Sheets
    # Each order should have 'order_id', 'date', 'total', etc.
    return []

def get_support_deep_link(user_id, order_id):
    """
    Create a deep link for support chat with prepared message.
    
    Args:
        user_id (int): User's Telegram ID
        order_id (str): Order ID for the support request
        
    Returns:
        str: Deep link URL for support chat
    """
    import urllib.parse
    from ganja_paraiso_bot.config.constants import SUPPORT_ADMIN_USERNAME
    
    message = f"Hi Support, I need help with my order. My user ID is {user_id} and my order ID is {order_id}."
    encoded_message = urllib.parse.quote(message)
    
    deep_link = f"https://t.me/{SUPPORT_ADMIN_USERNAME}?start&text={encoded_message}"
    
    return deep_link

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

def check_rate_limit(context: ContextTypes.DEFAULT_TYPE, user_id: int, action_type: str) -> bool:
    """
    Check if user has exceeded rate limits.
    
    Args:
        context: The conversation context
        user_id (int): User's Telegram ID
        action_type (str): Type of action being rate limited
        
    Returns:
        bool: True if within limits, False if exceeded
    """
    from ganja_paraiso_bot.config.constants import RATE_LIMITS
    
    if "rate_limits" not in context.bot_data:
        context.bot_data["rate_limits"] = {}
        
    key = f"{user_id}:{action_type}"
    now = time.time()
    
    if key not in context.bot_data["rate_limits"]:
        context.bot_data["rate_limits"][key] = {"count": 1, "first_action": now}
        return True
        
    data = context.bot_data["rate_limits"][key]
    
    # Reset counter if more than 1 hour has passed
    if now - data["first_action"] > 3600:
        data["count"] = 1
        data["first_action"] = now
        return True
        
    # Get limit for this action type
    max_actions = RATE_LIMITS.get(action_type, 20)  # Default limit
    
    # Increment and check
    data["count"] += 1
    return data["count"] <= max_actions

def get_user_session(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> Dict[str, Any]:
    """
    Get or create a user session.
    
    Args:
        context: The conversation context
        user_id: User's Telegram ID
        
    Returns:
        Dict[str, Any]: User session data
    """
    if "sessions" not in context.bot_data:
        context.bot_data["sessions"] = {}
        
    if user_id not in context.bot_data["sessions"]:
        context.bot_data["sessions"][user_id] = {
            "last_activity": time.time(),
            "order_count": 0,
            "total_spent": 0,
            "preferences": {}
        }
        
    # Update last activity time
    context.bot_data["sessions"][user_id]["last_activity"] = time.time()
    
    # Check user data size and trim if necessary (function defined elsewhere)
    if hasattr(context, "user_data") and user_id in context.user_data:
        from ganja_paraiso_bot.utils.persistence import trim_large_data_structures
        trim_large_data_structures(context.user_data[user_id])
    
    return context.bot_data["sessions"][user_id]

def cleanup_old_sessions(context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Clean up old or inactive user sessions to prevent memory leaks.
    
    Args:
        context: The conversation context
        
    Returns:
        int: Number of sessions cleaned up
    """
    if "sessions" not in context.bot_data:
        return 0
    
    now = time.time()
    cleanup_count = 0
    sessions_to_remove = []
    
    # Find old sessions
    for user_id, session in context.bot_data["sessions"].items():
        # Check if session is older than 7 days
        if now - session.get("last_activity", now) > 604800:  # 7 days in seconds
            sessions_to_remove.append(user_id)
    
    # Remove old sessions
    for user_id in sessions_to_remove:
        del context.bot_data["sessions"][user_id]
        cleanup_count += 1
    
    return cleanup_count

def get_recovery_message(user_data):
    """
    Generate an appropriate recovery message based on user's conversation state.
    
    Args:
        user_data (dict): The user's conversation data
        
    Returns:
        str: Context-appropriate recovery message
    """
    current_location = user_data.get('current_location', '')
    category = user_data.get('category', '')
    
    # Default message
    message = (
        f"{EMOJI['warning']} It looks like your conversation with me may have stalled.\n\n"
        f"This could be due to a temporary issue. Please try again by using one of the options below."
    )
    
    # Customize message based on context
    if category == 'buds':
        message = (
            f"{EMOJI['warning']} It looks like your Premium Buds selection may have stalled.\n\n"
            f"This could be due to a temporary issue. Please try again by using one of the options below."
        )
    elif category == 'carts':
        message = (
            f"{EMOJI['warning']} It looks like your Carts selection may have stalled.\n\n"
            f"This could be due to a temporary issue. Please try again by using one of the options below."
        )
    elif current_location == 'details':
        message = (
            f"{EMOJI['warning']} It looks like you were in the middle of entering shipping details.\n\n"
            f"Would you like to restart the process?"
        )
    elif current_location == 'payment':
        message = (
            f"{EMOJI['warning']} It looks like you were in the middle of submitting a payment.\n\n"
            f"If you already completed your payment, you can track your order with the /track command."
        )
        
    return message

def memory_usage_report() -> Dict[str, Union[int, float]]:
    """
    Get a report of current memory usage.
    
    This function reports system resource usage by the bot process.
    If psutil is not available, returns limited information.
    
    Returns:
        Dict[str, Union[int, float]]: Memory usage statistics
    """
    # Check if psutil is available
    try:
        import psutil
        PSUTIL_AVAILABLE = True
    except ImportError:
        PSUTIL_AVAILABLE = False
    
    if not PSUTIL_AVAILABLE:
        # Return basic information without psutil
        try:
            # Try using the resource module as fallback
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return {
                "memory_usage": usage.ru_maxrss / 1024,  # Convert to MB (system-dependent)
                "user_cpu_time": usage.ru_utime,
                "system_cpu_time": usage.ru_stime,
                "note": "Limited stats (psutil not installed)"
            }
        except (ImportError, AttributeError):
            # If resource module also not available (Windows without psutil)
            return {
                "note": "Memory stats unavailable (psutil not installed)",
                "recommendation": "Install psutil for more detailed system statistics"
            }
            
    # If psutil is available
    import gc
    
    # Force garbage collection
    gc.collect()
    
    # Get current process
    process = psutil.Process(os.getpid())
    
    # Get memory info
    memory_info = process.memory_info()
    
    return {
        "rss": memory_info.rss / 1024 / 1024,  # RSS in MB
        "vms": memory_info.vms / 1024 / 1024,  # VMS in MB
        "percent": process.memory_percent(),
        "num_threads": process.num_threads(),
        "open_files": len(process.open_files()),
    }

async def debug_state_tracking(update, context):
    """
    Middleware-like function to track conversation states.
    Call this at the beginning of key handler functions.
    
    Args:
        update: Telegram update
        context: Conversation context
    """
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    chat_id = update.effective_chat.id if update.effective_chat else "Unknown"
    
    # Get current location from context
    current_location = context.user_data.get("current_location", "Unknown")
    category = context.user_data.get("category", "None")
    
    # Determine what type of update this is
    update_type = "Unknown"
    callback_data = None
    
    if update.message:
        update_type = f"Message: {update.message.text[:20]}..." if update.message.text else "Message (non-text)"
    elif update.callback_query:
        update_type = "Callback Query"
        callback_data = update.callback_query.data
    
    # Log the state
    print(f"DEBUG STATE: User {user_id} | Chat {chat_id} | Location: {current_location} | Category: {category} | Update: {update_type} | Callback: {callback_data}")