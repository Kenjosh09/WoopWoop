"""
Order tracking handlers for the Ganja Paraiso bot.
"""
from telegram import Update
from telegram.ext import ContextTypes

from ganja_paraiso_bot.config.emoji import EMOJI
from ganja_paraiso_bot.config.messages import MESSAGES
from ganja_paraiso_bot.utils.ui import (
    create_button, create_button_layout, send_typing_action, get_common_buttons
)
from ganja_paraiso_bot.utils.validation import is_valid_order_id

# Define states for the conversation
from ganja_paraiso_bot.config.constants import TRACKING

async def track_order_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Entry point for order tracking.
    
    Args:
        update: Telegram update object
        context: Conversation context
        
    Returns:
        int: Next conversation state
    """
    # Set current location
    context.user_data["current_location"] = "tracking"
    
    # Handle different update types
    if update.callback_query:
        await update.callback_query.answer()
        chat_id = update.callback_query.message.chat_id
    else:
        chat_id = update.effective_chat.id
    
    # Show typing indicator
    await send_typing_action(context, chat_id)
    
    # Get recent orders for this user to show as quick options
    user_id = update.effective_user.id
    
    # TODO: Implement get_user_orders to fetch recent orders from Google Sheets
    # For now, just use a placeholder
    recent_orders = []
    
    if recent_orders:
        # Display recent orders for quick selection
        recent_message = (
            f"{EMOJI['tracking']} Track Your Orders\n\n"
            f"Select an order to track or enter your Order ID manually:"
        )
        
        # Create buttons for recent orders
        buttons = []
        for order in recent_orders[:5]:  # Show at most 5 recent orders
            order_id = order.get("order_id", "Unknown")
            order_date = order.get("date", "Unknown date")
            buttons.append(
                [create_button("action", f"order_{order_id}", f"Order {order_id} ({order_date})")]
            )
        
        # Add option to enter order ID manually
        buttons.append([create_button("action", "enter_order_id", "Enter Order ID Manually")])
        buttons.append([create_button("action", "start", "Back to Main Menu")])
        
        reply_markup = create_button_layout(buttons)
        
        if update.callback_query:
            await update.callback_query.message.edit_text(recent_message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(recent_message, reply_markup=reply_markup)
            
    else:
        # No recent orders, ask for order ID directly
        tracking_message = MESSAGES["tracking_prompt"]
        
        buttons = [
            [create_button("action", "cancel_tracking", "Cancel")]
        ]
        
        reply_markup = create_button_layout(buttons)
        
        if update.callback_query:
            await update.callback_query.message.edit_text(tracking_message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(tracking_message, reply_markup=reply_markup)
    
    return TRACKING

async def get_order_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Process order ID input and show tracking information.
    
    Args:
        update: Telegram update object
        context: Conversation context
        
    Returns:
        int: Next conversation state
    """
    from ganja_paraiso_bot.main import order_manager
    
    # Handle different input types
    order_id = None
    
    if update.callback_query:
        # Extract order ID from callback data
        await update.callback_query.answer()
        callback_data = update.callback_query.data
        
        if callback_data.startswith("order_"):
            order_id = callback_data.replace("order_", "")
            
            # Show typing indicator
            chat_id = update.callback_query.message.chat_id
            await send_typing_action(context, chat_id)
    elif update.message and update.message.text:
        # Get order ID from text input
        order_id = update.message.text.strip()
        
        # Show typing indicator
        chat_id = update.message.chat_id
        await send_typing_action(context, chat_id)
    
    if not order_id or not is_valid_order_id(order_id):
        # Invalid order ID
        error_message = MESSAGES["tracking_not_found"]
        
        # Create buttons
        buttons = [
            [create_button("action", "track_order", "Try Again")],
            [create_button("action", "start", "Back to Main Menu")]
        ]
        
        reply_markup = create_button_layout(buttons)
        
        if update.callback_query:
            await update.callback_query.message.edit_text(error_message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(error_message, reply_markup=reply_markup)
            
        return TRACKING
    
    # Store the order ID in context
    context.user_data["current_order_id"] = order_id
    
    # Get order status
    status, tracking_link, error = await order_manager.get_order_status(order_id)
    
    if error:
        # Error retrieving order status
        error_message = f"{EMOJI['error']} {error}"
        
        buttons = [
            [create_button("action", "track_order", "Try Again")],
            [create_button("action", "start", "Back to Main Menu")]
        ]
        
        reply_markup = create_button_layout(buttons)
        
        if update.callback_query:
            await update.callback_query.message.edit_text(error_message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(error_message, reply_markup=reply_markup)
            
        return TRACKING
    
    # Get formatted status message
    from ganja_paraiso_bot.utils.helpers import get_status_message
    status_emoji, status_description = get_status_message(status, tracking_link)
    
    # Create order status message
    order_message = (
        f"{EMOJI['shipping']} Order Status: {order_id}\n\n"
        f"Status: {status_emoji} {status}\n\n"
        f"{status_description}"
    )
    
    # Add tracking link if available
    if tracking_link:
        order_message += f"\n\n{EMOJI['tracking']} [Track your delivery here]({tracking_link})"
    
    # Create tracking buttons
    buttons = get_common_buttons("tracking_options", order_id)
    reply_markup = create_button_layout(buttons)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            order_message, 
            reply_markup=reply_markup,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    else:
        await update.message.reply_text(
            order_message,
            reply_markup=reply_markup,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    
    return TRACKING

async def refresh_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Refresh tracking information for an order.
    
    Args:
        update: Telegram update object
        context: Conversation context
        
    Returns:
        int: Next conversation state
    """
    # Extract order ID from callback data
    callback_data = update.callback_query.data
    order_id = callback_data.replace("refresh_tracking_", "")
    
    # Update the current order ID in context
    context.user_data["current_order_id"] = order_id
    
    # Use get_order_id to show updated tracking info
    return await get_order_id(update, context)

async def cancel_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Cancel order tracking.
    
    Args:
        update: Telegram update object
        context: Conversation context
        
    Returns:
        int: Next conversation state
    """
    # Acknowledge callback if applicable
    if update.callback_query:
        await update.callback_query.answer()
        
    # Show typing indicator
    chat_id = update.effective_chat.id
    await send_typing_action(context, chat_id)
    
    # Create message
    cancel_message = (
        f"{EMOJI['info']} Order tracking cancelled.\n\n"
        f"What would you like to do next?"
    )
    
    # Create navigation buttons
    buttons = [
        [create_button("action", "start_shopping", f"{EMOJI['cart']} Start Shopping")],
        [create_button("action", "start", f"{EMOJI['home']} Main Menu")]
    ]
    
    reply_markup = create_button_layout(buttons)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(cancel_message, reply_markup=reply_markup)
    else:
        await update.message.reply_text(cancel_message, reply_markup=reply_markup)
    
    # End the conversation
    return -1