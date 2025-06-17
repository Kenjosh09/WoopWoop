"""
Ganja Paraiso Telegram Bot - Main application file

This is the entry point for the Ganja Paraiso cannabis store Telegram bot.
It initializes the bot, sets up handlers, and starts the application.
"""
import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional, List

from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, PicklePersistence, filters
)

# Import configuration
from ganja_paraiso_bot.config.constants import (
    TOKEN, ADMIN_ID, CATEGORY, STRAIN_TYPE, BROWSE_BY, PRODUCT_SELECTION,
    QUANTITY, CONFIRM, DETAILS, CONFIRM_DETAILS, PAYMENT, TRACKING
)

# Import utilities
from ganja_paraiso_bot.utils.logging import setup_logging
from ganja_paraiso_bot.utils.persistence import cleanup_persistence_file
from ganja_paraiso_bot.utils.helpers import cleanup_old_sessions, cleanup_abandoned_carts

# Import API manager
from ganja_paraiso_bot.apis.google_api_manager import GoogleAPIsManager

# Import models
from ganja_paraiso_bot.models.inventory import InventoryManager
from ganja_paraiso_bot.models.order import OrderManager

# Import handlers
from ganja_paraiso_bot.handlers.start import (
    start, handle_start_shopping, restart_conversation, 
    contact_support, get_help, cancel
)
from ganja_paraiso_bot.handlers.browsing import (
    choose_category_wrapper, choose_strain_type_wrapper,
    browse_carts_by_wrapper, show_local_products_wrapper,
    select_product_wrapper, handle_back_navigation_wrapper,
    back_to_categories_wrapper
)

# Import admin panel
from ganja_paraiso_bot.admin.panel import AdminPanel

# Import middleware
from ganja_paraiso_bot.middleware.health_check import HealthCheckMiddleware
from ganja_paraiso_bot.middleware.activity_tracker import ActivityTrackerMiddleware
from ganja_paraiso_bot.middleware.error_handler import error_handler

# Global instances (will be initialized in main)
loggers = None
google_apis = None
inventory_manager = None
order_manager = None
admin_panel = None


async def handle_quantity_selection(update, context):
    """
    Handle selection of product quantity, either from buttons or custom input.
    This will be moved to its own module in the future.
    
    Args:
        update: Telegram update object
        context: Conversation context
    """
    callback_query = update.callback_query
    
    # Handle quantity selection via callback query
    if callback_query:
        await callback_query.answer()
        
        callback_data = callback_query.data
        
        # Check if this is custom quantity request
        if callback_data == "custom_quantity":
            await callback_query.message.edit_text(
                "📝 Please enter the quantity you want:",
                reply_markup=None
            )
            return QUANTITY
        
        # Extract quantity from callback data
        quantity = int(callback_data.replace("quantity_", ""))
        
        # Set the quantity in user data
        context.user_data["quantity"] = quantity
        
        # Forward to confirm order
        await confirm_order(update, context)
    
    # Handle custom quantity input via message
    elif update.message and update.message.text:
        from ganja_paraiso_bot.utils.validation import validate_quantity
        
        # Extract and validate quantity
        category = context.user_data.get("category", "")
        is_valid, result = validate_quantity(update.message.text, category)
        
        if not is_valid:
            # Show error message for invalid quantity
            await update.message.reply_text(
                f"❌ {result}\n\nPlease enter a valid quantity."
            )
            return QUANTITY
        
        # Set the validated quantity
        context.user_data["quantity"] = result
        
        # Show confirmation
        await confirm_order(update, context)
    
    return CONFIRM


