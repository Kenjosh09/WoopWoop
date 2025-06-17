"""
Payment handling for the Ganja Paraiso bot.
Processes payment screenshots and order creation.
"""
from telegram import Update
from telegram.ext import ContextTypes

from ganja_paraiso_bot.config.emoji import EMOJI
from ganja_paraiso_bot.config.messages import MESSAGES
from ganja_paraiso_bot.utils.ui import create_button, create_button_layout, send_typing_action
from ganja_paraiso_bot.utils.validation import validate_image

# Define states for the conversation
from ganja_paraiso_bot.config.constants import PAYMENT, TRACKING

async def handle_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Process payment screenshot and create order.
    
    Args:
        update: Telegram update object
        context: Conversation context
        
    Returns:
        int: Next conversation state
    """
    from ganja_paraiso_bot.main import order_manager, loggers
    
    # Must have a photo
    if not update.message or not update.message.photo:
        await update.message.reply_text(MESSAGES["invalid_payment"])
        return PAYMENT
    
    # Show typing indicator
    await send_typing_action(context, update.message.chat_id)
    
    # Get the photo with highest resolution
    photo = update.message.photo[-1]
    
    # Download the photo as bytes
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()
    
    # Validate image format and size
    is_valid, validation_message = validate_image(photo_bytes)
    
    if not is_valid:
        await update.message.reply_text(
            f"{EMOJI['error']} {validation_message}\n\nPlease send a valid payment screenshot."
        )
        return PAYMENT
    
    # Set status message while processing
    status_message = await update.message.reply_text(
        f"{EMOJI['clock']} Processing your payment screenshot..."
    )
    
    # Upload screenshot to Google Drive
    try:
        from ganja_paraiso_bot.main import google_apis
        
        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"payment_{timestamp}.jpg"
        
        # Upload to Google Drive
        payment_url = await google_apis.upload_payment_screenshot(photo_bytes, filename)
        
        # Create the order
        order_id = await order_manager.create_order(context, context.user_data, payment_url)
        
        if not order_id:
            # Order creation failed
            await status_message.edit_text(
                f"{EMOJI['error']} Failed to create your order. Please try again or contact support."
            )
            return PAYMENT
        
        # Store order ID in user data
        context.user_data["current_order_id"] = order_id
        
        # Format confirmation message
        confirmation = MESSAGES["order_confirmation"].format(order_id)
        
        # Create order success buttons
        buttons = [
            [create_button("action", "track_order", f"{EMOJI['tracking']} Track Order")],
            [create_button("action", "start", f"{EMOJI['home']} Main Menu")]
        ]
        
        reply_markup = create_button_layout(buttons)
        
        # Update status message with success
        await status_message.edit_text(confirmation, reply_markup=reply_markup)
        
        # Clear cart after successful order
        if "cart" in context.user_data:
            context.user_data["cart"] = []
        
        # Return to conversation end
        return -1  # End conversation
        
    except Exception as e:
        # Log the error
        loggers["errors"].error(f"Payment processing error: {str(e)}")
        
        # Update status message with error
        await status_message.edit_text(
            f"{EMOJI['error']} {MESSAGES['payment_processing']}\n\n"
            f"Technical details: {str(e)}\n\n"
            f"Please try again or contact support."
        )
        
        # Stay in payment state
        return PAYMENT