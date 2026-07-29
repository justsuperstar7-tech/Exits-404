from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from datetime import datetime
import logging

from database import Database
from keyboards.inline import (
    get_main_menu_keyboard,
    get_profile_keyboard,
    get_contact_admin_keyboard,
    get_settings_keyboard
)

router = Router()

class FeedbackState(StatesGroup):
    waiting_feedback = State()

class ContactState(StatesGroup):
    waiting_message = State()

@router.message(CommandStart())
async def start_command(message: Message, db: Database):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Check if user is banned
    user = await db.get_user(user_id)
    if user and user.get('is_banned', 0) == 1:
        await message.answer("🚫 You are banned from using this bot.")
        return
    
    # Add user to database
    is_new = await db.add_user(user_id, username, first_name, last_name)
    
    # Handle referral
    if is_new and message.text and ' ' in message.text:
        ref_code = message.text.split(' ', 1)[1]
        if ref_code.startswith('REF'):
            # Find referrer
            async with aiosqlite.connect(db.db_path) as conn:
                cursor = await conn.execute(
                    "SELECT user_id FROM users WHERE referral_code = ?",
                    (ref_code,)
                )
                row = await cursor.fetchone()
                if row:
                    referrer_id = row[0]
                    await db.add_user(user_id, username, first_name, last_name, referrer_id)
    
    # Get welcome message
    welcome_msg = await db.get_setting('welcome_message') or "Welcome to 404 Bot! 🎉\n\nUse /help to see available commands."
    
    # Check force subscribe
    force_sub = await db.get_setting('force_subscribe')
    if force_sub == 'True':
        # For demonstration, we'll just show a message
        await message.answer(
            f"{welcome_msg}\n\n📢 <b>Please join our channel to continue:</b>\nhttps://t.me/your_channel",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(welcome_msg, reply_markup=get_main_menu_keyboard())

@router.message(Command("help"))
async def help_command(message: Message):
    help_text = """
<b>🤖 404 Bot Help</b>

<b>📋 Available Commands:</b>
/start - Start the bot
/help - Show this help message
/ping - Check bot status
/profile - View your profile

<b>🛠 Features:</b>
• 📊 Referral System
• 📝 Feedback System
• 📨 Contact Admin

<b>ℹ️ About:</b>
This bot is designed to help you manage your community effectively.
"""
    await message.answer(help_text, parse_mode="HTML")

@router.message(Command("ping"))
async def ping_command(message: Message):
    import time
    start_time = time.time()
    await message.answer("🏓 Pong!")
    end_time = time.time()
    await message.answer(f"⏱ Response time: {round((end_time - start_time) * 1000)}ms")

@router.message(Command("profile"))
async def profile_command(message: Message, db: Database):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("❌ User not found. Please use /start first.")
        return
    
    referrals = await db.get_referrals(user_id)
    
    profile_text = f"""
<b>👤 Profile</b>

<b>ID:</b> <code>{user['user_id']}</code>
<b>Username:</b> @{user['username'] or 'N/A'}
<b>Name:</b> {user['first_name'] or 'N/A'} {user['last_name'] or ''}
<b>Joined:</b> {user['joined_date']}
<b>Referrals:</b> {referrals}
<b>Referral Code:</b> <code>{user['referral_code']}</code>
"""
    await message.answer(profile_text, parse_mode="HTML", reply_markup=get_profile_keyboard())

@router.message(Command("feedback"))
async def feedback_command(message: Message, state: FSMContext):
    await state.set_state(FeedbackState.waiting_feedback)
    await message.answer(
        "✍️ Please send your feedback message.\n\n"
        "You can write suggestions, bug reports, or any other feedback."
    )

@router.message(FeedbackState.waiting_feedback)
async def process_feedback(message: Message, state: FSMContext, db: Database):
    await db.save_feedback(message.from_user.id, message.text)
    await state.clear()
    await message.answer("✅ Thank you for your feedback! We appreciate it.")

@router.message(F.text == "📊 Profile")
async def profile_button(message: Message, db: Database):
    await profile_command(message, db)

@router.message(F.text == "📝 Feedback")
async def feedback_button(message: Message, state: FSMContext):
    await feedback_command(message, state)

@router.message(F.text == "📨 Contact Admin")
async def contact_admin_button(message: Message, state: FSMContext):
    await state.set_state(ContactState.waiting_message)
    await message.answer(
        "📨 Send your message to admin.\n\n"
        "Please describe your issue or question clearly."
    )

@router.message(ContactState.waiting_message)
async def process_contact(message: Message, state: FSMContext, db: Database, bot: types.Bot):
    from config import Config
    
    owner_id = Config.OWNER_ID
    user = message.from_user
    
    contact_text = f"""
<b>📨 New Contact Message</b>

<b>From:</b> {user.full_name}
<b>Username:</b> @{user.username or 'N/A'}
<b>User ID:</b> <code>{user.id}</code>

<b>Message:</b>
{message.text}
"""
    await bot.send_message(owner_id, contact_text, parse_mode="HTML")
    await state.clear()
    await message.answer("✅ Your message has been sent to the admin!")

@router.message(F.text == "🔙 Back to Menu")
async def back_to_menu(message: Message):
    await message.answer("Main Menu:", reply_markup=get_main_menu_keyboard())

@router.message(F.text)
async def auto_reply_handler(message: Message, db: Database):
    if message.text and not message.text.startswith('/'):
        # Check for auto reply
        reply = await db.get_auto_reply(message.text)
        if reply:
            await message.answer(reply)
            return
        
        # Check for bad words
        bad_words = await db.get_bad_words()
        if bad_words:
            text_lower = message.text.lower()
            for word in bad_words:
                if word in text_lower:
                    await message.delete()
                    await message.answer("⚠️ Your message contains inappropriate content and has been deleted.")
                    return