"""
Start command and welcome handlers for the Ganja Paraiso bot.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ganja_paraiso_bot.config.emoji import EMOJI
from ganja_paraiso_bot.config.messages import MESSAGES
from ganja_paraiso_bot.utils.ui import create_button, create_button_layout, send_typing_action

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /start command and display the welcome message.
    
    Args:
        update: Telegram update object
        context: Conversation context
    """
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name
    
    # Store user ID and username in user_data
    context.user_data["user_id"] = user_id
    context.user_data["username"] = username
    
    # Set current location
    context.user_data["current_location"] = "start"
    
    # Show typing indicator for natural UX
    await send_typing_action(context, update.effective_chat.id)
    
    # Create welcome buttons
    buttons = [
        [create_button("action", "start_shopping", f"{EMOJI['cart']} Start Shopping")],
        [create_button("action", "track_order", f"{EMOJI['tracking']} Track My Order")],
        [create_button("action", "contact_support", f"{EMOJI['support']} Contact Support")]
    ]
    
    reply_markup = create_button_layout(buttons)
    
    # Send welcome message
    await update.message.reply_text(
        MESSAGES["welcome"],
        reply_markup=reply_markup
    )

async def handle_start_shopping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the "Start Shopping" button click.
    
    Args:
        update: Telegram update object
        context: Conversation context
    """
    # Clear any existing cart
    if "cart" in context.user_data:
        context.user_data["cart"] = []
    
    # Show typing indicator
    callback_query = update.callback_query
    chat_id = callback_query.message.chat_id
    await send_typing_action(context, chat_id)
    
    # Acknowledge the callback
    await callback_query.answer()
    
    # Forward to choose_category handler
    from ganja_paraiso_bot.handlers.browsing import choose_category_wrapper
    await choose_category_wrapper(update, context)

async def restart_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Restart the conversation from the beginning.
    
    Args:
        update: Telegram update object
        context: Conversation context
    """
    # Clear conversation data but keep user identification
    user_id = context.user_data.get("user_id")
    username = context.user_data.get("username")
    
    # Reset user data
    context.user_data.clear()
    
    # Restore user identification
    context.user_data["user_id"] = user_id
    context.user_data["username"] = username
    
    # Show typing indicator
    chat_id = update.effective_chat.id
    await send_typing_action(context, chat_id)
    
    # Create restart message
    restart_message = f"{EMOJI['restart']} Your session has been reset. What would you like to do?"
    
    # Create welcome buttons
    buttons = [
        [create_button("action", "start_shopping", f"{EMOJI['cart']} Start Shopping")],
        [create_button("action", "track_order", f"{EMOJI['tracking']} Track My Order")],
        [create_button("action", "contact_support", f"{EMOJI['support']} Contact Support")]
    ]
    
    reply_markup = create_button_layout(buttons)
    
    # Handle different types of updates
    if update.callback_query:
        # Acknowledge the callback
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            restart_message,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            restart_message,
            reply_markup=reply_markup
        )

