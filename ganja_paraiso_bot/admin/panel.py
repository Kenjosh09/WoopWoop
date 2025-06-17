"""
Admin panel for the Ganja Paraiso bot.
Handles all admin functionality.
"""
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ganja_paraiso_bot.config.emoji import EMOJI
from ganja_paraiso_bot.config.messages import MESSAGES
from ganja_paraiso_bot.utils.ui import create_button, create_button_layout, send_typing_action
from ganja_paraiso_bot.utils.logging import log_admin_action

class AdminPanel:
    """Handles all admin panel functionality."""
    
    def __init__(self, bot, admin_ids, google_apis, order_manager, loggers):
        """
        Initialize the admin panel.
        
        Args:
            bot: Telegram bot instance
            admin_ids: List of admin user IDs
            google_apis: Google APIs manager instance
            order_manager: Order manager instance
            loggers: Dictionary of logger instances
        """
        self.bot = bot
        self.admin_ids = admin_ids
        self.google_apis = google_apis
        self.order_manager = order_manager
        self.loggers = loggers
    
    async def show_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Display the admin panel.
        
        Args:
            update: Telegram update object
            context: Conversation context
        """
        user_id = update.effective_user.id
        
        # Check if user is admin
        if user_id not in self.admin_ids:
            await update.message.reply_text(MESSAGES["not_authorized"])
            return
        
        # Show typing indicator
        await send_typing_action(context, update.effective_chat.id)
        
        # Log admin access
        log_admin_action(self.loggers["admin"], user_id, "accessed admin panel")
        
        # Create admin welcome message
        admin_message = (
            f"{EMOJI['admin']} Welcome to the Admin Panel\n\n"
            f"From here, you can manage orders, update statuses, "
            f"handle inventory, and process payments."
        )
        
        # Create admin buttons
        buttons = self._build_admin_buttons()
        reply_markup = InlineKeyboardMarkup(buttons)
        
        await update.message.reply_text(admin_message, reply_markup=reply_markup)
    
    def _build_admin_buttons(self):
        """
        Build admin panel buttons.
        
        Returns:
            list: List of button rows
        """
        buttons = [
            [create_button("action", "view_orders", f"{EMOJI['list']} View All Orders")],
            [create_button("action", "search_order", f"{EMOJI['search']} Search Order by ID")],
            [create_button("action", "manage_inventory", f"{EMOJI['inventory']} Manage Inventory")],
            [create_button("action", "review_payments", f"{EMOJI['review']} Review Payments")]
        ]
        
        return buttons
    
    async def view_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Display all recent orders.
        
        Args:
            update: Telegram update object
            context: Conversation context
        """
        user_id = update.effective_user.id
        
        # Check if user is admin
        if user_id not in self.admin_ids:
            await update.callback_query.answer(MESSAGES["not_authorized"])
            return
        
        # Acknowledge callback
        await update.callback_query.answer()
        
        # Show typing indicator
        chat_id = update.callback_query.message.chat_id
        await send_typing_action(context, chat_id)
        
        # Log admin action
        log_admin_action(self.loggers["admin"], user_id, "viewed all orders")
        
        # For now, show a placeholder message
        # In a real implementation, fetch orders from Google Sheets
        orders_message = (
            f"{EMOJI['list']} Recent Orders\n\n"
            f"This is where you would see a list of recent orders.\n"
            f"This feature will be implemented in the next phase."
        )
        
        # Create filter buttons
        filter_buttons = self._build_filter_buttons("all")
        
        # Add back button
        filter_buttons.append([create_button("back", "back_to_admin", "Back to Admin Panel")])
        
        reply_markup = InlineKeyboardMarkup(filter_buttons)
        
        await update.callback_query.message.edit_text(orders_message, reply_markup=reply_markup)
    
    def _build_filter_buttons(self, current_filter):
        """
        Build order filter buttons.
        
        Args:
            current_filter: Currently selected filter
            
        Returns:
            list: List of button rows
        """
        filters = {
            "all": "All Orders",
            "pending": "Pending Payment",
            "confirmed": "Payment Confirmed",
            "booked": "Booked",
            "delivered": "Delivered"
        }
        
        buttons = []
        
        for filter_key, filter_name in filters.items():
            # Add check mark to current filter
            text = f"{filter_name} ✓" if filter_key == current_filter else filter_name
            buttons.append([InlineKeyboardButton(text, callback_data=f"filter_{filter_key}")])
        
        return buttons
    
    async def manage_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id=None):
        """
        Display order management options.
        
        Args:
            update: Telegram update object
            context: Conversation context
            order_id: Optional order ID
        """
        user_id = update.effective_user.id
        
        # Check if user is admin
        if user_id not in self.admin_ids:
            await update.callback_query.answer(MESSAGES["not_authorized"])
            return
        
        # Acknowledge callback
        await update.callback_query.answer()
        
        # Extract order ID from callback data if not provided
        if not order_id and update.callback_query.data.startswith("order_"):
            order_id = update.callback_query.data.replace("order_", "")
        
        # Show typing indicator
        chat_id = update.callback_query.message.chat_id
        await send_typing_action(context, chat_id)
        
        # Log admin action
        log_admin_action(self.loggers["admin"], user_id, "managing order", order_id)
        
        # For now, show a placeholder message
        # In a real implementation, fetch order details from Google Sheets
        order_message = (
            f"{EMOJI['order']} Order Management: {order_id}\n\n"
            f"This is where you would see details for this order.\n"
            f"This feature will be implemented in the next phase."
        )
        
        # Create management buttons
        buttons = [
            [create_button("action", f"update_status_{order_id}", f"{EMOJI['update']} Update Status")],
            [create_button("action", f"view_payment_{order_id}", f"{EMOJI['screenshot']} View Payment")],
            [create_button("action", f"add_tracking_{order_id}", f"{EMOJI['tracking']} Add Tracking")],
            [create_button("back", "back_to_orders", "Back to Orders")]
        ]
        
        reply_markup = InlineKeyboardMarkup(buttons)
        
        await update.callback_query.message.edit_text(order_message, reply_markup=reply_markup)
    
    async def review_payments(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Review pending payments.
        
        Args:
            update: Telegram update object
            context: Conversation context
        """
        user_id = update.effective_user.id
        
        # Check if user is admin
        if user_id not in self.admin_ids:
            await update.callback_query.answer(MESSAGES["not_authorized"])
            return
        
        # Acknowledge callback
        await update.callback_query.answer()
        
        # Show typing indicator
        chat_id = update.callback_query.message.chat_id
        await send_typing_action(context, chat_id)
        
        # Log admin action
        log_admin_action(self.loggers["admin"], user_id, "reviewing payments")
        
        # For now, show a placeholder message
        # In a real implementation, fetch pending payments from Google Sheets
        payments_message = (
            f"{EMOJI['review']} Pending Payments\n\n"
            f"This is where you would see a list of pending payments.\n"
            f"This feature will be implemented in the next phase."
        )
        
        # Create back button
        buttons = [
            [create_button("back", "back_to_admin", "Back to Admin Panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(buttons)
        
        await update.callback_query.message.edit_text(payments_message, reply_markup=reply_markup)