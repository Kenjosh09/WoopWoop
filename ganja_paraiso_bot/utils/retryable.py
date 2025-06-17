"""
Utilities for handling retryable operations with backoff and error handling.
"""
import asyncio
import random
from typing import Callable, Any, Tuple, Dict

class RetryableOperation:
    """
    A class to encapsulate retryable async operations with advanced error handling.
    """
    
    def __init__(self, loggers, max_retries=3, base_delay=1.0, 
                 retry_on=(ConnectionError, TimeoutError), jitter=True):
        """
        Initialize a retryable operation.
        
        Args:
            loggers (dict): Dictionary of logger instances
            max_retries (int): Maximum number of retry attempts
            base_delay (float): Base delay between retries in seconds
            retry_on (tuple): Exceptions that should trigger a retry
            jitter (bool): Whether to add randomness to retry delays
        """
        self.loggers = loggers
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.retry_on = retry_on
        self.use_jitter = jitter
    
    async def run(self, operation_func, operation_name=None, *args, **kwargs):
        """
        Execute an async operation with retry logic.
        
        Args:
            operation_func (callable): Async function to execute
            operation_name (str, optional): Name for logging purposes
            *args: Arguments to pass to operation_func
            **kwargs: Keyword arguments to pass to operation_func
            
        Returns:
            Any: Result from the successful operation
            
        Raises:
            Exception: The last exception if all retries fail
        """
        if not operation_name:
            operation_name = getattr(operation_func, "__name__", "unknown_operation")
        
        retry_count = 0
        last_exception = None
        
        while retry_count <= self.max_retries:
            try:
                # Attempt the operation
                result = await operation_func(*args, **kwargs)
                return result
                
            except self.retry_on as e:
                # This is a retryable error
                retry_count += 1
                last_exception = e
                
                if retry_count > self.max_retries:
                    self.loggers["errors"].error(
                        f"Operation '{operation_name}' failed after {retry_count} attempts: {e}"
                    )
                    break
                
                # Calculate delay with exponential backoff
                delay = min(self.base_delay * (2 ** (retry_count - 1)), 60)  # Cap at 60 seconds
                
                # Add jitter if enabled (helps prevent thundering herd problem)
                if self.use_jitter:
                    jitter_amount = random.uniform(0, 0.5 * delay)
                    delay += jitter_amount
                
                self.loggers["main"].warning(
                    f"Operation '{operation_name}' attempt {retry_count}/{self.max_retries} "
                    f"failed: {e}. Retrying in {delay:.2f} seconds."
                )
                await asyncio.sleep(delay)
                
            except Exception as e:
                # Non-retryable error
                self.loggers["errors"].error(
                    f"Non-retryable error in operation '{operation_name}': {type(e).__name__}: {e}"
                )
                raise
        
        # If we get here, all retries failed
        raise last_exception or RuntimeError(f"Operation '{operation_name}' failed for unknown reasons")

async def retry_operation(operation, operation_name=None, max_retries=3, loggers=None):
    """
    Retry an async operation with exponential backoff.
    
    This function is a simpler wrapper around RetryableOperation for backward
    compatibility with existing code.
    
    Args:
        operation (callable): Async function to retry
        operation_name (str, optional): Name of operation for logging
        max_retries (int): Maximum number of retry attempts
        loggers (dict, optional): Dictionary of logger instances
        
    Returns:
        Any: Result from the operation
        
    Raises:
        Exception: The last exception encountered after all retries
    """
    # Use simple defaults if no loggers provided
    if not loggers:
        loggers = {
            "errors": print,
            "main": print
        }
    
    retry_handler = RetryableOperation(
        loggers, 
        max_retries=max_retries,
        retry_on=(ConnectionError, TimeoutError, BrokenPipeError)
    )
    
    return await retry_handler.run(operation, operation_name)