async def contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the "Contact Support" button click.
    
    Args:
        update: Telegram update object
        context: Conversation context
    """
    from ganja_paraiso_bot.config.constants import SUPPORT_ADMIN_USERNAME
    from ganja_paraiso_bot.utils.helpers import get_support_deep_link
    
    # Show typing indicator
    chat_id = update.effective_chat.id
    await send_typing_action(context, chat_id)
    
    user_id = update.effective_user.id
    
    # Get any active order ID
    current_order = context.user_data.get("current_order_id", "Unknown")
    
    # Create support link
    support_link = get_support_deep_link(user_id, current_order)
    
    # Create support message
    support_message = (
        f"{EMOJI['support']} Need help with your order?\n\n"
        f"You can contact our support team directly via Telegram.\n\n"
        f"Your User ID: {user_id}\n"
        f"{f'Your Order ID: {current_order}' if current_order != 'Unknown' else 'No active order'}\n\n"
        f"Please include this information in your message."
    )
    
    # Create support buttons
    buttons = [
        [InlineKeyboardButton(f"{EMOJI['phone']} Contact Support", url=support_link)],
        [create_button("action", "start", f"{EMOJI['home']} Back to Main Menu")]
    ]
    
    reply_markup = create_button_layout(buttons)
    
    # Handle different types of updates
    if update.callback_query:
        # Acknowledge the callback
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            support_message,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            support_message,
            reply_markup=reply_markup
        )

async def get_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Display help information based on current conversation state.
    
    Args:
        update: Telegram update object
        context: Conversation context
    """
    # Show typing indicator
    chat_id = update.effective_chat.id
    await send_typing_action(context, chat_id)
    
    # Get current location
    current_location = context.user_data.get("current_location", "start")
    
    # Create context-sensitive help message
    help_message = f"{EMOJI['help']} Help\n\n"
    
    if current_location == "category":
        help_message += (
            "You're currently selecting a product category.\n\n"
            "Each category has different products:\n"
            f"• {EMOJI['buds']} Premium Buds - High-quality cannabis flowers\n"
            f"• {EMOJI['local']} Local (BG) - Budget-friendly options\n"
            f"• {EMOJI['carts']} Carts/Disposables - Pre-filled vape cartridges\n"
            f"• {EMOJI['edibles']} Edibles - Cannabis-infused food products\n\n"
            "Just tap any category to see the available products."
        )
    elif current_location == "strain_selection":
        help_message += (
            "You're currently selecting a cannabis strain type.\n\n"
            "Different strains have different effects:\n"
            "• Indica - More relaxing, physical effects\n"
            "• Sativa - More energizing, mental effects\n"
            "• Hybrid - Balanced combination of both\n\n"
            "Tap any strain to see available products."
        )
    elif current_location == "product_selection":
        help_message += (
            "You're currently selecting a specific product.\n\n"
            "Each product shows:\n"
            "• Name and description\n"
            "• Price per unit\n"
            "• Current availability\n\n"
            "Tap a product to select it and proceed to quantity selection."
        )
    elif current_location == "quantity":
        help_message += (
            "You're currently entering a quantity for your selected product.\n\n"
            "You can either:\n"
            "• Use the preset buttons for common quantities, or\n"
            "• Type a custom quantity\n\n"
            "Some products have minimum order quantities."
        )
    elif current_location == "details":
        help_message += (
            "You need to enter your shipping details in this format:\n\n"
            "Name / Address / Contact Number\n\n"
            "For example:\n"
            "Juan Dela Cruz / 123 Main St, City / 09171234567\n\n"
            "This information is needed for proper delivery."
        )
    elif current_location == "payment":
        help_message += (
            "You need to send a screenshot of your payment.\n\n"
            "Steps:\n"
            "1. Make the payment via GCash to the number provided\n"
            "2. Take a screenshot showing the transaction details\n"
            "3. Send the screenshot here\n\n"
            "We'll review your payment and process your order."
        )
    else:
        # Default help
        help_message += (
            "Welcome to Ganja Paraiso! Here are the main commands:\n\n"
            "/start - Begin shopping or access main menu\n"
            "/track - Track your existing order\n"
            "/help - Display this help message\n"
            "/cancel - Cancel the current operation\n\n"
            "If you need further assistance, use the Contact Support option."
        )
    
    # Create buttons
    buttons = [
        [create_button("action", "start", f"{EMOJI['home']} Back to Main Menu")],
        [create_button("action", "contact_support", f"{EMOJI['support']} Contact Support")]
    ]
    
    reply_markup = create_button_layout(buttons)
    
    # Handle different types of updates
    if update.callback_query:
        # Acknowledge the callback
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            help_message,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            help_message,
            reply_markup=reply_markup
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Cancel the current operation and return to the main menu.
    
    Args:
        update: Telegram update object
        context: Conversation context
    """
    # Show typing indicator
    chat_id = update.effective_chat.id
    await send_typing_action(context, chat_id)
    
    # Clear cart
    if "cart" in context.user_data:
        context.user_data["cart"] = []
    
    # Create cancel message
    cancel_message = MESSAGES["cancel_order"]
    
    # Create buttons for main menu
    buttons = [
        [create_button("action", "start", f"{EMOJI['home']} Back to Main Menu")]
    ]
    
    reply_markup = create_button_layout(buttons)
    
    # Handle different types of updates
    if update.callback_query:
        # Acknowledge the callback
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            cancel_message,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            cancel_message,
            reply_markup=reply_markup
        )
    
    # Return to conversation start
    return -1  # End current conversation