"""
Enhanced caching system for improved performance.
"""
import time
from collections import deque

class EnhancedCache:
    """
    Enhanced caching system with dynamic TTL and LRU eviction.
    """
    
    def __init__(self, max_items=100):
        """
        Initialize the enhanced cache.
        
        Args:
            max_items (int): Maximum number of items to cache
        """
        self.cache = {}
        self.access_order = deque(maxlen=max_items)
        self.hits = 0
        self.misses = 0
        self.max_items = max_items
        self.default_ttl = 60  # Default TTL is 60 seconds
    
    def get(self, key, default_ttl=None):
        """
        Get a value from cache with freshness check.
        
        Args:
            key (str): Cache key
            default_ttl (int, optional): TTL to use if not specified in item
            
        Returns:
            tuple: (is_hit, cached_value)
        """
        if key not in self.cache:
            self.misses += 1
            return False, None
        
        # Get the cache entry
        entry = self.cache[key]
        now = time.time()
        ttl = entry.get("ttl", default_ttl or self.default_ttl)
        
        # Check if expired
        if now - entry.get("timestamp", 0) > ttl:
            # Remove the expired entry
            self._remove_entry(key)
            self.misses += 1
            return False, None
        
        # Update access order (LRU behavior)
        self._update_access_order(key)
        
        # Record the hit
        self.hits += 1
        return True, entry.get("data")
    
    def set(self, key, value, ttl=None):
        """
        Set a value in cache with specified TTL.
        
        Args:
            key (str): Cache key
            value: Value to cache
            ttl (int, optional): Time-to-live in seconds
            
        Returns:
            value: The cached value
        """
        # If cache is full, evict least recently used item
        if len(self.cache) >= self.max_items and key not in self.cache:
            self._evict_lru()
        
        # Store the value
        self.cache[key] = {
            "data": value,
            "timestamp": time.time(),
            "ttl": ttl or self.default_ttl
        }
        
        # Update access order
        self._update_access_order(key)
        
        return value
    
    def _update_access_order(self, key):
        """Update the access order for LRU tracking."""
        # Remove key if it exists and add it to the end (most recently used)
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)
    
    def _remove_entry(self, key):
        """Remove a cache entry."""
        if key in self.cache:
            del self.cache[key]
        if key in self.access_order:
            self.access_order.remove(key)
    
    def _evict_lru(self):
        """Evict the least recently used cache entry."""
        if self.access_order:
            lru_key = self.access_order[0]
            self._remove_entry(lru_key)
    
    def clear(self, key=None):
        """
        Clear a specific key or the entire cache.
        
        Args:
            key (str, optional): Specific key to clear, or None to clear all
        """
        if key:
            if key in self.cache:
                del self.cache[key]
                if key in self.access_order:
                    self.access_order.remove(key)
        else:
            self.cache.clear()
            self.access_order.clear()
    
    def get_stats(self):
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_ratio = 0 if total_requests == 0 else (self.hits / total_requests)
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": hit_ratio,
            "total_requests": total_requests,
            "items": len(self.cache),
            "max_items": self.max_items
        }