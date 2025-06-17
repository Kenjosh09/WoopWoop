"""
Input validation and data sanitization functions for the Ganja Paraiso bot.
"""
import re
from typing import Tuple, Dict, Union, Any

from ganja_paraiso_bot.config.constants import REGEX
from ganja_paraiso_bot.config.products import PRODUCTS

def sanitize_input(text, max_length=100):
    """
    Sanitize user input to prevent injection attacks and ensure data quality.
    
    Args:
        text (str): Text to sanitize
        max_length (int): Maximum length to allow
        
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
        
    # Remove any HTML or unwanted characters - use a more comprehensive pattern
    sanitized = re.sub(r'<[^>]*>|[^\w\s,.!?@:;()\-_\/]', '', text)
    
    # Trim whitespace
    sanitized = sanitized.strip()
    
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
        
    return sanitized

def validate_sensitive_data(data_type, value):
    """
    Validate sensitive user data against specific patterns.
    
    Args:
        data_type (str): Type of data being validated ('name', 'address', 'phone', etc.)
        value (str): Value to validate
        
    Returns:
        tuple: (is_valid, error_message or sanitized_value)
    """
    # First sanitize the input
    value = sanitize_input(value, max_length=200)
    
    if data_type == 'name':
        # Name should only contain letters, spaces, and basic punctuation
        if not re.match(r'^[\w\s.,\'-]{2,50}$', value):
            return False, "Name contains invalid characters or is too short/long."
        return True, value
        
    elif data_type == 'address':
        # Address should have minimum length and contain some numbers and letters
        if len(value) < 10:
            return False, "Address is too short. Please provide a complete address."
        if not (re.search(r'\d', value) and re.search(r'[a-zA-Z]', value)):
            return False, "Address should contain both numbers and letters."
        return True, value
        
    elif data_type == 'phone':
        # Phone number validation - allow different formats but ensure it has enough digits
        # Remove all non-digit characters first
        digits = re.sub(r'\D', '', value)
        if len(digits) < 10 or len(digits) > 15:
            return False, "Phone number should have 10-15 digits."
        # Format the phone number consistently
        formatted = digits
        return True, formatted
        
    elif data_type == 'order_id':
        # Validate order ID format (WW-XXXX-YYY)
        if not re.match(r'^WW-\d{4}-[A-Z]{3}$', value):
            return False, "Invalid order ID format. Should be like WW-1234-ABC."
        return True, value
    
    # Default case
    return True, value

def is_valid_order_id(order_id: str) -> bool:
    """
    Validate the format of an order ID with enhanced security checks.
    
    Args:
        order_id: Order ID to validate
        
    Returns:
        bool: True if the order ID is valid, False otherwise
        
    Example:
        >>> is_valid_order_id("WW-1234-ABC")
        True
        >>> is_valid_order_id("INVALID")
        False
    """
    valid, _ = validate_sensitive_data('order_id', order_id)
    return valid

def validate_quantity(text, category=None):
    """
    Validate quantity input from user.
    
    Args:
        text (str): Quantity text input
        category (str, optional): Product category
        
    Returns:
        tuple: (is_valid, result_or_error_message)
    """
    # Check if input is a number
    match = re.search(REGEX["quantity"], text)
    if not match:
        return False, "Please enter a number."
    
    quantity = int(match.group(1))
    
    # Basic validation
    if quantity <= 0:
        return False, "Please enter a positive number."
        
    # Category-specific validation
    if category == "local":
        # Only allow specific quantities
        valid_quantities = [10, 50, 100, 300]
        if quantity not in valid_quantities:
            return False, "For Local (BG), please select one of the available options: 10g, 50g, 100g, or 300g."
    
    # Product-specific validation
    if category and category in PRODUCTS:
        min_order = PRODUCTS[category].get("min_order", 1)
        unit = PRODUCTS[category].get("unit", "units")
        
        if quantity < min_order:
            return False, f"Minimum order for {PRODUCTS[category]['name']} is {min_order} {unit}."
    
    return True, quantity

def validate_shipping_details(text):
    """
    Validate shipping details format with enhanced flexibility and security.
    
    Args:
        text (str): Shipping details text in format "Name / Address / Contact"
        
    Returns:
        tuple: (is_valid, result_dict_or_error_message)
    """
    # Log the input for debugging without exposing full details
    print(f"Validating shipping details (length: {len(text)})")
    
    # Basic format check - need two slashes to have three parts
    if text.count('/') != 2:
        return False, "Invalid format. Need exactly two '/' separators. Format: Name / Address / Contact"
    
    # Split the text by slashes and trim whitespace
    parts = [part.strip() for part in text.split('/')]
    
    # Ensure we have three parts
    if len(parts) != 3:
        return False, "Invalid format. Use: Name / Address / Contact"
        
    name, address, contact = parts
    
    # Validate each part using our enhanced validators
    name_valid, name_result = validate_sensitive_data('name', name)
    if not name_valid:
        return False, f"Name validation failed: {name_result}"
    
    address_valid, address_result = validate_sensitive_data('address', address)
    if not address_valid:
        return False, f"Address validation failed: {address_result}"
    
    phone_valid, phone_result = validate_sensitive_data('phone', contact)
    if not phone_valid:
        return False, f"Contact number validation failed: {phone_result}"
    
    # Success - return the validated details
    return True, {
        "name": name_result,
        "address": address_result,
        "contact": phone_result
    }

def validate_image(file_bytes, max_size_mb=5):
    """
    Validate an uploaded image for security.
    
    Args:
        file_bytes (ByteArray): Raw image data
        max_size_mb (int): Maximum allowed size in MB
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not file_bytes:
        return False, "Empty file data received"
        
    # Check file size
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"File too large: {size_mb:.1f}MB (max {max_size_mb}MB)"
    
    # Check minimum size to ensure it's not an empty or corrupt image
    if len(file_bytes) < 1000:  # Less than 1KB
        return False, "File too small - might be corrupt or empty"
    
    try:
        # Check file signature (magic numbers)
        # JPEG signature
        if file_bytes[:3] == b'\xFF\xD8\xFF':
            return True, "JPEG image"
        
        # PNG signature
        if file_bytes[:8] == b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A':
            return True, "PNG image"
        
        # GIF signature
        if file_bytes[:6] in (b'GIF87a', b'GIF89a'):
            return True, "GIF image"
        
        # WebP signature
        if len(file_bytes) > 12 and file_bytes[:4] == b'RIFF' and file_bytes[8:12] == b'WEBP':
            return True, "WebP image"
        
        # No valid signature found
        return False, "Invalid image format (only JPEG, PNG, GIF, and WebP images are allowed)"
        
    except Exception as e:
        return False, f"Error validating image: {str(e)}"