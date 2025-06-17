"""
Order handling for the Ganja Paraiso bot.
Handles checkout flow, cart management, and order details.
"""
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ganja_paraiso_bot.utils.ui import (
    create_button, create_button_layout, send_typing_action,
    build_cart_summary, manage_cart
)
from ganja_paraiso_bot.config.emoji import EMOJI
from ganja_paraiso_bot.config.messages import MESSAGES

# Define states for the conversation
from ganja_paraiso_bot.config.constants import (
    CATEGORY, QUANTITY, CONFIRM, DETAILS, CONFIRM_DETAILS, PAYMENT
)

async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle checkout process and get shipping details.
    
    Args:
        update: Telegram update object
        context: Conversation context
    """
    # Handle different update types
    if update.callback_query:
        await update.callback_query.answer()
        chat_id = update.callback_query.message.chat_id
    else:
        chat_id = update.effective_chat.id
    
    # Show typing indicator
    await send_typing_action(context, chat_id)
    
    # Set conversation state
    context.user_data["current_location"] = "details"
    
    # Get cart summary
    cart = context.user_data.get("cart", [])
    if not cart:
        # Empty cart message
        message = MESSAGES["empty_cart"]
        buttons = [[create_button("action", "start_shopping", "Start Shopping")]]
        reply_markup = create_button_layout(buttons)
        
        if update.callback_query:
            await update.callback_query.message.edit_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)
        return CATEGORY
    
    # Display checkout prompt
    checkout_message = MESSAGES["checkout_prompt"]
    buttons = [[create_button("cancel", "cancel", "Cancel Order")]]
    reply_markup = create_button_layout(buttons)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(checkout_message, reply_markup=reply_markup)
    else:
        await update.message.reply_text(checkout_message, reply_markup=reply_markup)
    
    return DETAILS

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Display cart contents.
    
    Args:
        update: Telegram update object
        context: Conversation context
    """
    # Show typing indicator
    chat_id = update.callback_query.message.chat_id
    await send_typing_action(context, chat_id)
    
    # Acknowledge callback
    await update.callback_query.answer()
    
    # Get cart summary
    cart = context.user_data.get("cart", [])
    cart_summary, total_cost = build_cart_summary(cart)
    
    if not cart:
        # Empty cart message
        message = MESSAGES["empty_cart"]
        buttons = [[create_button("action", "start_shopping", "Start Shopping")]]
        reply_markup = create_button_layout(buttons)
        
        await update.callback_query.message.edit_text(message, reply_markup=reply_markup)
        return CATEGORY
    
    # Cart summary message
    message = (
        f"{EMOJI['cart']} Your Cart\n\n"
        f"{cart_summary}\n\n"
        f"What would you like to do?"
    )
    
    # Create buttons
    buttons = [
        [create_button("action", "browse_more", f"{EMOJI['browse']} Add More Items")],
        [create_button("action", "checkout", f"{EMOJI['shipping']} Checkout")],
        [create_button("action", "clear_cart", f"{EMOJI['error']} Clear Cart")]
    ]
    
    reply_markup = create_button_layout(buttons)
    
    await update.callback_query.message.edit_text(message, reply_markup=reply_markup)
    return CONFIRM

