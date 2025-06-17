"""
Admin command handlers for the Ganja Paraiso bot.
"""
from telegram import Update
from telegram.ext import ContextTypes

from ganja_paraiso_bot.config.emoji import EMOJI
from ganja_paraiso_bot.config.constants import ADMIN_ID, SUPPORT_ADMIN_USERNAME

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Reset user conversation state (admin command).
    
    Args:
        update: Telegram update object
        context: Conversation context
    """
    from ganja_paraiso_bot.handlers.start import restart_conversation
    
    # Reset user data
    await restart_conversation(update, context)
    
    # Add admin-specific message
    await update.message.reply_text(
        f"{EMOJI['success']} User session has been reset successfully."
    )

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Provide support information.
    
    Args:
        update: Telegram update object
        context: Conversation context
    """
    support_message = (
        f"{EMOJI['support']} Support Information\n\n"
        f"For any issues or questions about your order, please contact:\n\n"
        f"Telegram: @{SUPPORT_ADMIN_USERNAME}\n"
        f"Working hours: 9 AM - 9 PM daily\n\n"
        f"When contacting support, please provide your order ID if available."
    )
    
    await update.message.reply_text(support_message)