async def confirm_order(update, context):
    """
    Display order confirmation with price calculation.
    This will be moved to its own module in the future.
    
    Args:
        update: Telegram update object
        context: Conversation context
    """
    from ganja_paraiso_bot.utils.ui import create_button_layout, manage_cart
    from ganja_paraiso_bot.config.emoji import EMOJI
    
    # Set current location
    context.user_data["current_location"] = "confirm"
    
    # Get product information
    category = context.user_data.get("category", "")
    product_key = context.user_data.get("selected_product", "")
    quantity = context.user_data.get("quantity", 0)
    strain_type = context.user_data.get("strain_type", "")
    
    # Get product details
    product_details = await inventory_manager.get_product_details(
        category, product_key, strain_type
    )
    
    if not product_details:
        # Product not found or no longer available
        error_message = f"{EMOJI['error']} Sorry, this product is no longer available."
        
        if update.callback_query:
            await update.callback_query.message.edit_text(
                error_message,
                reply_markup=create_button_layout([
                    [create_button("back", "back_to_categories", "Browse Again")]
                ])
            )
        else:
            await update.message.reply_text(
                error_message,
                reply_markup=create_button_layout([
                    [create_button("back", "back_to_categories", "Browse Again")]
                ])
            )
        return CATEGORY
    
    # Get product name and other details
    product_name = product_details.get("name", "Unknown Product")
    
    # Calculate price
    price_result = await inventory_manager.calculate_price(category, product_key, quantity)
    
    # Handle different price result formats
    if len(price_result) == 4:  # Includes discount info
        total_price, unit_price, regular_price, discount_info = price_result
        has_discount = True
    else:
        total_price, unit_price = price_result
        regular_price = None
        discount_info = None
        has_discount = False
    
    # Create cart item
    cart_item = {
        "category": category,
        "suboption": product_name,
        "product_key": product_key,
        "quantity": quantity,
        "unit_price": unit_price,
        "total_price": total_price
    }
    
    # Add discount info if available
    if has_discount:
        cart_item["regular_price"] = regular_price
        cart_item["discount_info"] = discount_info
    
    # Add to cart
    manage_cart(context, "add", cart_item)
    
    # Get unit name
    unit = "grams" if category in ["buds", "local"] else "units"
    
    # Create confirmation message
    if has_discount:
        confirm_message = (
            f"{EMOJI['cart']} Item Added to Cart:\n\n"
            f"{EMOJI[category]} {product_name}\n"
            f"Quantity: {quantity} {unit}\n"
            f"Regular Price: ₱{regular_price:,}\n"
            f"Discounted Price: ₱{total_price:,} {discount_info}\n\n"
            f"What would you like to do next?"
        )
    else:
        confirm_message = (
            f"{EMOJI['cart']} Item Added to Cart:\n\n"
            f"{EMOJI[category]} {product_name}\n"
            f"Quantity: {quantity} {unit}\n"
            f"Unit Price: ₱{unit_price:,}/{unit}\n"
            f"Total: ₱{total_price:,}\n\n"
            f"What would you like to do next?"
        )
    
    # Create action buttons
    buttons = [
        [create_button("action", "browse_more", f"{EMOJI['browse']} Add More Items")],
        [create_button("action", "checkout", f"{EMOJI['shipping']} Checkout")],
        [create_button("action", "view_cart", f"{EMOJI['cart']} View Cart")]
    ]
    
    reply_markup = create_button_layout(buttons)
    
    # Handle different types of updates
    if update.callback_query:
        await update.callback_query.message.edit_text(
            confirm_message,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            confirm_message,
            reply_markup=reply_markup
        )
    
    return CONFIRM


