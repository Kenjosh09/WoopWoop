"""
Logging setup and utility functions for the Ganja Paraiso bot.
"""
import logging
import os
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Dict

def setup_logging():
    """
    Set up a robust logging system with rotation and separate log files.
    
    Returns:
        dict: Dictionary containing configured loggers for different components
    """
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Define all required loggers
    logger_names = [
        "main", "orders", "payments", "errors", "admin", 
        "performance", "status", "users", "security"
    ]
    
    loggers = {}
    
    # Configure each logger
    for name in logger_names:
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        
        # Create rotating file handler (10 files, 5MB each)
        handler = RotatingFileHandler(
            f"{log_dir}/{name}.log",
            maxBytes=5*1024*1024,
            backupCount=10
        )
        
        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(handler)
        
        # Also add a console handler for development
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)
        logger.addHandler(console)
        
        loggers[name] = logger
    
    # Log startup message
    loggers["main"].info("Bot logging system initialized")
    
    return loggers

def log_order(logger, order_data, action="created"):
    """
    Log order information with consistent formatting.
    Sensitive data is masked for security.
    
    Args:
        logger: The logger instance to use
        order_data (dict): Order information
        action (str): Action being performed on the order
    """
    order_id = order_data.get("order_id", "Unknown")
    customer = mask_sensitive_data(order_data.get("name", "Unknown"), 'name')
    total = order_data.get("total", 0)
    
    logger.info(
        f"Order {order_id} {action} | Customer: {customer} | "
        f"Total: ₱{total:,.2f} | Items: {order_data.get('items_count', 0)}"
    )

def mask_sensitive_data(data, mask_type='default'):
    """
    Mask sensitive data for logging purposes.
    
    Args:
        data (str): Data to mask
        mask_type (str): Type of data being masked ('phone', 'address', 'name', etc.)
        
    Returns:
        str: Masked data
    """
    if not data:
        return ''
    
    data = str(data)
    
    if mask_type == 'phone':
        # Mask phone number - keep first 3 and last 2 digits
        if len(data) > 5:
            visible_part = data[:3] + '*' * (len(data) - 5) + data[-2:]
            return visible_part
        return '*' * len(data)
    
    elif mask_type == 'address':
        # For address, show only the first part and city
        parts = data.split(',')
        if len(parts) > 1:
            # Take first part of street address
            street = parts[0].strip()
            city_part = parts[-1].strip()
            
            # Get house/building number if available
            address_parts = street.split(' ', 1)
            
            if len(address_parts) > 1 and address_parts[0].isdigit():
                # Show house number and first letter of street name
                masked_street = address_parts[0] + ' ' + address_parts[1][0] + '*' * (len(address_parts[1]) - 1)
            else:
                # Just show first 3 chars of address
                masked_street = street[:3] + '*' * (len(street) - 3) if len(street) > 3 else street
                
            return f"{masked_street}, {city_part}"
        
        # If simple address, show first 4 chars
        if len(data) > 4:
            return data[:4] + '*' * (len(data) - 4)
        return data
        
    elif mask_type == 'name':
        # Show first letter of each name part (with Unicode support)
        import unicodedata
        name_parts = data.split()
        masked_parts = []
    
        for part in name_parts:
            if len(part) > 1:
                # Get first character correctly even with multi-byte chars
                first_char = part[0]
                masked_parts.append(f"{first_char}{'*' * (len(part) - 1)}")
            else:
                masked_parts.append(part)
            
        return ' '.join(masked_parts)
        
    else:
        # Default masking - show first 3 chars and last char
        if len(data) > 4:
            return data[:3] + '*' * (len(data) - 4) + data[-1]
        return '*' * len(data)

def log_payment(logger, order_id, status, amount=None):
    """
    Log payment information with consistent formatting.
    
    Args:
        logger: The logger instance to use
        order_id (str): The order ID
        status (str): Payment status (received, confirmed, rejected)
        amount (float, optional): Payment amount
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    amount_str = f" | Amount: ₱{amount:,.2f}" if amount else ""
    
    logger.info(
        f"Payment for order {order_id} {status} at {timestamp}{amount_str}"
    )

def log_error(logger, function_name, error, user_id=None):
    """
    Log error information with consistent formatting.
    
    Args:
        logger: The logger instance to use
        function_name (str): Name of the function where the error occurred
        error (Exception): The error object
        user_id (int, optional): Telegram user ID if applicable
    """
    user_info = f" | User: {user_id}" if user_id else ""
    
    logger.error(
        f"Error in {function_name}{user_info} | {type(error).__name__}: {str(error)}"
    )

def log_security_event(logger, event_type, user_id=None, ip=None, details=None):
    """
    Log security-related events for monitoring and auditing.
    
    Args:
        logger: The logger instance to use
        event_type (str): Type of security event
        user_id (int, optional): Telegram user ID if applicable
        ip (str, optional): IP address if available
        details (str, optional): Additional event details
    """
    # Create a secure log with consistent format and UTC time
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    user_info = f"User: {user_id}" if user_id else "No user"
    ip_info = f"IP: {ip}" if ip else "No IP"
    details_info = f"Details: {details}" if details else ""
    
    logger["security"].warning(
        f"SECURITY EVENT [{event_type}] | {timestamp} | {user_info} | {ip_info} | {details_info}"
    )

def log_admin_action(logger, admin_id, action, order_id=None):
    """
    Log admin actions with consistent formatting.
    
    Args:
        logger: The logger instance to use
        admin_id (int): Telegram ID of the admin
        action (str): Action performed
        order_id (str, optional): Order ID if applicable
    """
    order_info = f" | Order: {order_id}" if order_id else ""
    
    logger.info(
        f"Admin {admin_id} performed: {action}{order_info}"
    )