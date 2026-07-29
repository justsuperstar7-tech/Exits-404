import aiosqlite
from datetime import datetime, timedelta
import json
from typing import Optional, List, Dict, Any
import asyncio

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    joined_date TEXT,
                    is_banned INTEGER DEFAULT 0,
                    is_admin INTEGER DEFAULT 0,
                    referral_code TEXT UNIQUE,
                    referred_by INTEGER,
                    total_referrals INTEGER DEFAULT 0
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    date TEXT,
                    is_reply INTEGER DEFAULT 0
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    date TEXT,
                    status TEXT DEFAULT 'pending'
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS broadcast_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_sent INTEGER,
                    total_failed INTEGER,
                    date TEXT,
                    message_type TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS auto_replies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE,
                    reply TEXT,
                    is_regex INTEGER DEFAULT 0
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bad_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT UNIQUE
                )
            """)
            
            # Default settings
            default_settings = {
                'welcome_message': 'Welcome to 404 Bot! 🎉\n\nUse /help to see available commands.',
                'force_subscribe': 'False',
                'spam_protection': 'True',
                'link_filter': 'True'
            }
            
            for key, value in default_settings.items():
                await db.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, value)
                )
            
            await db.commit()
    
    async def add_user(self, user_id: int, username: str = None, 
                       first_name: str = None, last_name: str = None,
                       referred_by: int = None) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            # Check if user exists
            cursor = await db.execute(
                "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
            )
            if await cursor.fetchone():
                return False
            
            # Generate referral code
            referral_code = f"REF{user_id}{datetime.now().strftime('%m%d')}"
            
            await db.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, 
                                 joined_date, referral_code, referred_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, username, first_name, last_name,
                datetime.now().isoformat(), referral_code, referred_by
            ))
            
            if referred_by:
                await db.execute(
                    "UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id = ?",
                    (referred_by,)
                )
            
            await db.commit()
            return True
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def get_all_users(self) -> List[int]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT user_id FROM users WHERE is_banned = 0")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    
    async def get_total_users(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_banned = 0")
            row = await cursor.fetchone()
            return row[0] if row else 0
    
    async def get_today_users(self) -> int:
        today = datetime.now().date().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM users WHERE DATE(joined_date) = ? AND is_banned = 0",
                (today,)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
    
    async def ban_user(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET is_banned = 1 WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
            return True
    
    async def unban_user(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET is_banned = 0 WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
            return True
    
    async def get_setting(self, key: str) -> Optional[str]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None
    
    async def set_setting(self, key: str, value: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
            await db.commit()
    
    async def add_auto_reply(self, keyword: str, reply: str, is_regex: int = 0):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO auto_replies (keyword, reply, is_regex) VALUES (?, ?, ?)",
                (keyword, reply, is_regex)
            )
            await db.commit()
    
    async def get_auto_reply(self, message: str) -> Optional[str]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT keyword, reply, is_regex FROM auto_replies"
            )
            rows = await cursor.fetchall()
            
            for keyword, reply, is_regex in rows:
                if is_regex:
                    import re
                    if re.search(keyword, message, re.IGNORECASE):
                        return reply
                elif keyword.lower() in message.lower():
                    return reply
            return None
    
    async def add_bad_word(self, word: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO bad_words (word) VALUES (?)",
                (word.lower(),)
            )
            await db.commit()
    
    async def get_bad_words(self) -> List[str]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT word FROM bad_words")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    
    async def save_feedback(self, user_id: int, message: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO feedback (user_id, message, date) VALUES (?, ?, ?)",
                (user_id, message, datetime.now().isoformat())
            )
            await db.commit()
    
    async def get_referrals(self, user_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT total_referrals FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
    
    async def export_users_csv(self) -> str:
        import csv
        import io
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT user_id, username, first_name, last_name, joined_date, total_referrals FROM users WHERE is_banned = 0"
            )
            rows = await cursor.fetchall()
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['User ID', 'Username', 'First Name', 'Last Name', 'Joined Date', 'Total Referrals'])
            
            for row in rows:
                writer.writerow([
                    row['user_id'], row['username'], row['first_name'],
                    row['last_name'], row['joined_date'], row['total_referrals']
                ])
            
            return output.getvalue()