def register_handlers(application: Application) -> None:
    """
    Register all conversation and command handlers.
    
    Args:
        application: Telegram bot application
    """
    # Main conversation handler for the shopping flow
    shopping_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(handle_start_shopping, pattern="^start_shopping$")
        ],
        states={
            CATEGORY: [
                CallbackQueryHandler(choose_category_wrapper, pattern="^start_shopping$"),
                CallbackQueryHandler(choose_strain_type_wrapper, pattern="^buds$"),
                CallbackQueryHandler(browse_carts_by_wrapper, pattern="^carts$"),
                CallbackQueryHandler(show_local_products_wrapper, pattern="^local$")
            ],
            STRAIN_TYPE: [
                CallbackQueryHandler(show_strain_products_wrapper, pattern="^(indica|sativa|hybrid)$")
            ],
            BROWSE_BY: [
                CallbackQueryHandler(show_carts_by_option_wrapper, pattern="^browse_by_(brand|weight)$"),
                CallbackQueryHandler(show_carts_by_option_wrapper, pattern="^show_all_carts$")
            ],
            PRODUCT_SELECTION: [
                CallbackQueryHandler(select_product_wrapper, pattern="^product_")
            ],
            QUANTITY: [
                CallbackQueryHandler(handle_quantity_selection, pattern="^quantity_"),
                CallbackQueryHandler(handle_quantity_selection, pattern="^custom_quantity$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quantity_selection)
            ],
            CONFIRM: [
                CallbackQueryHandler(back_to_categories_wrapper, pattern="^browse_more$"),
                CallbackQueryHandler(checkout, pattern="^checkout$"),
                CallbackQueryHandler(view_cart, pattern="^view_cart$")
            ],
            DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_details)
            ],
            CONFIRM_DETAILS: [
                CallbackQueryHandler(confirm_details, pattern="^confirm$"),
                CallbackQueryHandler(input_details_wrapper, pattern="^edit_details$")
            ],
            PAYMENT: [
                MessageHandler(filters.PHOTO, handle_payment_screenshot),
                CallbackQueryHandler(cancel_payment, pattern="^cancel_payment$")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$"),
            CallbackQueryHandler(handle_back_navigation_wrapper, pattern="^back$"),
            CallbackQueryHandler(back_to_categories_wrapper, pattern="^back_to_categories$"),
            CallbackQueryHandler(restart_conversation, pattern="^restart_conversation$"),
            CommandHandler("help", get_help),
            CallbackQueryHandler(get_help, pattern="^get_help$")
        ],
        name="shopping_conversation",
        persistent=True
    )
    
    # Order tracking conversation handler
    tracking_handler = ConversationHandler(
        entry_points=[
            CommandHandler("track", track_order_wrapper),
            CallbackQueryHandler(track_order_wrapper, pattern="^track_order$")
        ],
        states={
            TRACKING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_order_id),
                CallbackQueryHandler(get_order_id, pattern="^order_"),
                CallbackQueryHandler(refresh_tracking, pattern="^refresh_tracking_")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_tracking),
            CallbackQueryHandler(cancel_tracking, pattern="^cancel_tracking$"),
            CallbackQueryHandler(start, pattern="^start$")
        ],
        name="tracking_conversation",
        persistent=True
    )
    
    # Register conversation handlers
    application.add_handler(shopping_handler)
    application.add_handler(tracking_handler)
    
    # Admin panel handlers
    application.add_handler(CommandHandler("admin", admin_panel.show_panel))
    application.add_handler(CallbackQueryHandler(admin_panel.view_orders, pattern="^view_orders"))
    application.add_handler(CallbackQueryHandler(admin_panel.manage_order, pattern="^order_"))
    application.add_handler(CallbackQueryHandler(admin_panel.review_payments, pattern="^review_payments"))
    
    # Utility handlers
    application.add_handler(CommandHandler("help", get_help))
    application.add_handler(CallbackQueryHandler(get_help, pattern="^get_help$"))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("support", support_command))
    
    # Error handler
    application.add_error_handler(error_handler)


async def post_init(application: Application) -> None:
    """
    Perform post-initialization tasks.
    
    Args:
        application: Telegram bot application
    """
    # Log startup
    loggers["main"].info("Bot started successfully")
    print("✅ Bot started successfully")
    
    # Store start time in bot data
    application.bot_data["start_time"] = time.time()
    
    # Initialize sheets
    try:
        await google_apis.initialize_sheets()
        print("✅ Google Sheets initialized")
    except Exception as e:
        loggers["errors"].error(f"Failed to initialize sheets: {e}")
        print(f"❌ Failed to initialize sheets: {e}")
    
    # Send startup notification to admin
    try:
        startup_message = (
            "🚀 Bot has been started!\n\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "Use /admin to access the admin panel."
        )
        await application.bot.send_message(chat_id=ADMIN_ID, text=startup_message)
    except Exception as e:
        loggers["errors"].error(f"Failed to send admin notification: {e}")
        print(f"⚠️ Failed to send admin notification: {e}")


async def setup_scheduled_jobs(application: Application) -> None:
    """
    Set up scheduled jobs for maintenance tasks.
    
    Args:
        application: Telegram bot application
    """
    job_queue = application.job_queue
    
    # Set up regular cleanup job (every 12 hours)
    job_queue.run_repeating(cleanup_job, interval=43200)  # 12 hours in seconds
    
    # Set up conversation timeout recovery (every 30 minutes)
    job_queue.run_repeating(timeout_recovery_job, interval=1800)  # 30 minutes
    
    # Set up health check job (every 5 minutes)
    job_queue.run_repeating(health_check_job, interval=300)  # 5 minutes


async def cleanup_job(context):
    """
    Run regular cleanup tasks.
    
    Args:
        context: Job context
    """
    try:
        # Log start of cleanup
        loggers["main"].info("Starting scheduled cleanup job")
        
        # Clean up old sessions
        sessions_cleaned = cleanup_old_sessions(context)
        
        # Clean up abandoned carts
        carts_cleaned = await order_manager.cleanup_abandoned_carts(context)
        
        # Clean up persistence file if needed
        persistence_cleaned = False
        current_size = get_persistence_file_size()
        
        if current_size > 25:  # MB
            success, old_size, new_size = cleanup_persistence_file(context, loggers)
            persistence_cleaned = success
            if success:
                loggers["main"].info(
                    f"Persistence file cleaned: {old_size:.1f}MB -> {new_size:.1f}MB"
                )
        
        # Log cleanup results
        loggers["main"].info(
            f"Cleanup completed: {sessions_cleaned} sessions, {carts_cleaned} carts, "
            f"persistence cleaned: {persistence_cleaned}"
        )
    except Exception as e:
        loggers["errors"].error(f"Error in cleanup job: {e}")


