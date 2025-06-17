"""
Product browsing handlers for the Ganja Paraiso bot.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ganja_paraiso_bot.config.emoji import EMOJI
from ganja_paraiso_bot.config.products import PRODUCTS
from ganja_paraiso_bot.utils.ui import (
    create_button, create_button_layout, send_typing_action, 
    get_navigation_buttons, build_category_buttons
)

async def choose_category(update: Update, context: ContextTypes.DEFAULT_TYPE, inventory_manager, loggers):
    """
    Display product categories for the user to choose from.
    
    Args:
        update: Telegram update object
        context: Conversation context
        inventory_manager: Inventory manager instance
        loggers: Dictionary of logger instances
    """
    # Set current location
    context.user_data["current_location"] = "category"
    
    # Show typing indicator for natural UX
    chat_id = update.effective_chat.id
    await send_typing_action(context, chat_id)
    
    # Get available categories
    available_categories = inventory_manager.get_available_categories()
    
    # Create category menu message
    category_message = (
        f"{EMOJI['browse']} Select a product category:\n\n"
        f"Please choose from our available products below."
    )
    
    # Create keyboard with product categories
    reply_markup = build_category_buttons(available_categories)
    
    # Handle different types of updates
    if update.callback_query:
        # Acknowledge the callback
        await update.callback_query.answer()
        
        # Edit the message to show categories
        await update.callback_query.message.edit_text(
            category_message,
            reply_markup=reply_markup
        )
    else:
        # Send new message with categories
        await update.message.reply_text(
            category_message,
            reply_markup=reply_markup
        )

async def handle_back_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE, inventory_manager, loggers):
    """
    Handle back button navigation based on current location.
    
    Args:
        update: Telegram update object
        context: Conversation context
        inventory_manager: Inventory manager instance
        loggers: Dictionary of logger instances
    """
    # Show typing indicator
    chat_id = update.callback_query.message.chat_id
    await send_typing_action(context, chat_id)
    
    # Acknowledge the callback
    await update.callback_query.answer()
    
    # Get current location
    current_location = context.user_data.get("current_location", "start")
    
    # Handle navigation based on current location
    if current_location == "product_selection":
        # Go back to strain selection or category selection
        if context.user_data.get("category") == "buds":
            await back_to_strain_type(update, context, inventory_manager, loggers)
        else:
            await back_to_categories(update, context, inventory_manager, loggers)
    elif current_location == "strain_selection":
        await back_to_categories(update, context, inventory_manager, loggers)
    elif current_location == "browse_carts_by":
        await back_to_categories(update, context, inventory_manager, loggers)
    elif current_location == "quantity":
        # Go back to product selection
        await back_to_products(update, context, inventory_manager, loggers)
    else:
        # Default: go back to the main menu
        await restart_conversation(update, context)

async def back_to_categories(update: Update, context: ContextTypes.DEFAULT_TYPE, inventory_manager, loggers):
    """
    Navigate back to the category selection screen.
    
    Args:
        update: Telegram update object
        context: Conversation context
        inventory_manager: Inventory manager instance
        loggers: Dictionary of logger instances
    """
    # Reset category-related data
    if "category" in context.user_data:
        del context.user_data["category"]
    if "strain_type" in context.user_data:
        del context.user_data["strain_type"]
    
    # Go to category selection
    await choose_category(update, context, inventory_manager, loggers)

async def back_to_strain_type(update: Update, context: ContextTypes.DEFAULT_TYPE, inventory_manager, loggers):
    """
    Navigate back to the strain type selection screen.
    
    Args:
        update: Telegram update object
        context: Conversation context
        inventory_manager: Inventory manager instance
        loggers: Dictionary of logger instances
    """
    # Keep category but reset strain-specific data
    if "strain_type" in context.user_data:
        del context.user_data["strain_type"]
    if "selected_product" in context.user_data:
        del context.user_data["selected_product"]
    
    # Go to strain selection
    await choose_strain_type(update, context, inventory_manager, loggers)

async def back_to_products(update: Update, context: ContextTypes.DEFAULT_TYPE, inventory_manager, loggers):
    """
    Navigate back to the product selection screen.
    
    Args:
        update: Telegram update object
        context: Conversation context
        inventory_manager: Inventory manager instance
        loggers: Dictionary of logger instances
    """
    # Reset product-specific data but keep category and strain
    if "selected_product" in context.user_data:
        del context.user_data["selected_product"]
    
    # Determine which product screen to show
    category = context.user_data.get("category", "")
    strain_type = context.user_data.get("strain_type", "")
    
    if category == "buds" and strain_type:
        await show_strain_products(update, context, inventory_manager, loggers)
    elif category == "carts":
        browse_by = context.user_data.get("browse_by", "")
        if browse_by:
            await show_carts_by_option(update, context, inventory_manager, loggers)
        else:
            await browse_carts_by(update, context, inventory_manager, loggers)
    elif category == "local":
        await show_local_products(update, context, inventory_manager, loggers)
    else:
        # Default fallback
        await choose_category(update, context, inventory_manager, loggers)

async def choose_strain_type(update: Update, context: ContextTypes.DEFAULT_TYPE, inventory_manager, loggers):
    """
    Display strain selection for buds.
    
    Args:
        update: Telegram update object
        context: Conversation context
        inventory_manager: Inventory manager instance
        loggers: Dictionary of logger instances
    """
    # Set current location
    context.user_data["current_location"] = "strain_selection"
    
    # Store the selected category (should be "buds")
    if update.callback_query and update.callback_query.data == "buds":
        context.user_data["category"] = "buds"
    
    # Show typing indicator
    chat_id = update.effective_chat.id
    await send_typing_action(context, chat_id)
    
    # Create strain selection message
    strain_message = (
        f"{EMOJI['buds']} Select a Strain Type:\n\n"
        f"Indica: Relaxing effects, great for nighttime use.\n"
        f"Sativa: Energizing effects, ideal for daytime use.\n"
        f"Hybrid: Balanced effects, versatile for any time."
    )
    
    # Create strain selection buttons
    buttons = [
        [InlineKeyboardButton("🌿 Indica", callback_data="indica")],
        [InlineKeyboardButton("🌱 Sativa", callback_data="sativa")],
        [InlineKeyboardButton("🍃 Hybrid", callback_data="hybrid")],
        [create_button("back", "back_to_categories", "Back to Categories")]
    ]
    
    reply_markup = create_button_layout(buttons)
    
    # Handle different types of updates
    if update.callback_query:
        # Acknowledge the callback
        await update.callback_query.answer()
        
        # Edit message to show strain selection
        await update.callback_query.message.edit_text(
            strain_message,
            reply_markup=reply_markup
        )
    else:
        # Send new message with strain selection
        await update.message.reply_text(
            strain_message,
            reply_markup=reply_markup
        )

async def browse_carts_by(update: Update, context: ContextTypes.DEFAULT_TYPE, inventory_manager, loggers):
    """
    Display browsing options for carts (by brand or weight).
    
    Args:
        update: Telegram update object
        context: Conversation context
        inventory_manager: Inventory manager instance
        loggers: Dictionary of logger instances
    """
    # Set current location
    context.user_data["current_location"] = "browse_carts_by"
    
    # Store the selected category (should be "carts")
    if update.callback_query and update.callback_query.data == "carts":
        context.user_data["category"] = "carts"
    
    # Show typing indicator
    chat_id = update.effective_chat.id
    await send_typing_action(context, chat_id)
    
    # Create options message
    options_message = (
        f"{EMOJI['carts']} Browse Carts & Disposables By:\n\n"
        f"How would you like to browse our selection?"
    )
    
    # Create browsing option buttons
    buttons = [
        [create_button("action", "browse_by_brand", "Browse by Brand")],
        [create_button("action", "browse_by_weight", "Browse by Weight")],
        [create_button("action", "show_all_carts", "Show All Carts")],
        [create_button("back", "back_to_categories", "Back to Categories")]
    ]
    
    reply_markup = create_button_layout(buttons)
    
    # Handle different types of updates
    if update.callback_query:
        # Acknowledge the callback
        await update.callback_query.answer()
        
        # Edit message to show options
        await update.callback_query.message.edit_text(
            options_message,
            reply_markup=reply_markup
        )
    else:
        # Send new message with options
        await update.message.reply_text(
            options_message,
            reply_markup=reply_markup
        )

async def show_local_products(update: Update, context: ContextTypes.DEFAULT_TYPE, inventory_manager, loggers):
    """
    Display local (BG) products with pricing information.
    
    Args:
        update: Telegram update object
        context: Conversation context
        inventory_manager: Inventory manager instance
        loggers: Dictionary of logger instances
    """
    # Set current location
    context.user_data["current_location"] = "product_selection"
    
    # Store the selected category (should be "local")
    if update.callback_query and update.callback_query.data == "local":
        context.user_data["category"] = "local"
    
    # Show typing indicator
    chat_id = update.effective_chat.id
    await send_typing_action(context, chat_id)
    
    # Create pricing message for Local (BG)
    pricing_message = (
        f"{EMOJI['local']} Local (BG) Pricing:\n\n"
        f"• 10 grams: ₱1,000/g = ₱10,000\n"
        f"• 50 grams: ₱700/g = ₱35,000 (30% discount)\n"
        f"• 100 grams: ₱600/g = ₱60,000 (40% discount)\n"
        f"• 300 grams: ₱500/g = ₱150,000 (50% discount)\n\n"
        f"Please select a quantity option:"
    )
    
    # Create quantity buttons for Local (BG)
    buttons = [
        [InlineKeyboardButton("10 grams - ₱10,000", callback_data="quantity_10")],
        [InlineKeyboardButton("50 grams - ₱35,000", callback_data="quantity_50")],
        [InlineKeyboardButton("100 grams - ₱60,000", callback_data="quantity_100")],
        [InlineKeyboardButton("300 grams - ₱150,000", callback_data="quantity_300")],
        [create_button("back", "back_to_categories", "Back to Categories")]
    ]
    
    reply_markup = create_button_layout(buttons)
    
    # Handle different types of updates
    if update.callback_query:
        # Acknowledge the callback
        await update.callback_query.answer()
        
        # Edit message to show pricing
        await update.callback_query.message.edit_text(
            pricing_message,
            reply_markup=reply_markup
        )
    else:
        # Send new message with pricing
        await update.message.reply_text(
            pricing_message,
            reply_markup=reply_markup
        )

async def show_strain_products(update: Update, context: ContextTypes.DEFAULT_TYPE, inventory_manager, loggers):
    """
    Display products for a selected strain type.
    
    Args:
        update: Telegram update object
        context: Conversation context
        inventory_manager: Inventory manager instance
        loggers: Dictionary of logger instances
    """
    # Set current location
    context.user_data["current_location"] = "product_selection"
    
    # Store the selected strain type
    strain_type = update.callback_query.data if update.callback_query else None
    if strain_type in ["indica", "sativa", "hybrid"]:
        context.user_data["strain_type"] = strain_type
    else:
        strain_type = context.user_data.get("strain_type", "")
    
    # Show typing indicator
    chat_id = update.effective_chat.id
    await send_typing_action(context, chat_id)
    
    # Get products for this strain type
    products_by_tag, products_by_strain, _ = await inventory_manager.get_inventory_safe()
    strain_products = products_by_strain.get(strain_type, [])
    
    # Create strain products message
    strain_emoji = "🌿" if strain_type == "indica" else "🌱" if strain_type == "sativa" else "🍃"
    products_message = (
        f"{strain_emoji} {strain_type.title()} Strains:\n\n"
        f"Select a strain to view details:"
    )
    
    # Create product buttons
    buttons = []
    for product in strain_products:
        name = product.get("name", "Unknown")
        price = product.get("price", 0)
        button_text = f"{name} - ₱{price:,}/g"
        button_data = f"product_{product.get('key', name.lower().replace(' ', '_'))}"
        buttons.append([InlineKeyboardButton(button_text, callback_data=button_data)])
    
    # Add navigation buttons
    buttons.append([create_button("back", "back_to_strain", "Back to Strain Types")])
    
    reply_markup = create_button_layout(buttons)
    
    # Handle different types of updates
    if update.callback_query:
        # Acknowledge the callback
        await update.callback_query.answer()
        
        # Edit message to show products
        await update.callback_query.message.edit_text(
            products_message,
            reply_markup=reply_markup
        )
    else:
        # Send new message with products
        await update.message.reply_text(
            products_message,
            reply_markup=reply_markup
        )

async def show_carts_by_option(update: Update, context: ContextTypes.DEFAULT_TYPE, inventory_manager, loggers):
    """
    Display carts filtered by selected option (brand or weight).
    
    Args:
        update: Telegram update object
        context: Conversation context
        inventory_manager: Inventory manager instance
        loggers: Dictionary of logger instances
    """
    # Set current location
    context.user_data["current_location"] = "product_selection"
    
    # Get browse option from callback data
    callback_data = update.callback_query.data if update.callback_query else ""
    
    if callback_data == "browse_by_brand":
        context.user_data["browse_by"] = "brand"
        filter_field = "brand"
        filter_display = "Brand"
    elif callback_data == "browse_by_weight":
        context.user_data["browse_by"] = "weight"
        filter_field = "weight"
        filter_display = "Weight"
    elif callback_data == "show_all_carts":
        context.user_data["browse_by"] = "all"
        filter_field = None
        filter_display = "All"
    else:
        # Use existing browse option if available
        browse_by = context.user_data.get("browse_by", "")
        if browse_by == "brand":
            filter_field = "brand"
            filter_display = "Brand"
        elif browse_by == "weight":
            filter_field = "weight"
            filter_display = "Weight"
        else:
            filter_field = None
            filter_display = "All"
    
    # Show typing indicator
    chat_id = update.effective_chat.id
    await send_typing_action(context, chat_id)
    
    # Get cart products
    products_by_tag, _, _ = await inventory_manager.get_inventory_safe()
    cart_products = products_by_tag.get("carts", [])
    
    # Create product list message
    products_message = (
        f"{EMOJI['carts']} Carts & Disposables ({filter_display}):\n\n"
        f"Select a product to view details:"
    )
    
    # Group products if using a filter
    grouped_products = {}
    if filter_field:
        for product in cart_products:
            filter_value = product.get(filter_field, "Other")
            if filter_value not in grouped_products:
                grouped_products[filter_value] = []
            grouped_products[filter_value].append(product)
    else:
        # No grouping for "show all" option
        grouped_products = {"All": cart_products}
    
    # Create product buttons, grouped by filter
    buttons = []
    
    for group, products in grouped_products.items():
        # Add group header if there are multiple groups
        if len(grouped_products) > 1:
            group_header = f"--- {group} ---"
            buttons.append([InlineKeyboardButton(group_header, callback_data=f"group_{group}")])
        
        # Add product buttons for this group
        for product in products:
            name = product.get("name", "Unknown")
            price = product.get("price", 0)
            weight = product.get("weight", "")
            brand = product.get("brand", "")
            
            # Create descriptive button text
            if weight and brand:
                button_text = f"{brand} {name} ({weight}) - ₱{price:,}"
            elif weight:
                button_text = f"{name} ({weight}) - ₱{price:,}"
            elif brand:
                button_text = f"{brand} {name} - ₱{price:,}"
            else:
                button_text = f"{name} - ₱{price:,}"
            
            button_data = f"product_{product.get('key', name.lower().replace(' ', '_'))}"
            buttons.append([InlineKeyboardButton(button_text, callback_data=button_data)])
    
    # Add navigation buttons
    buttons.append([create_button("back", "back_to_browse", "Back to Browse Options")])
    
    reply_markup = create_button_layout(buttons)
    
    # Handle different types of updates
    if update.callback_query:
        # Acknowledge the callback
        await update.callback_query.answer()
        
        # Edit message to show products
        await update.callback_query.message.edit_text(
            products_message,
            reply_markup=reply_markup
        )
    else:
        # Send new message with products
        await update.message.reply_text(
            products_message,
            reply_markup=reply_markup
        )

async def select_product(update: Update, context: ContextTypes.DEFAULT_TYPE, inventory_manager, loggers):
    """
    Handle product selection and show quantity options.
    
    Args:
        update: Telegram update object
        context: Conversation context
        inventory_manager: Inventory manager instance
        loggers: Dictionary of logger instances
    """
    # Ensure we have a callback query
    if not update.callback_query:
        return
    
    # Set current location
    context.user_data["current_location"] = "quantity"
    
    # Extract product key from callback data
    callback_data = update.callback_query.data
    product_key = callback_data.replace("product_", "")
    
    # Store selected product key
    context.user_data["selected_product"] = product_key
    
    # Show typing indicator
    chat_id = update.callback_query.message.chat_id
    await send_typing_action(context, chat_id)
    
    # Acknowledge the callback
    await update.callback_query.answer()
    
    # Get product details
    category = context.user_data.get("category", "")
    strain_type = context.user_data.get("strain_type", "")
    
    product_details = await inventory_manager.get_product_details(
        category, product_key, strain_type
    )
    
    if not product_details:
        # Handle product not found case
        error_message = f"{EMOJI['error']} Sorry, this product is no longer available."
        
        await update.callback_query.message.edit_text(
            error_message,
            reply_markup=create_button_layout([[create_button("back", "back", "Go Back")]])
        )
        return
    
    # Get product information
    product_name = product_details.get("name", "Unknown Product")
    price = product_details.get("price", 0)
    stock = product_details.get("stock", 0)
    
    # Get min order quantity
    min_order = 1
    unit = "unit(s)"
    
    if category in PRODUCTS:
        min_order = PRODUCTS[category].get("min_order", 1)
        unit = PRODUCTS[category].get("unit", "unit(s)")
    
    # Create product details message
    product_message = (
        f"{EMOJI.get(category.lower(), '🔍')} {product_name}\n\n"
        f"Price: ₱{price:,} per {unit}\n"
        f"Available: {stock} {unit}\n\n"
        f"Minimum order: {min_order} {unit}\n\n"
        f"Please select a quantity:"
    )
    
    # Create quantity selection buttons
    buttons = []
    
    # Different quantity options based on product category
    if category == "buds":
        # Common bud quantities
        buttons = [
            [InlineKeyboardButton("1 gram", callback_data="quantity_1")],
            [InlineKeyboardButton("3 grams", callback_data="quantity_3")],
            [InlineKeyboardButton("5 grams", callback_data="quantity_5")],
            [InlineKeyboardButton("7 grams", callback_data="quantity_7")],
            [InlineKeyboardButton("14 grams", callback_data="quantity_14")],
            [InlineKeyboardButton("28 grams", callback_data="quantity_28")],
            [InlineKeyboardButton("Custom Quantity", callback_data="custom_quantity")]
        ]
    elif category == "local":
        # Local has fixed quantity options with pricing already shown
        buttons = [
            [InlineKeyboardButton("10 grams", callback_data="quantity_10")],
            [InlineKeyboardButton("50 grams", callback_data="quantity_50")],
            [InlineKeyboardButton("100 grams", callback_data="quantity_100")],
            [InlineKeyboardButton("300 grams", callback_data="quantity_300")]
        ]
    elif category == "carts":
        # Carts typically sold as individual units
        buttons = [
            [InlineKeyboardButton("1 unit", callback_data="quantity_1")],
            [InlineKeyboardButton("2 units", callback_data="quantity_2")],
            [InlineKeyboardButton("3 units", callback_data="quantity_3")],
            [InlineKeyboardButton("5 units", callback_data="quantity_5")],
            [InlineKeyboardButton("Custom Quantity", callback_data="custom_quantity")]
        ]
    else:
        # Generic quantity options for other products
        buttons = [
            [InlineKeyboardButton("1", callback_data="quantity_1")],
            [InlineKeyboardButton("2", callback_data="quantity_2")],
            [InlineKeyboardButton("3", callback_data="quantity_3")],
            [InlineKeyboardButton("5", callback_data="quantity_5")],
            [InlineKeyboardButton("Custom Quantity", callback_data="custom_quantity")]
        ]
    
    # Add navigation buttons
    buttons.append([create_button("back", "back", "Go Back")])
    
    reply_markup = create_button_layout(buttons)
    
    # Update message with product details and quantity selection
    await update.callback_query.message.edit_text(
        product_message,
        reply_markup=reply_markup
    )

# Wrapper functions for integrating with the main application
async def choose_category_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper for choose_category to inject dependencies."""
    # These would be imported from main.py or injected
    from ganja_paraiso_bot.main import inventory_manager, loggers
    await choose_category(update, context, inventory_manager, loggers)

