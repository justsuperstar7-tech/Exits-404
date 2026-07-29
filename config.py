import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("8957575409:AAFYA-Ve7ZO2vUl3ExtBEDcnouBsAh938j4")
    OWNER_ID = int(os.getenv("8653084707", 0))
    DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_data.db")
    MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "False").lower() == "true"
    
    # Bot settings
    ADMIN_IDS = [OWNER_ID]
    FLOOD_TIME = 1  # seconds
    MAX_MESSAGE_LENGTH = 4096