"""
Error handling middleware for the Ganja Paraiso bot.
"""
import html
import json
import traceback
from typing import Dict, Any

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ganja_paraiso_bot.config.emoji import EMOJI
from ganja_paraiso_bot.config.constants import ADMIN_ID

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Global error handler to catch and log exceptions.
    Also notifies admin of critical errors.
    
    Args:
        update: Update that caused the error
        context: Context with error information
    """
    # Get logger from context data if available
    logger = context.bot_data.get("loggers", {}).get("errors")
    
    # Get the exception info
    error = context.error
    
    # Log the error
    if logger:
        logger.error(f"Exception while handling an update: {error}", exc_info=context.error)
    else:
        # Fallback if logger not available
        print(f"Exception while handling an update: {error}")
    
    # Create error message for admin
    tb_list = traceback.format_exception(None, error, error.__traceback__)
    tb_string = "".join(tb_list)
    
    # Basic information about the update
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    
    # Clean sensitive data for the admin message
    cleaned_update = clean_sensitive_data(update_str)
    
    # Create message for admin
    admin_message = (
        f"{EMOJI['alert']} <b>Error Report</b>\n\n"
        f"<b>Error:</b> {html.escape(str(error))}\n\n"
        f"<b>Update:</b> {html.escape(json.dumps(cleaned_update, indent=2, ensure_ascii=False))}\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )
    
    # Notify admin for serious errors
    try:
        # Only notify if it's a significant error
        if is_significant_error(error):
            # Limit message length to avoid API errors
            if len(admin_message) > 4000:
                admin_message = admin_message[:3900] + "...\n[truncated]</pre>"
                
            # Send to admin
            await context.bot.send_message(
                chat_id=ADMIN_ID, 
                text=admin_message,
                parse_mode=ParseMode.HTML
            )
    except Exception:
        # If we can't send to admin, just log it
        if logger:
            logger.error("Failed to notify admin about error")
    
    # Try to handle the error gracefully for the user
    try:
        if update and update.effective_message:
            # For users, send a simple error message
            user_message = (
                f"{EMOJI['error']} Something went wrong.\n\n"
                "The issue has been reported to the administrator. "
                "Please try again later or use /start to restart."
            )
            
            await update.effective_message.reply_text(user_message)
    except Exception:
        # Fail silently
        pass


def is_significant_error(error: Exception) -> bool:
    """
    Determines if an error is significant enough to notify the admin.
    Filters out common non-critical errors.
    
    Args:
        error: The exception to check
        
    Returns:
        bool: True if significant, False otherwise
    """
    error_text = str(error)
    
    # List of common non-critical errors
    ignored_patterns = [
        "Forbidden: bot was blocked by the user",
        "Message is not modified",
        "Message to delete not found",
        "Can't parse entities",
        "Message to edit not found",
        "Query is too old",
        "Have no rights to send a message"
    ]
    
    # Check if it's one of the ignorable errors
    for pattern in ignored_patterns:
        if pattern in error_text:
            return False
    
    # Otherwise, it's significant
    return True


def clean_sensitive_data(data) -> Dict[str, Any]:
    """
    Clean sensitive data from error reports.
    
    Args:
        data: Raw error data
        
    Returns:
        dict: Cleaned data
    """
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            # Skip potentially sensitive keys
            if key in ["phone_number", "email", "address", "credit_card"]:
                cleaned[key] = "[REDACTED]"
            # Recursively clean nested dictionaries
            elif isinstance(value, dict):
                cleaned[key] = clean_sensitive_data(value)
            # Clean text fields that might contain personal data
            elif key in ["text", "caption"] and isinstance(value, str):
                # Keep the first few characters
                if len(value) > 10:
                    cleaned[key] = value[:10] + "..." 
                else:
                    cleaned[key] = value
            # Keep other values as is
            else:
                cleaned[key] = value
        return cleaned
    elif isinstance(data, list):
        return [clean_sensitive_data(item) if isinstance(item, (dict, list)) else item 
                for item in data]
    else:
        # Try to convert string representation of dict back to dict
        try:
            if isinstance(data, str) and data.startswith("{") and data.endswith("}"):
                dict_data = json.loads(data)
                return clean_sensitive_data(dict_data)
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # Return original data if not a container or parsable json string
        return data