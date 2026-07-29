from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable
import re

from database import Database

class SpamProtectionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        db: Database = data.get('db')
        
        if not db:
            return await handler(event, data)
        
        # Check if spam protection is enabled
        spam_enabled = await db.get_setting('spam_protection')
        if spam_enabled != 'True':
            return await handler(event, data)
        
        # Check for spam patterns
        text = event.text or event.caption or ''
        if text:
            # Check for repeated messages
            if len(text) > 100 and text.count('\n') < 2:
                await event.answer("⚠️ Your message looks like spam and has been blocked.")
                return
            
            # Check for excessive caps
            caps_count = sum(1 for c in text if c.isupper())
            if len(text) > 20 and caps_count / len(text) > 0.8:
                await event.answer("⚠️ Excessive use of capital letters detected.")
                return
            
            # Check for excessive emojis
            import emoji
            emoji_count = len([c for c in text if c in emoji.EMOJI_DATA])
            if len(text) > 20 and emoji_count / len(text) > 0.5:
                await event.answer("⚠️ Excessive use of emojis detected.")
                return
        
        return await handler(event, data)