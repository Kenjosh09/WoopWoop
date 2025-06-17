"""
Google API Manager for handling connections to Google Sheets and Drive.
"""
import asyncio
import random
import time
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional, Tuple, Any, Union

import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from ganja_paraiso_bot.config.constants import (
    GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_NAME, PAYMENT_SCREENSHOTS_FOLDER_ID,
    SHEET_HEADERS, SHEET_COLUMN_INDICES, DEFAULT_INVENTORY
)
from ganja_paraiso_bot.utils.cache import EnhancedCache
from ganja_paraiso_bot.utils.retryable import RetryableOperation

class GoogleAPIsManager:
    """Manage Google API connections with rate limiting, backoff, and enhanced caching."""
    
    def __init__(self, loggers: Dict[str, Any]) -> None:
        """
        Initialize the Google APIs Manager.
        
        Args:
            loggers: Dictionary of logger instances
        """
        self.loggers = loggers
        self.last_request_time: Dict[str, float] = {}
        self.min_request_interval: float = 1.0  # Minimum seconds between requests
        self._sheet_client = None
        self._drive_service = None
        self._sheet = None
        self._inventory_sheet = None
        self._sheet_initialized: bool = False
        
        # Create enhanced caches with appropriate sizes
        self.caches = {
            "inventory": EnhancedCache(max_items=20),
            "orders": EnhancedCache(max_items=100),
            "sheets": EnhancedCache(max_items=50),
            "drive": EnhancedCache(max_items=30)
        }
        
        # Set appropriate TTLs for different cache types
        self.caches["inventory"].default_ttl = 300  # 5 minutes for inventory
        self.caches["orders"].default_ttl = 60      # 1 minute for orders 
        self.caches["sheets"].default_ttl = 120     # 2 minutes for sheets
        self.caches["drive"].default_ttl = 600      # 10 minutes for drive
        
    async def get_sheet_client(self):
        """
        Get or create a gspread client with authorization.
        
        Returns:
            gspread.Client: Authorized gspread client
        """
        # Use existing client if available
        if self._sheet_client:
            return self._sheet_client
                
        try:
            # Verify the file exists before proceeding
            import os
            if not os.path.isfile(GOOGLE_CREDENTIALS_FILE):
                error_msg = (
                    f"Credentials file not found: {GOOGLE_CREDENTIALS_FILE}\n"
                    f"Please ensure the file exists at this location."
                )
                self.loggers["errors"].error(error_msg)
                print(f"❌ {error_msg}")
                raise FileNotFoundError(error_msg)
            
            # Log successful file access
            file_size = os.path.getsize(GOOGLE_CREDENTIALS_FILE)
            self.loggers["main"].info(
                f"Using credentials file ({file_size} bytes): {GOOGLE_CREDENTIALS_FILE}"
            )
            
            # Set up authentication for Google Sheets using google-auth
            scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']
            
            try:
                import json
                creds = service_account.Credentials.from_service_account_file(
                    GOOGLE_CREDENTIALS_FILE,
                    scopes=scope
                )
            except json.JSONDecodeError:
                error_msg = f"Credentials file is not valid JSON: {GOOGLE_CREDENTIALS_FILE}"
                self.loggers["errors"].error(error_msg)
                raise ValueError(error_msg)
            except Exception as cred_error:
                self.loggers["errors"].error(f"Error loading credentials: {str(cred_error)}")
                raise
            
            self._sheet_client = gspread.authorize(creds)
            self.loggers["main"].info("Successfully authenticated with Google Sheets")
            return self._sheet_client
        except Exception as e:
            self.loggers["errors"].error(f"Failed to authenticate with Google Sheets: {e}")
            raise
    
    async def get_drive_service(self):
        """
        Get or create a Google Drive service client.
        
        Returns:
            Resource: Google Drive API service instance
        """
        # Use existing drive service if available
        if self._drive_service:
            return self._drive_service
            
        try:
            # Set up Google Drive API client
            credentials = service_account.Credentials.from_service_account_file(
                GOOGLE_CREDENTIALS_FILE, 
                scopes=['https://www.googleapis.com/auth/drive']
            )
            self._drive_service = build('drive', 'v3', credentials=credentials)
            return self._drive_service
        except Exception as e:
            self.loggers["errors"].error(f"Failed to authenticate with Google Drive: {e}")
            raise
    
    async def initialize_sheets(self):
        """
        Initialize the order sheet and inventory sheet.
        Sets up headers if needed.
        
        Returns:
            tuple: (orders_sheet, inventory_sheet)
        """
        if self._sheet_initialized and self._sheet and self._inventory_sheet:
            return self._sheet, self._inventory_sheet
            
        try:
            # Make a rate-limited request
            await self._rate_limit_request('sheets')
            
            # Get the spreadsheet with enhanced error handling
            client = await self.get_sheet_client()
            if not client:
                self.loggers["errors"].error("Failed to get sheet client")
                return None, None
                
            print("DEBUG SHEETS: Got sheet client, opening spreadsheet")
            
            try:
                spreadsheet = client.open(GOOGLE_SHEET_NAME)
            except Exception as sheet_err:
                self.loggers["errors"].error(f"Failed to open spreadsheet: {str(sheet_err)}")
                print(f"DEBUG SHEETS: Error opening spreadsheet: {str(sheet_err)}")
                return None, None
            
            # Get or create the main orders sheet
            try:
                self._sheet = spreadsheet.sheet1
                print("DEBUG SHEETS: Successfully accessed orders sheet")
            except Exception as orders_err:
                self.loggers["errors"].error(f"Error accessing orders sheet: {str(orders_err)}")
                try:
                    print("DEBUG SHEETS: Creating orders sheet")
                    self._sheet = spreadsheet.add_worksheet("Orders", 1000, 20)
                except Exception as create_err:
                    self.loggers["errors"].error(f"Error creating orders sheet: {str(create_err)}")
                    return None, None
            
            # Get or create the inventory sheet
            try:
                self._inventory_sheet = spreadsheet.worksheet("Inventory")
                print("DEBUG SHEETS: Successfully accessed inventory sheet")
            except Exception as inv_err:
                self.loggers["errors"].error(f"Error accessing inventory sheet: {str(inv_err)}")
                try:
                    print("DEBUG SHEETS: Creating inventory sheet")
                    self._inventory_sheet = spreadsheet.add_worksheet("Inventory", 100, 10)
                    # Initialize inventory headers with new columns
                    self._inventory_sheet.append_row([
                        "Name", "Strain", "Type", "Tag", "Price", "Stock", 
                        "Weight", "Brand", "Description", "Image_URL"
                    ])
                except Exception as create_err:
                    self.loggers["errors"].error(f"Error creating inventory sheet: {str(create_err)}")
                    # We can continue with just the orders sheet if needed
            
            # Ensure the orders sheet has the correct headers
            try:
                current_headers = self._sheet.row_values(1)
                if not current_headers or len(current_headers) < len(SHEET_HEADERS):
                    print("DEBUG SHEETS: Setting up sheet headers")
                    self._sheet.update("A1", [SHEET_HEADERS])
            except Exception as header_err:
                self.loggers["errors"].error(f"Error setting sheet headers: {str(header_err)}")
                # We can still try to continue if headers exist
            
            self._sheet_initialized = True
            print("DEBUG SHEETS: Sheets successfully initialized")
            return self._sheet, self._inventory_sheet
            
        except Exception as e:
            self.loggers["errors"].error(f"Failed to initialize sheets: {e}")
            # Return None or provide fallback behavior
            print(f"DEBUG SHEETS: Fatal error initializing sheets: {str(e)}")
            return None, None
                
    def _check_cache(self, cache_key, cache_type="inventory", max_age=None):
        """
        Check if cached data exists and is still valid.
        
        Args:
            cache_key (str): The specific key for the cached data
            cache_type (str): The type of cache to use
            max_age (int, optional): Override the default TTL
            
        Returns:
            tuple: (is_valid, cached_data)
        """
        if cache_type not in self.caches:
            cache_type = "inventory"  # Default to inventory cache
            
        cache = self.caches[cache_type]
        ttl = max_age if max_age is not None else None  # Use cache default if not specified
        
        return cache.get(cache_key, ttl)
    
    def _update_cache(self, cache_key, data, cache_type="inventory", ttl=None):
        """
        Update the cache with new data.
        
        Args:
            cache_key (str): The key for the cached data
            data: The data to cache
            cache_type (str): The type of cache to use
            ttl (int, optional): Override the default TTL
            
        Returns:
            The cached data
        """
        if cache_type not in self.caches:
            cache_type = "inventory"  # Default to inventory cache
            
        cache = self.caches[cache_type]
        return cache.set(cache_key, data, ttl)
    
    async def fetch_inventory(self):
        """
        Fetch inventory data from Google Sheets including tags and stock.
        Uses enhanced caching to reduce API calls.
        
        Returns:
            tuple: (products_by_tag, products_by_strain, all_products)
        """
        # Check cache first
        is_valid, cached_data = self._check_cache("inventory_data", "inventory")
        if is_valid:
            return cached_data
        
        products_by_tag = {'buds': [], 'local': [], 'carts': [], 'edibs': []}
        products_by_strain = {'indica': [], 'sativa': [], 'hybrid': []}
        all_products = []
        
        try:
            # Initialize sheets
            _, inventory_sheet = await self.initialize_sheets()
            
            if not inventory_sheet:
                default_inventory = self._create_default_inventory()
                return self._update_cache("inventory_data", default_inventory, "inventory")
            
            # Make a rate-limited request
            await self._rate_limit_request('inventory')
            
            # Get inventory data
            inventory_data = inventory_sheet.get_all_records()
            
            for item in inventory_data:
                # Skip items with no stock
                if 'Stock' not in item or item['Stock'] <= 0:
                    continue
                    
                product_name = item.get('Name', item.get('Strain', 'Unknown'))
                product_key = product_name.lower().replace(' ', '_')
                product_tag = item.get('Tag', '').lower()
                strain_type = item.get('Type', '').lower()
                price = item.get('Price', 0)
                stock = item.get('Stock', 0)
                
                product = {
                    'name': product_name,
                    'key': product_key,
                    'price': price,
                    'stock': stock,
                    'tag': product_tag,
                    'strain': strain_type,
                    'weight': item.get('Weight', ''),  # For carts
                    'brand': item.get('Brand', '')     # For carts
                }
                
                # Add to all products list
                all_products.append(product)
                
                # Categorize by tag
                if product_tag in products_by_tag:
                    products_by_tag[product_tag].append(product)
                    
                # Categorize by strain
                if strain_type in products_by_strain:
                    products_by_strain[strain_type].append(product)
            
            result = (products_by_tag, products_by_strain, all_products)
            return self._update_cache("inventory_data", result, "inventory")
            
        except Exception as e:
            self.loggers["errors"].error(f"Error fetching inventory: {e}")
            # Fallback to default inventory
            default_inventory = self._create_default_inventory()
            return self._update_cache("inventory_data", default_inventory, "inventory")
            
    def _create_default_inventory(self):
        """
        Create a default inventory when API access fails.
        
        Returns:
            tuple: (products_by_tag, products_by_strain, all_products)
        """
        products_by_tag = {'buds': [], 'local': [], 'carts': [], 'edibs': []}
        products_by_strain = {'indica': [], 'sativa': [], 'hybrid': []}
        all_products = []
        
        for item in DEFAULT_INVENTORY:
            product_name = item.get('Name', item.get('Strain', 'Unknown'))
            product_key = product_name.lower().replace(' ', '_')
            product_tag = item.get('Tag', '').lower()
            strain_type = item.get('Type', '').lower()
            price = item.get('Price', 0)
            stock = item.get('Stock', 0)
            
            product = {
                'name': product_name,
                'key': product_key,
                'price': price,
                'stock': stock,
                'tag': product_tag,
                'strain': strain_type,
                'weight': item.get('Weight', ''),
                'brand': item.get('Brand', '')
            }
            
            all_products.append(product)
            
            if product_tag and product_tag in products_by_tag:
                products_by_tag[product_tag].append(product)
                
            if strain_type and strain_type in products_by_strain:
                products_by_strain[strain_type].append(product)
        
        self.loggers["errors"].warning("Using default inventory due to API failure")
        return products_by_tag, products_by_strain, all_products
    
    async def upload_payment_screenshot(self, file_bytes, filename):
        """
        Upload a payment screenshot to Google Drive with enhanced retry logic.
        
        Args:
            file_bytes (BytesIO): File bytes to upload
            filename (str): Name to give the file
            
        Returns:
            str: Web view link to the uploaded file
            
        Raises:
            ConnectionError: When network connectivity issues occur
            ValueError: When file data is invalid
            RuntimeError: For Google API issues
            Exception: For other unexpected errors
        """
        try:
            # Make a rate-limited request
            await self._rate_limit_request('drive')
            
            # Get the drive service
            drive_service = await self.get_drive_service()
            
            # Validate input
            if not file_bytes:
                raise ValueError("Empty file bytes provided")
            
            if not filename or not isinstance(filename, str):
                filename = f"payment_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            
            # Prepare file metadata
            file_metadata = {
                'name': filename,
                'mimeType': 'image/jpeg',
                'parents': [PAYMENT_SCREENSHOTS_FOLDER_ID]
            }
            
            # Create media upload object
            try:
                media = MediaIoBaseUpload(BytesIO(file_bytes), mimetype='image/jpeg')
            except Exception as media_error:
                raise ValueError(f"Invalid file bytes: {media_error}") from media_error
            
            # Create a retryable operation for the upload
            async def perform_upload():
                try:
                    return drive_service.files().create(
                        body=file_metadata, 
                        media_body=media, 
                        fields='id, webViewLink'
                    ).execute()
                except TimeoutError as timeout_err:
                    raise TimeoutError(f"Upload timed out: {timeout_err}") from timeout_err
                except ConnectionError as conn_err:
                    raise ConnectionError(f"Connection error during upload: {conn_err}") from conn_err
                except Exception as api_err:
                    raise RuntimeError(f"Google Drive API error: {api_err}") from api_err
            
            # Use the retryable operation with specific error types
            retry_handler = RetryableOperation(
                self.loggers, 
                max_retries=3,
                retry_on=(ConnectionError, TimeoutError, BrokenPipeError)
            )
            
            drive_file = await retry_handler.run(
                perform_upload, 
                operation_name="upload_payment_screenshot"
            )
            
            # Validate and return the web link
            web_link = drive_file.get('webViewLink')
            if not web_link:
                raise RuntimeError("Drive API returned no webViewLink")
                
            return web_link
            
        except ConnectionError as e:
            self.loggers["errors"].error(f"Connection error uploading payment screenshot: {e}")
            raise
        except TimeoutError as e:
            self.loggers["errors"].error(f"Timeout uploading payment screenshot: {e}")
            raise
        except ValueError as e:
            self.loggers["errors"].error(f"Invalid data for payment screenshot: {e}")
            raise
        except RuntimeError as e:
            self.loggers["errors"].error(f"API error uploading payment screenshot: {e}")
            raise
        except Exception as e:
            self.loggers["errors"].error(f"Unexpected error uploading payment screenshot: {str(e)}")
            raise RuntimeError(f"Failed to upload payment screenshot: {e}") from e
    
    async def add_order_to_sheet(self, order_data):
        """
        Add a new order to the Google Sheet.
        
        Args:
            order_data: List of order values to add to sheet
            
        Returns:
            bool: Success status
        """
        try:
            # Initialize the sheets if not already done
            sheet, _ = await self.initialize_sheets()
            if not sheet:
                self.loggers["errors"].error("Failed to initialize sheet for adding order")
                return False
                
            # Make a rate-limited request
            await self._rate_limit_request('sheets_write')
            
            # Debug print the order data length
            print(f"DEBUG SHEET: Adding order with {len(order_data)} columns to sheet")
            
            # Check if row has correct number of columns
            expected_columns = len(SHEET_HEADERS)
            if len(order_data) != expected_columns:
                # Adjust the order data to match expected columns
                if len(order_data) < expected_columns:
                    # Add empty strings to fill missing columns
                    order_data.extend([""] * (expected_columns - len(order_data)))
                else:
                    # Truncate extra columns
                    order_data = order_data[:expected_columns]
                
                print(f"DEBUG SHEET: Adjusted order data to {len(order_data)} columns")
            
            # Find the next empty row
            try:
                # Get all values in first column
                col_a = sheet.col_values(1)
                # Next row is one more than the length
                next_row = len(col_a) + 1
            except Exception as row_err:
                self.loggers["errors"].error(f"Error finding next row: {str(row_err)}")
                # Default to append as fallback
                next_row = None
            
            # Use RetryableOperation for robust error handling
            retry_handler = RetryableOperation(
                self.loggers, 
                max_retries=3,
                retry_on=(ConnectionError, TimeoutError, BrokenPipeError)
            )
            
            # Define the add operation
            async def add_to_sheet():
                if next_row:
                    # If we know the next row, insert there
                    sheet.insert_row(order_data, next_row)
                else:
                    # Otherwise just append
                    sheet.append_row(order_data)
                return True
            
            # Try adding with retries
            success = await retry_handler.run(
                add_to_sheet,
                operation_name="add_order_to_sheet"
            )
            
            # Update cache
            if success:
                # Invalidate orders cache
                if 'orders' in self.caches:
                    self.caches['orders'].clear()
            
            return success
            
        except Exception as e:
            self.loggers["errors"].error(f"Failed to add order to sheet: {str(e)}")
            return False

    async def update_order_status(self, order_id, new_status, tracking_link=None):
        """
        Update the status and optional tracking link for an existing order.
        
        Args:
            order_id (str): Order ID to update
            new_status (str): New status to set for the order
            tracking_link (str, optional): Tracking link to add to the order
            
        Returns:
            tuple: (success, customer_id) - Success status and customer Telegram ID for notifications
        """
        try:
            # Initialize the sheets if needed
            sheet, _ = await self.initialize_sheets()
            if not sheet:
                self.loggers["errors"].error(f"Failed to initialize sheets for updating order {order_id}")
                return False, None
                
            # Make a rate-limited request
            await self._rate_limit_request('sheets_write')
            
            # Find the order by ID
            all_orders = sheet.get_all_records()
            
            # Debug logging
            print(f"DEBUG STATUS: Updating order {order_id} to status: {new_status}")
            
            # Track if we found and updated the order
            found_order = False
            customer_id = None
            
            # Process the orders
            for idx, order in enumerate(all_orders):
                # Look for the main order entry with matching ID
                if 'Order ID' in order and order['Order ID'] == order_id:
                    if 'Product' in order and order['Product'] == "COMPLETE ORDER":
                        # This is our main order row
                        found_order = True
                        
                        # Extract customer ID for notifications
                        if 'Telegram ID' in order:
                            try:
                                customer_id = int(order['Telegram ID'])
                            except (ValueError, TypeError):
                                customer_id = None
                        
                        # Calculate the row number (add 2: 1 for header, 1 for 0-indexing)
                        row_number = idx + 2
                        
                        # Define what to update
                        updates = {
                            'Status': new_status  # Always update status
                        }
                        
                        # Add tracking link if provided
                        if tracking_link:
                            updates['Tracking Link'] = tracking_link
                        
                        # Perform updates with retry logic
                        retry_handler = RetryableOperation(
                            self.loggers, 
                            max_retries=3,
                            retry_on=(ConnectionError, TimeoutError, BrokenPipeError)
                        )
                        
                        # Define the update operation
                        async def update_sheet_cells():
                            for field, value in updates.items():
                                # Find the column index for this field
                                if field in SHEET_COLUMN_INDICES:
                                    col_idx = SHEET_COLUMN_INDICES[field]
                                    # Update the cell
                                    sheet.update_cell(row_number, col_idx, value)
                                    # Small delay to avoid rate limits
                                    await asyncio.sleep(0.5)
                            return True
                        
                        # Execute with retries
                        success = await retry_handler.run(
                            update_sheet_cells,
                            operation_name=f"update_order_status_{order_id}"
                        )
                        
                        # Clear cache for this order
                        cache_key = f"order_{order_id}"
                        if 'orders' in self.caches:
                            self.caches["orders"].clear(cache_key)
                        
                        # Log the result
                        if success:
                            self.loggers["main"].info(
                                f"Updated order {order_id} status to '{new_status}'"
                                f"{' with tracking' if tracking_link else ''}"
                            )
                        else:
                            self.loggers["errors"].error(
                                f"Failed to update sheet cells for order {order_id}"
                            )
                        
                        # Return the result with customer ID for notifications
                        return success, customer_id
            
            # If we reach here, we didn't find the order
            if not found_order:
                self.loggers["errors"].error(f"Order {order_id} not found for status update")
                return False, None
                
        except Exception as e:
            self.loggers["errors"].error(f"Error updating order status: {str(e)}")
            return False, None
        
    async def get_order_details(self, order_id):
        """
        Get details for a specific order with enhanced caching for frequent requests.
        
        Args:
            order_id (str): Order ID to look up
            
        Returns:
            dict: Order details or None if not found
        """
        # For active orders, use a shorter cache expiry
        cache_key = f"order_{order_id}"
        is_valid, cached_data = self._check_cache(cache_key, "orders", max_age=30)  # Short cache time for orders
        if is_valid:
            return cached_data

        try:
            # Initialize sheets
            sheet, _ = await self.initialize_sheets()
            
            if not sheet:
                self.loggers["errors"].error("Failed to get sheet for order details")
                return None
            
            # Make a rate-limited request
            await self._rate_limit_request('sheets_read')
            
            # Get all orders
            orders = sheet.get_all_records()
            
            # Find the main order
            for order in orders:
                if (order.get('Order ID') == order_id and 
                    order.get('Product') == 'COMPLETE ORDER'):
                    # Cache this order's details
                    return self._update_cache(cache_key, order, "orders")
            
            # If not found, cache a None value briefly to prevent repeated lookups
            return self._update_cache(cache_key, None, "orders", ttl=30)
            
        except Exception as e:
            self.loggers["errors"].error(f"Failed to get order details: {e}")
            return None
    
    async def _rate_limit_request(self, api_name):
        """
        Rate limit requests to Google APIs to prevent quota issues.
        
        This method implements an adaptive rate limiting strategy that tracks
        request timing and enforces appropriate delays between requests.
        
        Args:
            api_name (str): Name of the API being accessed for tracking purposes
        """
        now = time.time()
        
        # Define minimum wait times for different API operations (in seconds)
        min_wait_times = {
            'sheets': 1.0,           # General sheets access
            'sheets_read': 0.5,      # Read operations (less intensive)
            'sheets_write': 1.2,     # Write operations (more intensive)
            'drive': 1.5,            # Drive operations
            'inventory': 0.8,        # Inventory fetches
            'default': 1.0           # Default for any other operation
        }
        
        # Get the appropriate wait time
        min_wait = min_wait_times.get(api_name, min_wait_times['default'])
        
        # Check if we need to wait
        last_request = self.last_request_time.get(api_name, 0)
        time_since_last = now - last_request
        
        if time_since_last < min_wait:
            # Calculate wait time with a small buffer
            wait_time = min_wait - time_since_last + 0.1  # Add 0.1s buffer
            
            # Add jitter to prevent synchronized requests (±10%)
            jitter = random.uniform(-0.1, 0.1) * wait_time
            adjusted_wait = max(0.1, wait_time + jitter)  # Ensure at least a minimal wait
            
            # Wait the calculated time
            await asyncio.sleep(adjusted_wait)
        
        # Update the last request time
        self.last_request_time[api_name] = time.time()
        
        # If there are too many entries in last_request_time, clean it up
        if len(self.last_request_time) > 20:
            # Keep only the most recent APIs used
            recent_apis = sorted(
                self.last_request_time.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            self.last_request_time = dict(recent_apis)

    def get_cache_stats(self):
        """
        Get statistics on cache performance.
        
        Returns:
            dict: Cache statistics
        """
        stats = {}
        total_hits = 0
        total_misses = 0
        
        for cache_type, cache in self.caches.items():
            cache_stats = cache.get_stats()
            stats[cache_type] = cache_stats
            total_hits += cache_stats["hits"]
            total_misses += cache_stats["misses"]
        
        total_requests = total_hits + total_misses
        hit_ratio = 0 if total_requests == 0 else (total_hits / total_requests)
        
        # Add aggregated statistics
        stats["total"] = {
            "hits": total_hits,
            "misses": total_misses,
            "hit_ratio": hit_ratio,
            "total_requests": total_requests,
            "cache_types": len(self.caches)
        }
        
        return stats