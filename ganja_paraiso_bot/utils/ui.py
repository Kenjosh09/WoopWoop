"""
UI components and builders for Telegram bot interface elements.
"""
import asyncio
from typing import List, Union, Optional, Tuple

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Message, 
    ParseMode
)
from telegram.ext import ContextTypes

from ganja_paraiso_bot.config.emoji import EMOJI
from ganja_paraiso_bot.config.products import PRODUCTS

async def send_typing_action(context, chat_id, seconds=1):
    """
    Send a typing indicator to the user to show the bot is processing.
    
    Args:
        context: Conversation context containing the bot
        chat_id (int): Chat ID to send typing indicator to
        seconds (float): How long to show typing for
    """
    try:
        # Send typing action
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        # If more than minimal typing time is requested, sleep
        if seconds > 0.5:
            await asyncio.sleep(seconds)
    except Exception:
        # Silently ignore errors with typing indicator
        pass

def create_button(button_type, callback_data=None, custom_text=None, url=None):
    """
    Factory function to create common button types with consistent styling.
    
    Args:
        button_type (str): Type of button ('back', 'action', 'status', etc.)
        callback_data (str, optional): Callback data for the button
        custom_text (str, optional): Custom button text
        url (str, optional): URL for link buttons
    
    Returns:
        InlineKeyboardButton: Configured button with appropriate text and callback
    """
    if button_type == "back":
        destination = callback_data.replace("back_to_", "") if callback_data else "previous"
        destination_text = destination.replace("_", " ").title()
        text = f"{EMOJI['back']} Back to {destination_text}" if not custom_text else f"{EMOJI['back']} {custom_text}"
        return InlineKeyboardButton(text, callback_data=callback_data or "back")
        
    elif button_type == "action":
        # Extract emoji key from callback data if possible
        emoji_key = callback_data.split("_")[0] if callback_data and "_" in callback_data else callback_data
        emoji = EMOJI.get(emoji_key, EMOJI.get("info", "ℹ️"))
        text = f"{emoji} {custom_text}" if custom_text else f"{emoji} {callback_data.replace('_', ' ').title()}"
        return InlineKeyboardButton(text, callback_data=callback_data)
        
    elif button_type == "link":
        if not url:
            raise ValueError("URL is required for link buttons")
        emoji = EMOJI.get("link", "🔗")
        text = f"{emoji} {custom_text}" if custom_text else f"{emoji} Link"
        return InlineKeyboardButton(text, url=url)
        
    elif button_type == "cancel":
        text = f"{EMOJI['error']} {custom_text}" if custom_text else f"{EMOJI['error']} Cancel"
        return InlineKeyboardButton(text, callback_data=callback_data or "cancel")
    
    # Default case - generic button
    return InlineKeyboardButton(custom_text or "Button", callback_data=callback_data or "generic")

def create_button_layout(buttons, columns=1):
    """
    Create a standardized button layout with specified number of columns.
    
    Args:
        buttons (list): List of InlineKeyboardButton objects or lists of buttons
        columns (int): Number of buttons per row
    
    Returns:
        InlineKeyboardMarkup: Formatted keyboard markup
    """
    keyboard = []
    
    # If buttons already contains rows (nested lists), use them directly
    if buttons and isinstance(buttons[0], list):
        keyboard = buttons
    else:
        # Create rows based on columns specification
        row = []
        for idx, button in enumerate(buttons):
            row.append(button)
            if (idx + 1) % columns == 0:
                keyboard.append(row)
                row = []
        
        # Add any remaining buttons
        if row:
            keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

def get_navigation_buttons(current_location=None, include_home=True, include_help=True, custom_back=None):
    """
    Get appropriate navigation buttons based on current location.
    
    Args:
        current_location (str, optional): Current conversation location
        include_home (bool): Whether to include main menu button
        include_help (bool): Whether to include help button
        custom_back (tuple, optional): Custom back button (text, callback_data)
    
    Returns:
        list: List of InlineKeyboardButton objects
    """
    buttons = []
    
    # Add context-specific back button
    if custom_back:
        buttons.append(InlineKeyboardButton(
            f"{EMOJI['back']} {custom_back[0]}", 
            callback_data=custom_back[1]
        ))
    elif current_location:
        # Standard back buttons based on location
        if "product_" in current_location:
            buttons.append(create_button("back", "back_to_browse", "Back to Browse"))
        elif current_location == "strain_selection":
            buttons.append(create_button("back", "back_to_categories", "Back to Categories"))
        elif current_location == "browse_carts_by":
            buttons.append(create_button("back", "back_to_categories", "Back to Categories"))
        elif current_location == "admin_orders":
            buttons.append(create_button("back", "back_to_admin", "Back to Admin Panel"))
    
    # Add home button if requested
    if include_home:
        buttons.append(InlineKeyboardButton(f"{EMOJI['home']} Main Menu", callback_data="start"))
    
    # Add help button if requested
    if include_help:
        buttons.append(InlineKeyboardButton(f"{EMOJI['help']} Help", callback_data="get_help"))
    
    return buttons

