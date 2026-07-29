import logging
from datetime import datetime
import sys
from config import Config

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from libraries
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)

def is_admin(user_id: int) -> bool:
    return user_id == Config.OWNER_ID

def format_stats(stats: dict) -> str:
    return f"""
<b>📊 Bot Statistics</b>

👥 Total Users: {stats['total_users']}
📈 Today Users: {stats['today_users']}
⏱ Uptime: {stats['uptime']}
"""

def validate_token(token: str) -> bool:
    return token and token.startswith('7') and len(token) > 20

def get_bot_version() -> str:
    return "1.0.0"

def format_time(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"