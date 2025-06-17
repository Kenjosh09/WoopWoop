"""
Inventory Manager for the Ganja Paraiso bot.
Handles product data, availability, and pricing calculations.
"""
from typing import Dict, List, Tuple, Any, Optional, Union

from ganja_paraiso_bot.config.products import PRODUCTS

class InventoryManager:
    """
    Manage product inventory with caching and efficient access patterns.
    """
    
    def __init__(self, google_apis: Any, loggers: Dict[str, Any]) -> None:
        """
        Initialize the inventory manager.
        
        Args:
            google_apis: Google APIs manager instance
            loggers: Dictionary of logger instances
        """
        self.google_apis = google_apis
        self.loggers = loggers
        self._inventory_cache: Dict[str, Any] = {}
        self._last_refresh: float = 0
        self._cache_ttl: int = 300  # 5 minutes
        
    async def get_inventory(self, force_refresh: bool = False) -> Tuple[Dict[str, List[Dict]], Dict[str, List[Dict]], List[Dict]]:
        """
        Get product inventory data with caching.
        
        Args:
            force_refresh: Force refresh the cache regardless of age
            
        Returns:
            tuple: (products_by_tag, products_by_strain, all_products)
        """
        import time
        now = time.time()
        
        # Check if we need to refresh the cache
        if force_refresh or not self._inventory_cache or now - self._last_refresh > self._cache_ttl:
            # Fetch fresh inventory data
            products_by_tag, products_by_strain, all_products = await self.google_apis.fetch_inventory()
            
            # Update cache
            self._inventory_cache = {
                "products_by_tag": products_by_tag,
                "products_by_strain": products_by_strain,
                "all_products": all_products
            }
            self._last_refresh = now
            
        # Return cached data
        return (
            self._inventory_cache.get("products_by_tag", {}),
            self._inventory_cache.get("products_by_strain", {}),
            self._inventory_cache.get("all_products", [])
        )
        
    async def get_inventory_safe(self, force_refresh=False):
        """
        Get inventory data with graceful degradation if API fails.
    
        Args:
            force_refresh (bool): Force refresh the cache regardless of age
        
        Returns:
            tuple: (products_by_tag, products_by_strain, all_products)
        """
        try:
            # First attempt - normal get_inventory with caching
            return await self.get_inventory(force_refresh)
        
        except Exception as primary_error:
            # Log the primary error
            self.loggers["errors"].error(f"Primary inventory fetch failed: {primary_error}")
        
            try:
                # Second attempt - try with default settings and no force refresh
                if force_refresh:
                    self.loggers["main"].warning("Retrying inventory fetch without force refresh")
                    # Call get_inventory directly, not get_inventory_safe to avoid recursion
                    return await self.get_inventory(False)
            
                # If we're already using cached data or defaults, raise the original error
                raise primary_error
            
            except Exception as secondary_error:
                # Log the secondary error
                self.loggers["errors"].error(f"Secondary inventory fetch failed: {secondary_error}")
                
                # Final fallback - create a minimal default inventory that won't crash the app
                self.loggers["main"].warning("Using emergency minimal inventory")
                
                # Create minimal defaults for critical categories
                products_by_tag = {'buds': [], 'local': [], 'carts': [], 'edibs': []}
                products_by_strain = {'indica': [], 'sativa': [], 'hybrid': []}
                
                # Include at least one product per category to keep the app functional
                default_product = {
                    'name': 'Default Product',
                    'key': 'default_product',
                    'price': 1000,
                    'stock': 1,
                    'tag': 'buds',
                    'strain': 'hybrid',
                }
                
                # Add the default product to each category
                for tag in products_by_tag:
                    product_copy = default_product.copy()
                    product_copy['tag'] = tag
                    products_by_tag[tag].append(product_copy)
                
                for strain in products_by_strain:
                    product_copy = default_product.copy()
                    product_copy['strain'] = strain
                    products_by_strain[strain].append(product_copy)
                
                all_products = [default_product]
                
                return products_by_tag, products_by_strain, all_products
    
    async def category_has_products(self, category):
        """
        Check if a category has any products in stock.
        Enhanced with better error handling and graceful degradation.

        Args:
            category (str): Product category key
        
        Returns:
            bool: True if category has products in stock, False otherwise
        """
        try:
            if category not in PRODUCTS:
                return False
            
            tag = PRODUCTS[category].get("tag")
            if not tag:
                return False
            
            # Use the safe inventory method
            products_by_tag, _, _ = await self.get_inventory_safe()
        
            # Get products for this category
            category_products = products_by_tag.get(tag, [])
            has_products = len(category_products) > 0
            
            # Log what we found
            print(f"DEBUG: Category '{category}' (tag: {tag}) has {len(category_products)} products available")
            
            return has_products
        
        except Exception as e:
            # Log the error
            self.loggers["errors"].error(f"Error checking products for {category}: {str(e)}")
            print(f"DEBUG ERROR in category_has_products: {str(e)}")
        
            # Return True as a fallback to avoid breaking the flow
            return True
    
    async def calculate_price(self, category, product_key, quantity):
        """
        Calculate price for a product based on category and quantity.
        Handles special pricing for local products with discounts.
        
        Args:
            category (str): Product category
            product_key (str): Product key 
            quantity (int): Quantity
            
        Returns:
            tuple: (total_price, unit_price) or (total_price, unit_price, regular_price, discount_info)
            depending on whether there's a discount
        """
        try:
            # Special case for local products with tiered pricing
            if category.lower() == "local":
                # Get base price from products configuration
                base_price = PRODUCTS["local"].get("price_per_unit", 1000)
                
                # Calculate tiered pricing for Local (BG)
                if quantity >= 300:  # 300g tier
                    price_per_gram = 500  # P500 per gram at 300g level
                    total_price = quantity * price_per_gram
                    regular_price = quantity * base_price
                    discount_info = f"(50% volume discount)"
                    return total_price, price_per_gram, regular_price, discount_info
                    
                elif quantity >= 100:  # 100g tier
                    price_per_gram = 600  # P600 per gram at 100g level
                    total_price = quantity * price_per_gram
                    regular_price = quantity * base_price
                    discount_info = f"(40% volume discount)"
                    return total_price, price_per_gram, regular_price, discount_info
                    
                elif quantity >= 50:  # 50g tier
                    price_per_gram = 700  # P700 per gram at 50g level
                    total_price = quantity * price_per_gram
                    regular_price = quantity * base_price
                    discount_info = f"(30% volume discount)"
                    return total_price, price_per_gram, regular_price, discount_info
                    
                else:  # Regular price
                    total_price = quantity * base_price
                    return total_price, base_price
            
            # For other product categories
            products_by_tag, products_by_strain, all_products = await self.get_inventory_safe()
            
            # Find the product using its key
            product = None
            for p in all_products:
                if p.get('key') == product_key or p.get('name').lower().replace(' ', '_') == product_key:
                    product = p
                    break
            
            # If product found, calculate price
            if product and 'price' in product:
                unit_price = product['price']
                total_price = unit_price * quantity
                return total_price, unit_price
            
            # Fallback: if product not found
            self.loggers["errors"].warning(f"Product not found for price calculation: {category}/{product_key}")
            
            # Use category default price as fallback
            fallback_price = 0
            if category in PRODUCTS and hasattr(PRODUCTS[category], "price_per_unit"):
                fallback_price = PRODUCTS[category]["price_per_unit"]
            else:
                # Ultimate fallback: use 1000 as default price
                fallback_price = 1000
                
            total_price = fallback_price * quantity
            return total_price, fallback_price
            
        except Exception as e:
            # Log the error
            self.loggers["errors"].error(f"Error calculating price: {str(e)}")
            
            # Return a safe fallback price to avoid breaking the order flow
            fallback_unit_price = 1000
            fallback_total = fallback_unit_price * quantity
            return fallback_total, fallback_unit_price

    async def get_product_details(self, category, product_key=None, strain_type=None):
        """
        Get detailed information about a specific product.
        
        Args:
            category (str): Product category
            product_key (str, optional): Specific product key
            strain_type (str, optional): Strain type (indica, sativa, hybrid)
            
        Returns:
            dict: Product details or None if not found
        """
        try:
            products_by_tag, products_by_strain, all_products = await self.get_inventory_safe()
            
            # If looking for a specific product by key
            if product_key:
                for product in all_products:
                    if (product.get('key') == product_key or 
                        product.get('name', '').lower().replace(' ', '_') == product_key):
                        return product
            
            # If looking for products by category and strain
            if category in PRODUCTS and strain_type:
                tag = PRODUCTS[category].get("tag")
                if tag and tag in products_by_tag:
                    matching_products = [
                        p for p in products_by_tag[tag] 
                        if p.get('strain', '').lower() == strain_type.lower()
                    ]
                    if matching_products:
                        return matching_products[0]  # Return first matching product
            
            # If looking for products by category only
            if category in PRODUCTS:
                tag = PRODUCTS[category].get("tag")
                if tag and tag in products_by_tag and products_by_tag[tag]:
                    return products_by_tag[tag][0]  # Return first product in category
            
            return None
        
        except Exception as e:
            self.loggers["errors"].error(f"Error getting product details: {str(e)}")
            return None

    def get_available_categories(self):
        """
        Get list of available product categories.
        
        Returns:
            list: List of category IDs
        """
        # Get all categories from the PRODUCTS config
        return list(PRODUCTS.keys())