def get_common_buttons(button_type, context_data=None):
    """
    Get common button groups used throughout the application.
    
    Args:
        button_type (str): Type of button group ('order_actions', 'confirm_cancel', etc.)
        context_data (dict, optional): Additional context data for customizing buttons
    
    Returns:
        list: List of InlineKeyboardButton objects or rows
    """
    if button_type == "confirm_cancel":
        # Confirm and cancel buttons
        return [
            [create_button("action", "confirm", "Confirm")],
            [create_button("cancel", "cancel", "Cancel")]
        ]
    
    elif button_type == "order_actions":
        # Order action buttons
        return [
            [create_button("action", "add_more", "Add More", f"{EMOJI['cart']} Add More")],
            [create_button("action", "proceed", "Proceed to Checkout", f"{EMOJI['shipping']} Proceed to Checkout")],
            [create_button("cancel", "cancel", "Cancel Order")]
        ]
    
    elif button_type == "restart_home":
        # Restart and home buttons
        return [
            [create_button("action", "restart_conversation", "Reset Session", f"{EMOJI['restart']} Reset Session")],
            [create_button("action", "start", "Main Menu", f"{EMOJI['home']} Main Menu")]
        ]
    
    elif button_type == "strain_buttons":
        # Strain selection buttons
        return [
            [InlineKeyboardButton("🌿 Indica", callback_data="indica")],
            [InlineKeyboardButton("🌱 Sativa", callback_data="sativa")],
            [InlineKeyboardButton("🍃 Hybrid", callback_data="hybrid")],
            [create_button("back", "back_to_categories", "Back to Categories")]
        ]
    
    elif button_type == "tracking_options":
        # Tracking options (with optional order id as context)
        order_id = context_data
        buttons = []
        
        if order_id:
            buttons.append([InlineKeyboardButton(f"{EMOJI['restart']} Refresh Status", 
                               callback_data=f"refresh_tracking_{order_id}")])
        
        buttons.extend([
            [InlineKeyboardButton(f"{EMOJI['support']} Contact Support", 
                               callback_data="contact_support")],
            [InlineKeyboardButton(f"{EMOJI['home']} Main Menu", 
                               callback_data="start")]
        ])
        
        return buttons
    
    # Default empty button list
    return []

def build_category_buttons(available_categories):
    """
    Build inline keyboard with available product category buttons.
    
    Args:
        available_categories (list): List of available category IDs
        
    Returns:
        InlineKeyboardMarkup: Keyboard with product category buttons
    """
    buttons = []
    
    # Debug print to verify available categories
    print(f"DEBUG: Building category buttons for: {available_categories}")
    
    for product_id in available_categories:
        if product_id in PRODUCTS:
            product = PRODUCTS[product_id]
            button_text = f"{product['emoji']} {product['name']}"
            
            buttons.append([InlineKeyboardButton(button_text, callback_data=product_id)])
    
    # Add cancel button
    buttons.append([create_button("cancel", "cancel", "Cancel")])
    
    return InlineKeyboardMarkup(buttons)

def build_admin_buttons():
    """
    Build inline keyboard with admin panel options.
    
    Returns:
        InlineKeyboardMarkup: Keyboard with admin options
    """
    buttons = [
        [create_button("action", "view_orders", f"{EMOJI['list']} View All Orders")],
        [create_button("action", "search_order", f"{EMOJI['search']} Search Order by ID")],
        [create_button("action", "manage_inventory", f"{EMOJI['inventory']} Manage Inventory")],
        [create_button("action", "approve_payments", f"{EMOJI['review']} Review Payments")]
    ]
    
    return InlineKeyboardMarkup(buttons)

def build_cart_summary(cart):
    """
    Build a formatted summary of the cart contents.
    
    Args:
        cart (list): List of cart items
        
    Returns:
        tuple: (summary_text, total_cost)
    """
    # If the cart is empty, return a message indicating so
    if not cart:
        return f"{EMOJI['cart']} Your cart is empty.\n", 0

    # Initialize the summary string and total cost
    summary = f"{EMOJI['cart']} Your Cart:\n\n"
    total_cost = 0

    # Loop through each item in the cart to generate a detailed summary
    for item in cart:
        category = item.get("category", "Unknown")
        suboption = item.get("suboption", "Unknown")
        quantity = item.get("quantity", 0)
        total_price = item.get("total_price", 0)
        unit = PRODUCTS.get(category.lower(), {}).get("unit", "units")
        total_cost += total_price  # Accumulate the total cost
        
        # Check if there's discount information available
        regular_price = item.get("regular_price")
        discount_info = item.get("discount_info", "")
        
        # Add the item details to the summary, with discount if applicable
        if category.lower() == "local" and regular_price:
            summary += (
                f"- {category} ({suboption}): {quantity} {unit}\n"
                f"  Regular Price: ₱{regular_price:,.0f}\n"
                f"  Discounted Price: ₱{total_price:,.0f} {discount_info}\n"
            )
        else:
            summary += f"- {category} ({suboption}): {quantity} {unit} - ₱{total_price:,.0f}\n"

    # Add the total cost to the summary
    summary += f"\n{EMOJI['money']} Total Cost: ₱{total_cost:,.0f}\n"

    return summary, total_cost

