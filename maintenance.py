from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable

from config import Config

class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        if Config.MAINTENANCE_MODE:
            user_id = event.from_user.id
            
            # Allow owner access
            if user_id != Config.OWNER_ID:
                if isinstance(event, Message):
                    await event.answer("🔧 Bot is under maintenance. Please try again later.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("🔧 Bot is under maintenance.", show_alert=True)
                return
        
        return await handler(event, data)