async def choose_strain_type_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper for choose_strain_type to inject dependencies."""
    from ganja_paraiso_bot.main import inventory_manager, loggers
    await choose_strain_type(update, context, inventory_manager, loggers)

async def browse_carts_by_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper for browse_carts_by to inject dependencies."""
    from ganja_paraiso_bot.main import inventory_manager, loggers
    await browse_carts_by(update, context, inventory_manager, loggers)

async def show_local_products_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper for show_local_products to inject dependencies."""
    from ganja_paraiso_bot.main import inventory_manager, loggers
    await show_local_products(update, context, inventory_manager, loggers)

async def select_product_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper for select_product to inject dependencies."""
    from ganja_paraiso_bot.main import inventory_manager, loggers
    await select_product(update, context, inventory_manager, loggers)

async def handle_back_navigation_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper for handle_back_navigation to inject dependencies."""
    from ganja_paraiso_bot.main import inventory_manager, loggers
    await handle_back_navigation(update, context, inventory_manager, loggers)

async def back_to_categories_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper for back_to_categories to inject dependencies."""
    from ganja_paraiso_bot.main import inventory_manager, loggers
    await back_to_categories(update, context, inventory_manager, loggers)

async def show_strain_products_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper for show_strain_products to inject dependencies."""
    from ganja_paraiso_bot.main import inventory_manager, loggers
    await show_strain_products(update, context, inventory_manager, loggers)

async def show_carts_by_option_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper for show_carts_by_option to inject dependencies."""
    from ganja_paraiso_bot.main import inventory_manager, loggers
    await show_carts_by_option(update, context, inventory_manager, loggers)