def manage_cart(context, action, item=None):
    """
    Manage the user's shopping cart.
    
    Args:
        context: The conversation context
        action (str): Action to perform ('add', 'get', 'clear')
        item (dict, optional): Item to add to cart
        
    Returns:
        list: The current cart after the operation
    """
    if "cart" not in context.user_data:
        context.user_data["cart"] = []
        
    if action == "add" and item:
        context.user_data["cart"].append(item)
    elif action == "clear":
        context.user_data["cart"] = []
        
    return context.user_data["cart"]

def convert_gdrive_url_to_direct_link(url):
    """
    Convert a Google Drive sharing URL to a direct download link suitable for images.
    
    Args:
        url (str): Google Drive URL (e.g., https://drive.google.com/file/d/FILE_ID/view?usp=sharing)
        
    Returns:
        str: Direct download URL or the original URL if conversion fails
    """
    try:
        # Check if it's a Google Drive URL
        if "drive.google.com" in url and "/file/d/" in url:
            # Extract the file ID
            file_id = url.split("/file/d/")[1].split("/")[0]
            # Create direct download link
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        return url
    except Exception:
        # Return original URL if any error occurs
        return url

class BotResponse:
    """
    Class to create consistent, well-formatted bot responses.
    
    This helps maintain a consistent style and structure across all bot messages.
    """
    
    def __init__(self, emoji_key=None, header=None):
        """
        Initialize a bot response.
    
        Args:
            emoji_key (str, optional): Key to lookup in EMOJI dictionary
            header (str, optional): Header text for the message
        """
        self.parts = []
    
        # Get emoji dict safely
        emoji_dict = EMOJI
    
        if emoji_key and emoji_key in emoji_dict:
            self.header = f"{emoji_dict[emoji_key]} {header}" if header else emoji_dict[emoji_key]
        else:
            self.header = header
    
    def add_header(self, text, emoji_key=None):
        """
        Add a header to the message.
        
        Args:
            text (str): Header text
            emoji_key (str, optional): Key to lookup in EMOJI dictionary
            
        Returns:
            BotResponse: self for method chaining
        """
        if emoji_key and emoji_key in EMOJI:
            self.header = f"{EMOJI[emoji_key]} {text}"
        else:
            self.header = text
        return self
    
    def add_paragraph(self, text):
        """
        Add a paragraph to the message.
        
        Args:
            text (str): Paragraph text
            
        Returns:
            BotResponse: self for method chaining
        """
        self.parts.append(text)
        return self
    
    def add_bullet_list(self, items, emoji_key=None):
        """
        Add a bullet list to the message.
        
        Args:
            items (list): List items
            emoji_key (str, optional): Key to lookup in EMOJI dictionary for bullets
            
        Returns:
            BotResponse: self for method chaining
        """
        bullet = EMOJI[emoji_key] if emoji_key and emoji_key in EMOJI else "•"
        bullet_list = []
        
        for item in items:
            bullet_list.append(f"{bullet} {item}")
        
        self.parts.append("\n".join(bullet_list))
        return self
    
    def add_data_table(self, data, headers=None):
        """
        Add a formatted data table.
        
        Args:
            data (list): List of data rows
            headers (list, optional): Column headers
            
        Returns:
            BotResponse: self for method chaining
        """
        if not data:
            return self
        
        table_str = ""
        
        # Add headers if provided
        if headers:
            table_str += " | ".join(headers) + "\n"
            table_str += "-" * (sum(len(h) for h in headers) + 3 * (len(headers) - 1)) + "\n"
        
        # Add data rows
        for row in data:
            table_str += " | ".join(str(cell) for cell in row)
            table_str += "\n"
        
        self.parts.append(table_str)
        return self
    
    def add_divider(self):
        """
        Add a divider line.
        
        Returns:
            BotResponse: self for method chaining
        """
        self.parts.append("------------------------")
        return self
    
    def get_message(self):
        """
        Get the complete formatted message.
        
        Returns:
            str: The formatted message text
        """
        message = ""
        
        # Add header if present
        if self.header:
            message += f"{self.header}\n\n"
        
        # Add all parts with spacing
        for i, part in enumerate(self.parts):
            message += part
            # Add spacing after all parts except the last
            if i < len(self.parts) - 1:
                message += "\n\n"
        
        return message