async def input_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Process shipping details input.
    
    Args:
        update: Telegram update object
        context: Conversation context
        
    Returns:
        int: Next conversation state
    """
    from ganja_paraiso_bot.utils.validation import validate_shipping_details
    from ganja_paraiso_bot.config.messages import MESSAGES
    
    # Check if we have text input
    if not update.message or not update.message.text:
        # Handle invalid input
        await update.message.reply_text(MESSAGES["invalid_details"])
        return DETAILS
    
    # Get and validate shipping details
    shipping_text = update.message.text
    is_valid, result = validate_shipping_details(shipping_text)
    
    if not is_valid:
        # Invalid details - send error message
        await update.message.reply_text(f"{EMOJI['error']} {result}\n\n{MESSAGES['invalid_details']}")
        return DETAILS
    
    # Store validated shipping details
    context.user_data["shipping_details"] = result
    
    # Show typing indicator
    await send_typing_action(context, update.message.chat_id)
    
    # Get cart summary for confirmation
    cart = context.user_data.get("cart", [])
    cart_summary, total_cost = build_cart_summary(cart)
    
    # Create confirmation message
    confirm_message = (
        f"{EMOJI['shipping']} Shipping Details\n\n"
        f"{EMOJI['customer']} Name: {result['name']}\n"
        f"{EMOJI['address']} Address: {result['address']}\n"
        f"{EMOJI['phone']} Contact: {result['contact']}\n\n"
        f"{cart_summary}\n"
        f"Is this information correct?"
    )
    
    # Create confirmation buttons
    buttons = [
        [create_button("action", "confirm", f"{EMOJI['success']} Confirm")],
        [create_button("action", "edit_details", f"{EMOJI['edit']} Edit Details")],
        [create_button("cancel", "cancel", f"{EMOJI['error']} Cancel")]
    ]
    
    reply_markup = create_button_layout(buttons)
    
    await update.message.reply_text(confirm_message, reply_markup=reply_markup)
    return CONFIRM_DETAILS

async def input_details_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper for input_details to support callback queries."""
    # If this is a callback query for editing details
    if update.callback_query and update.callback_query.data == "edit_details":
        await update.callback_query.answer()
        
        # Show shipping details prompt again
        await update.callback_query.message.edit_text(
            MESSAGES["checkout_prompt"],
            reply_markup=create_button_layout([[create_button("cancel", "cancel", "Cancel Order")]])
        )
        return DETAILS
    
    # Otherwise delegate to regular input_details
    return await input_details(update, context)

async def confirm_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Confirm shipping details and proceed to payment.
    
    Args:
        update: Telegram update object
        context: Conversation context
        
    Returns:
        int: Next conversation state
    """
    from ganja_paraiso_bot.config.constants import GCASH_NUMBER, GCASH_QR_CODE_URL
    
    # Acknowledge callback
    await update.callback_query.answer()
    
    # Set current location
    context.user_data["current_location"] = "payment"
    
    # Show typing indicator
    chat_id = update.callback_query.message.chat_id
    await send_typing_action(context, chat_id)
    
    # Format payment instructions with GCash info
    payment_message = MESSAGES["payment_instructions"].format(GCASH_NUMBER)
    
    # Add payment buttons
    buttons = [
        [create_button("cancel", "cancel_payment", f"{EMOJI['error']} Cancel Payment")]
    ]
    
    reply_markup = create_button_layout(buttons)
    
    # Send QR code image with payment instructions
    try:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=GCASH_QR_CODE_URL,
            caption=payment_message,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        # Fallback to text-only message if image fails
        await update.callback_query.message.edit_text(
            f"{payment_message}\n\n{EMOJI['error']} Failed to load QR code: {str(e)}",
            reply_markup=reply_markup
        )
    
    return PAYMENT

async def cancel_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Cancel the payment process.
    
    Args:
        update: Telegram update object
        context: Conversation context
        
    Returns:
        int: Next conversation state
    """
    # Acknowledge callback
    await update.callback_query.answer()
    
    # Show typing indicator
    chat_id = update.callback_query.message.chat_id
    await send_typing_action(context, chat_id)
    
    # Cancel message
    cancel_message = (
        f"{EMOJI['warning']} Payment Cancelled\n\n"
        f"Your order has been cancelled. You can start over anytime by using the buttons below."
    )
    
    # Create navigation buttons
    buttons = [
        [create_button("action", "start_shopping", f"{EMOJI['cart']} Start Shopping")],
        [create_button("action", "start", f"{EMOJI['home']} Main Menu")]
    ]
    
    reply_markup = create_button_layout(buttons)
    
    await update.callback_query.message.reply_text(cancel_message, reply_markup=reply_markup)
    
    # Clear cart
    if "cart" in context.user_data:
        context.user_data["cart"] = []
    
    return CATEGORY