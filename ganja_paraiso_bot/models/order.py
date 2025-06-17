"""
Order Manager for the Ganja Paraiso bot.
Handles order creation, updates, and status tracking.
"""
from datetime import datetime
from typing import Dict, Any, Optional, Union

from telegram.ext import ContextTypes

from ganja_paraiso_bot.utils.helpers import generate_order_id
from ganja_paraiso_bot.utils.ui import build_cart_summary
from ganja_paraiso_bot.config.constants import ADMIN_ID

class OrderManager:
    """Manages order operations and persistence."""
    
    def __init__(self, google_apis, loggers):
        """
        Initialize the order manager.
        
        Args:
            google_apis: Google APIs manager instance
            loggers: Dictionary of logger instances
        """
        self.google_apis = google_apis
        self.loggers = loggers
        
    async def create_order(self, context: ContextTypes.DEFAULT_TYPE, user_data: Dict[str, Any], payment_url=None):
        """
        Create a new order and add it to Google Sheets.
        
        Args:
            context: The conversation context
            user_data: User data containing order information
            payment_url: URL to payment screenshot if available
            
        Returns:
            str: Order ID of the created order, or None if creation failed
        """
        try:
            user = context.user_data.get("username", "Unknown")
            user_id = context.user_data.get("user_id", "Unknown")
            
            # Generate cart summary
            cart = user_data.get("cart", [])
            if not cart:
                self.loggers["orders"].error(f"Attempted to create order with empty cart for user {user_id}")
                return None
                
            cart_summary, total_cost = build_cart_summary(cart)
            
            # Get shipping details
            shipping_details = user_data.get("shipping_details", {})
            name = shipping_details.get("name", user)
            address = shipping_details.get("address", "No address provided")
            contact = shipping_details.get("contact", "No contact provided")
            
            # Generate order ID
            order_id = generate_order_id()
            
            # Create timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Create order data for Google Sheets
            order_data = [
                order_id,            # Order ID
                user_id,             # Telegram ID
                name,                # Customer Name
                address,             # Address
                contact,             # Contact
                "COMPLETE ORDER",    # Special marker row for complete order
                len(cart),           # Quantity (number of items)
                total_cost,          # Total price
                "Pending Payment Review",  # Initial status
                payment_url or "",   # Payment URL
                timestamp,           # Order date
                "",                  # Notes
                ""                   # Tracking link
            ]
            
            # Add order to Google Sheets
            success = await self.google_apis.add_order_to_sheet(order_data)
            
            if success:
                # Log the order creation
                self.loggers["orders"].info(
                    f"Order {order_id} created for user {user_id} with {len(cart)} items, total: {total_cost}"
                )
                
                # Add each cart item as a separate row for reference
                for item in cart:
                    category = item.get("category", "Unknown")
                    suboption = item.get("suboption", "Unknown")
                    quantity = item.get("quantity", 0)
                    price = item.get("total_price", 0)
                    
                    item_name = f"{category} - {suboption}"
                    
                    item_data = [
                        order_id,            # Order ID
                        user_id,             # Telegram ID
                        name,                # Customer Name
                        "",                  # Address (blank for item rows)
                        "",                  # Contact (blank for item rows)
                        item_name,           # Product
                        quantity,            # Quantity
                        price,               # Price
                        "",                  # Status (blank for item rows)
                        "",                  # Payment URL (blank for item rows)
                        timestamp,           # Order date
                        "",                  # Notes
                        ""                   # Tracking link
                    ]
                    
                    # Add each item as a separate row
                    await self.google_apis.add_order_to_sheet(item_data)
                
                # Also notify admin about new order
                try:
                    admin_message = (
                        f"🆕 New order received!\n"
                        f"Order ID: {order_id}\n"
                        f"Customer: {name}\n"
                        f"Items: {len(cart)}\n"
                        f"Total: ₱{total_cost:,.2f}\n\n"
                        f"Use /admin to manage orders."
                    )
                    
                    # Try to send notification to admin
                    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)
                except Exception as admin_err:
                    self.loggers["errors"].error(f"Failed to notify admin about order: {admin_err}")
                
                return order_id
            else:
                self.loggers["errors"].error(f"Failed to add order to Google Sheets for user {user_id}")
                return None
                
        except Exception as e:
            self.loggers["errors"].error(f"Error creating order: {e}")
            return None
    
    async def update_order_status(self, context, order_id, new_status, tracking_link=None):
        """
        Update the status of an existing order and notify the customer.
        
        Args:
            context: The conversation context
            order_id (str): Order ID to update
            new_status (str): New status value
            tracking_link (str, optional): Tracking link for order shipment
            
        Returns:
            bool: Success status
        """
        try:
            # Update status in Google Sheets
            success, customer_id = await self.google_apis.update_order_status(
                order_id, new_status, tracking_link
            )
            
            if not success:
                self.loggers["errors"].error(f"Failed to update status for order {order_id}")
                return False
                
            # Log the status update
            self.loggers["orders"].info(
                f"Order {order_id} status updated to '{new_status}'"
                f"{' with tracking' if tracking_link else ''}"
            )
            
            # Notify customer if we have their ID and they're not the admin
            if customer_id and customer_id != ADMIN_ID:
                try:
                    from ganja_paraiso_bot.utils.helpers import get_status_message
                    from ganja_paraiso_bot.config.emoji import EMOJI
                    
                    # Get appropriate message for this status
                    emoji, status_message = get_status_message(new_status, tracking_link)
                    
                    # Create notification message
                    customer_message = (
                        f"{EMOJI['shipping']} Order Status Update\n\n"
                        f"Your order ({order_id}) has been updated.\n\n"
                        f"Status: {emoji} {new_status}\n\n"
                        f"{status_message}"
                    )
                    
                    # Add tracking link if available
                    if tracking_link:
                        customer_message += f"\n\n{EMOJI['tracking']} [Track your delivery here]({tracking_link})"
                    
                    # Send notification to customer
                    await context.bot.send_message(
                        chat_id=customer_id,
                        text=customer_message,
                        parse_mode="Markdown",
                        disable_web_page_preview=True
                    )
                except Exception as notify_err:
                    self.loggers["errors"].error(f"Failed to notify customer about status update: {notify_err}")
            
            return True
            
        except Exception as e:
            self.loggers["errors"].error(f"Error updating order status: {e}")
            return False
    
    async def get_order_details(self, order_id):
        """
        Get details for a specific order.
        
        Args:
            order_id (str): Order ID to look up
            
        Returns:
            dict: Order details or None if not found
        """
        try:
            return await self.google_apis.get_order_details(order_id)
        except Exception as e:
            self.loggers["errors"].error(f"Error getting order details: {e}")
            return None
    
    async def get_order_status(self, order_id):
        """
        Get the current status of an order.
        
        Args:
            order_id (str): Order ID to check
            
        Returns:
            tuple: (status, tracking_link, error_message)
            One of the first two will be None depending on success
        """
        try:
            order_details = await self.get_order_details(order_id)
            
            if not order_details:
                return None, None, "Order not found. Please check your Order ID."
                
            status = order_details.get("Status", "Unknown")
            tracking_link = order_details.get("Tracking Link", "")
            
            return status, tracking_link, None
            
        except Exception as e:
            self.loggers["errors"].error(f"Error getting order status: {e}")
            return None, None, "An error occurred while checking order status."
            
    async def cleanup_abandoned_carts(self, context):
        """
        Clean up abandoned carts to free up memory.
        
        Args:
            context: The conversation context
            
        Returns:
            int: Number of carts cleaned up
        """
        import time
        
        cleanup_count = 0
        cart_expiry = 86400  # 24 hours in seconds
        now = time.time()
        
        # No direct access to user_data for all users, must loop through sessions
        if "sessions" in context.bot_data:
            for user_id, session in context.bot_data["sessions"].items():
                # Skip if no last_activity timestamp
                if "last_activity" not in session:
                    continue
                    
                # Check if session is older than cart_expiry
                if now - session["last_activity"] > cart_expiry:
                    # Try to clean up the cart if it exists
                    try:
                        if user_id in context.user_data and "cart" in context.user_data[user_id]:
                            if context.user_data[user_id]["cart"]:
                                self.loggers["main"].info(
                                    f"Cleaning up abandoned cart for user {user_id}"
                                )
                                context.user_data[user_id]["cart"] = []
                                cleanup_count += 1
                    except Exception:
                        # Skip this user if there's an error
                        continue
        
        return cleanup_count