async def timeout_recovery_job(context):
    """
    Check and recover timed out conversations.
    
    Args:
        context: Job context
    """
    try:
        from ganja_paraiso_bot.utils.helpers import get_recovery_message
        
        # Get current time
        now = time.time()
        timeout_threshold = 3600  # 1 hour
        
        # No direct way to iterate through all conversations in user_data
        # Look through sessions instead
        if "sessions" in context.bot_data:
            for user_id, session in context.bot_data["sessions"].items():
                # Skip if no last_activity timestamp
                if "last_activity" not in session:
                    continue
                    
                # Check if session is inactive but not timed out yet
                if now - session["last_activity"] > timeout_threshold:
                    # Try to check if user is in the middle of a conversation
                    try:
                        if (user_id in context.user_data and 
                                "current_location" in context.user_data[user_id] and
                                context.user_data[user_id].get("current_location") not in 
                                ["start", None]):
                            
                            # Send recovery message
                            recovery_message = get_recovery_message(context.user_data[user_id])
                            
                            # Create recovery buttons
                            from ganja_paraiso_bot.utils.ui import get_common_buttons
                            reply_markup = create_button_layout(
                                get_common_buttons("restart_home")
                            )
                            
                            await context.bot.send_message(
                                chat_id=user_id,
                                text=recovery_message,
                                reply_markup=reply_markup
                            )
                            
                            # Log recovery attempt
                            loggers["main"].info(f"Sent conversation recovery to user {user_id}")
                    except Exception:
                        # Skip this user if there's an error
                        continue
    except Exception as e:
        loggers["errors"].error(f"Error in timeout recovery job: {e}")


async def health_check_job(context):
    """
    Perform health check and log status.
    
    Args:
        context: Job context
    """
    try:
        from ganja_paraiso_bot.utils.helpers import memory_usage_report
        
        # Get memory usage
        memory_stats = memory_usage_report()
        
        # Get cache stats
        cache_stats = google_apis.get_cache_stats()
        
        # Calculate uptime
        start_time = context.bot_data.get("start_time", time.time())
        uptime_seconds = time.time() - start_time
        uptime_hours = uptime_seconds / 3600
        
        # Log health stats
        loggers["performance"].info(
            f"Health stats: Uptime: {uptime_hours:.1f}h, "
            f"Memory: {memory_stats.get('rss', 'N/A'):.1f}MB, "
            f"Cache hit rate: {cache_stats.get('total', {}).get('hit_ratio', 0):.2%}"
        )
    except Exception as e:
        loggers["errors"].error(f"Error in health check job: {e}")


def main() -> None:
    """Initialize and start the Ganja Paraiso bot."""
    global loggers, google_apis, inventory_manager, order_manager, admin_panel
    
    # Set up logging
    loggers = setup_logging()
    loggers["main"].info("Starting Ganja Paraiso Bot")
    
    # Initialize persistence
    persistence = PicklePersistence(filepath="bot_persistence")
    
    # Create the application
    application = Application.builder().token(TOKEN).persistence(persistence).build()
    
    # Initialize components
    google_apis = GoogleAPIsManager(loggers)
    inventory_manager = InventoryManager(google_apis, loggers)
    order_manager = OrderManager(google_apis, loggers)
    admin_panel = AdminPanel(application.bot, [ADMIN_ID], google_apis, order_manager, loggers)
    
    # Set up middlewares
    health_middleware = HealthCheckMiddleware(application.bot, [ADMIN_ID], loggers)
    application.add_handler(health_middleware)
    
    activity_middleware = ActivityTrackerMiddleware()
    application.add_handler(activity_middleware)
    
    # Register all handlers
    register_handlers(application)
    
    # Set up post-initialization tasks
    application.post_init = post_init
    
    # Set up scheduled jobs
    application.job_queue.run_once(
        lambda ctx: asyncio.create_task(setup_scheduled_jobs(application)),
        when=1
    )
    
    # Start the bot
    loggers["main"].info("Starting bot polling")
    application.run_polling()


if __name__ == "__main__":
    main()