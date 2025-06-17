"""
Health check middleware for the Ganja Paraiso bot.
Monitors response times and detects when the bot becomes unresponsive.
"""
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any

from telegram import Bot, Update
from telegram.ext import BaseHandler

class HealthCheckMiddleware(BaseHandler):
    """Middleware to track response times and detect when the bot becomes unresponsive."""
    
    def __init__(self, bot: Bot, admin_ids: List[int], loggers: Dict[str, Any]):
        """
        Initialize the health check middleware.
        
        Args:
            bot: Telegram bot instance
            admin_ids: List of admin IDs to notify on issues
            loggers: Dictionary of logger instances
        """
        super().__init__(self.on_pre_process_update)
        self.bot = bot
        self.admin_ids = admin_ids
        self.loggers = loggers
        self.response_times = []
        self.max_response_times = 100  # Keep last 100 response times
        self.last_health_check = time.time()
        self.watchdog_task = None
        self.is_healthy = True
        
        # Start the watchdog
        self.start_watchdog()
    
    async def on_pre_process_update(self, update: Update, data: dict):
        """
        Process an update before it's handled.
        
        Args:
            update: Telegram update
            data: Additional data
            
        Returns:
            dict: Updated data
        """
        # Add timestamp to track processing time
        data["health_check_start_time"] = time.time()
        return data
    
    async def on_post_process_update(self, update: Update, result, data: dict):
        """
        Process an update after it's handled.
        
        Args:
            update: Telegram update
            result: Handler result
            data: Additional data
            
        Returns:
            Any: Handler result
        """
        # Calculate response time if we have a start time
        if "health_check_start_time" in data:
            start_time = data["health_check_start_time"]
            response_time = time.time() - start_time
            
            # Track response time
            self.response_times.append(response_time)
            
            # Keep only the last N response times
            if len(self.response_times) > self.max_response_times:
                self.response_times = self.response_times[-self.max_response_times:]
            
            # Log slow responses (> 2 seconds)
            if response_time > 2:
                update_type = "message" if update.message else "callback" if update.callback_query else "other"
                self.loggers["performance"].warning(
                    f"Slow response: {response_time:.2f}s for {update_type} update"
                )
                
                # Additional debugging for very slow responses
                if response_time > 5:
                    update_text = update.message.text if update.message and update.message.text else "No text"
                    callback_data = update.callback_query.data if update.callback_query else "No callback"
                    self.loggers["performance"].warning(
                        f"Very slow response: {response_time:.2f}s, "
                        f"update text: {update_text}, callback: {callback_data}"
                    )
        
        return result
    
    def start_watchdog(self):
        """Start the watchdog timer to monitor bot health."""
        async def watchdog_check():
            """Check bot health periodically."""
            while True:
                try:
                    await asyncio.sleep(60)  # Check every minute
                    
                    now = time.time()
                    
                    # If no updates in 10 minutes, log a warning
                    if not self.response_times and now - self.last_health_check > 600:
                        self.loggers["performance"].warning("No updates processed in the last 10 minutes")
                    
                    # Calculate average response time
                    if self.response_times:
                        avg_response_time = sum(self.response_times) / len(self.response_times)
                        
                        # Log if response times are concerning
                        if avg_response_time > 1.5:
                            self.loggers["performance"].warning(
                                f"High average response time: {avg_response_time:.2f}s"
                            )
                        
                        # Check if bot is becoming unhealthy
                        if avg_response_time > 3 and self.is_healthy:
                            self.is_healthy = False
                            
                            # Alert admins
                            await self.alert_admins(
                                f"🔴 Bot health warning: High response times ({avg_response_time:.2f}s)"
                            )
                        
                        # Bot has recovered
                        elif avg_response_time < 1 and not self.is_healthy:
                            self.is_healthy = True
                            
                            # Alert admins about recovery
                            await self.alert_admins(
                                f"🟢 Bot has recovered: Response times normalized ({avg_response_time:.2f}s)"
                            )
                    
                    # Update last health check time
                    self.last_health_check = now
                    
                except Exception as e:
                    # Log errors in the watchdog itself
                    self.loggers["errors"].error(f"Error in health check watchdog: {e}")
        
        # Start the watchdog task
        self.watchdog_task = asyncio.create_task(watchdog_check())
    
    async def alert_admins(self, message: str):
        """
        Send an alert to all admins.
        
        Args:
            message: Alert message
        """
        # Log the alert
        self.loggers["performance"].warning(message)
        
        # Only alert admins once an hour at most, except for critical alerts
        if "critical" not in message.lower() and time.time() - self.last_health_check < 3600:
            return
            
        # Send message to all admins
        for admin_id in self.admin_ids:
            try:
                await self.bot.send_message(chat_id=admin_id, text=message)
            except Exception as e:
                self.loggers["errors"].error(f"Failed to alert admin {admin_id}: {e}")