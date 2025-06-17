"""
Message templates and text content for the Ganja Paraiso bot.
"""
from ganja_paraiso_bot.config.emoji import EMOJI
from ganja_paraiso_bot.config.status import STATUS

# Message Templates
MESSAGES = {
    "welcome": f"{EMOJI['welcome']} Mabuhigh! Welcome to Ganja Paraiso! What would you like to order today?",
    
    "order_added": f"{EMOJI['success']} Item added to your cart. What would you like to do next?",
    
    "checkout_prompt": (
        f"{EMOJI['cart']} Please enter your shipping details (Name / Address / Contact Number).\n\n"
        f"{EMOJI['info']} Example: Juan Dela Cruz / 123 Main St, City / 09171234567\n\n"
        "Please provide the correct information to proceed."
    ),
    
    "payment_instructions": (
    f"{EMOJI['payment']} Please send a screenshot of your payment to complete the order.\n\n"
    f"{EMOJI['money']} Send payment to GCash: {{}}\n\n"
    f"{EMOJI['qrcode']} Scan this QR code for faster payment:\n"
    f"[QR Code will appear here]\n\n"
    f"{EMOJI['info']} <b>Note: If you're using the desktop app of Telegram, please select "
    "the option to compress the image when uploading or pasting your payment screenshot.</b>\n\n"
    f"{EMOJI['success']} We will review your payment and proceed with processing your order."
    ),
    
    "order_confirmation": (
        f"{EMOJI['success']} Payment screenshot received! Your order ID is: {{}}\n\n"
        "We will review it shortly and process your order. You can check the status "
        "of your order anytime using the /track command."
    ),
    
    "invalid_format": f"{EMOJI['error']} Invalid format. Please try again using the correct format.",
    
    "cancel_order": f"{EMOJI['warning']} Order cancelled. You can start over anytime by typing /start.",
    
    "empty_cart": f"{EMOJI['cart']} Your cart is empty. Please add items before continuing.",
    
    "invalid_details": (
        f"{EMOJI['error']} Invalid shipping details. Please use the format:\n\n"
        "Name / Address / Contact Number\n\n"
        f"{EMOJI['success']} Example: Juan Dela Cruz / 123 Main St, City / 09171234567\n\n"
        "Please provide the correct information to proceed."
    ),
    
    "invalid_payment": f"{EMOJI['error']} Please send a valid payment screenshot.",
    
    "admin_welcome": (
        f"{EMOJI['admin']} Welcome to the Admin Panel\n\n"
        "From here, you can manage orders, update statuses, handle inventory, and process payments."
    ),
    
    "not_authorized": f"{EMOJI['error']} You are not authorized to access this feature.",
    
    "order_not_found": f"{EMOJI['error']} Order {{}} not found.",
    
    "status_updated": f"{EMOJI['success']} Status updated to '{{}}' for Order {{}}.",
    
    "tracking_updated": f"{EMOJI['success']} Tracking link has been updated for Order {{}}.",
    
    "error": f"{EMOJI['error']} An unexpected error occurred. Please try again later.",
    
    "tracking_prompt": (
        f"{EMOJI['tracking']} Please enter your Order ID to track your order:\n\n"
        "Example: WW-1234-ABC"
    ),
    
    "order_status_heading": f"{EMOJI['shipping']} Order Status Update"
}

# Error Messages
ERRORS = {
    "payment_processing": f"{EMOJI['error']} We had trouble processing your payment. Please try again.",
    
    "invalid_quantity": f"{EMOJI['warning']} Please enter a valid quantity.",
    
    "minimum_order": f"{EMOJI['info']} Minimum order for {{}} is {{}} {{}}.",
    
    "invalid_category": f"{EMOJI['error']} Invalid category or suboption. Please try again.",
    
    "network_error": f"{EMOJI['error']} Network connection issue. Please try again later.",
    
    "timeout": f"{EMOJI['time']} Your session has timed out for security reasons. Please start again with /start.",
    
    "not_authorized": f"{EMOJI['error']} You are not authorized to use this feature.",
    
    "update_failed": f"{EMOJI['error']} Failed to update status for Order {{}}.",
    
    "no_screenshot": f"{EMOJI['error']} Payment screenshot not found for this order.",
    
    "tracking_not_found": (
        f"{EMOJI['error']} Order ID not found. Please check your Order ID and try again.\n\n"
        "If you continue having issues, please contact customer support."
    )
}