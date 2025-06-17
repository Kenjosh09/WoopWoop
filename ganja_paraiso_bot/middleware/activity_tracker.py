"""
Activity tracking middleware for the Ganja Paraiso bot.
"""
import time
from typing import Dict, Any

from telegram import Update
from telegram.ext import BaseHandler

class ActivityTrackerMiddleware(BaseHandler):
    """Middleware to track user activity timestamps."""
    
    def __init__(self):
        """Initialize the activity tracker middleware."""
        super().__init__(self.on_pre_process_update)
    
    async def on_pre_process_update(self, update: Update, data: dict):
        """
        Process an update to track user activity.
        
        Args:
            update: Telegram update
            data: Additional data
            
        Returns:
            dict: Updated data
        """
        # Get user ID from update
        user_id = None
        
        if update.effective_user:
            user_id = update.effective_user.id
        
        # If we have a user ID, update their activity timestamp
        if user_id:
            # Get the context from data
            context = data.get("context")
            
            if context:
                # Ensure sessions dictionary exists
                if "sessions" not in context.bot_data:
                    context.bot_data["sessions"] = {}
                
                # Ensure this user has a session
                if user_id not in context.bot_data["sessions"]:
                    context.bot_data["sessions"][user_id] = {}
                
                # Update last activity time
                now = time.time()
                context.bot_data["sessions"][user_id]["last_activity"] = now
                
                # Also update user_data if it exists for this user
                if user_id in context.user_data:
                    context.user_data[user_id]["last_activity_time"] = now
        
        return data