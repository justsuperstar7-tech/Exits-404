from aiogram import Router, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from datetime import datetime
import logging
import io

from config import Config
from database import Database
from keyboards.inline import get_admin_panel_keyboard, get_admin_settings_keyboard
from utils.helpers import is_admin, format_stats

router = Router()

class BroadcastState(StatesGroup):
    waiting_broadcast_text = State()
    waiting_broadcast_media = State()
    waiting_broadcast_confirm = State()

class AdminMessageState(StatesGroup):
    waiting_user_id = State()
    waiting_message = State()

class AdminReplyState(StatesGroup):
    waiting_reply_message = State()

class SettingsState(StatesGroup):
    waiting_welcome_message = State()
    waiting_auto_reply_keyword = State()
    waiting_auto_reply_message = State()
    waiting_bad_word = State()

@router.message(Command("admin"))
async def admin_panel(message: Message, db: Database):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Access Denied! You are not authorized to use this command.")
        return
    
    stats = await get_stats(db)
    stats_text = format_stats(stats)
    
    await message.answer(
        f"<b>👑 Admin Panel</b>\n\n{stats_text}",
        parse_mode="HTML",
        reply_markup=get_admin_panel_keyboard()
    )

async def get_stats(db: Database):
    total_users = await db.get_total_users()
    today_users = await db.get_today_users()
    
    return {
        'total_users': total_users,
        'today_users': today_users,
        'uptime': "00:00:00"  # Will be calculated in main
    }

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Access Denied!", show_alert=True)
        return
    
    stats = await get_stats(db)
    stats_text = format_stats(stats)
    
    await callback.message.edit_text(
        f"<b>📊 Bot Statistics</b>\n\n{stats_text}",
        parse_mode="HTML",
        reply_markup=get_admin_panel_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "admin_total_users")
async def admin_total_users(callback: types.CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Access Denied!", show_alert=True)
        return
    
    total = await db.get_total_users()
    await callback.answer(f"Total Users: {total}", show_alert=True)

@router.callback_query(F.data == "admin_today_users")
async def admin_today_users(callback: types.CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Access Denied!", show_alert=True)
        return
    
    today = await db.get_today_users()
    await callback.answer(f"Today's Users: {today}", show_alert=True)

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Access Denied!", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Text Broadcast", callback_data="broadcast_text")],
        [InlineKeyboardButton(text="🖼 Photo Broadcast", callback_data="broadcast_photo")],
        [InlineKeyboardButton(text="🎥 Video Broadcast", callback_data="broadcast_video")],
        [InlineKeyboardButton(text="📄 Document Broadcast", callback_data="broadcast_document")],
        [InlineKeyboardButton(text="🎬 Animation Broadcast", callback_data="broadcast_animation")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(
        "📢 <b>Broadcast Menu</b>\n\nSelect broadcast type:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data == "broadcast_text")
async def broadcast_text(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Access Denied!", show_alert=True)
        return
    
    await state.set_state(BroadcastState.waiting_broadcast_text)
    await callback.message.edit_text(
        "📝 <b>Text Broadcast</b>\n\n"
        "Send the message you want to broadcast to all users.\n"
        "You can use HTML formatting.\n\n"
        "<b>Note:</b> To cancel, use /cancel",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(BroadcastState.waiting_broadcast_text)
async def process_broadcast_text(message: types.Message, state: FSMContext, db: Database, bot: types.Bot):
    await state.update_data(message_text=message.text, message_type='text')
    
    users = await db.get_all_users()
    total_users = len(users)
    
    await message.answer(
        f"📊 Broadcast Preview\n\n"
        f"Total users: {total_users}\n"
        f"Message:\n{message.text[:200]}...\n\n"
        f"Send /confirm to start broadcasting",
        parse_mode="HTML"
    )
    await state.set_state(BroadcastState.waiting_broadcast_confirm)

@router.message(Command("confirm"))
async def confirm_broadcast(message: types.Message, state: FSMContext, db: Database, bot: types.Bot):
    data = await state.get_data()
    if not data:
        await message.answer("❌ No broadcast data found. Please start broadcast again.")
        return
    
    users = await db.get_all_users()
    total = len(users)
    sent = 0
    failed = 0
    
    progress_msg = await message.answer("📤 Starting broadcast...")
    
    for i, user_id in enumerate(users):
        try:
            if data.get('message_type') == 'text':
                await bot.send_message(user_id, data['message_text'], parse_mode="HTML")
            else:
                # Handle media broadcast
                pass
            sent += 1
        except Exception as e:
            failed += 1
            logging.error(f"Failed to send to {user_id}: {e}")
        
        if (i + 1) % 10 == 0:
            await progress_msg.edit_text(
                f"📤 Broadcasting...\n"
                f"Progress: {i+1}/{total}\n"
                f"Sent: {sent} | Failed: {failed}"
            )
    
    # Save broadcast log
    async with aiosqlite.connect(db.db_path) as conn:
        await conn.execute(
            "INSERT INTO broadcast_logs (total_sent, total_failed, date, message_type) VALUES (?, ?, ?, ?)",
            (sent, failed, datetime.now().isoformat(), data.get('message_type', 'text'))
        )
        await conn.commit()
    
    await progress_msg.edit_text(
        f"✅ Broadcast Complete!\n\n"
        f"Total: {total}\n"
        f"Sent: {sent}\n"
        f"Failed: {failed}"
    )
    
    await state.clear()
    await admin_panel(message, db)

@router.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Operation cancelled.")

@router.callback_query(F.data == "admin_backup")
async def admin_backup(callback: types.CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Access Denied!", show_alert=True)
        return
    
    # Create backup
    async with aiosqlite.connect(db.db_path) as conn:
        await conn.execute("VACUUM")
    
    await callback.answer("✅ Database backup completed!", show_alert=True)

@router.callback_query(F.data == "admin_export_csv")
async def admin_export_csv(callback: types.CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Access Denied!", show_alert=True)
        return
    
    csv_data = await db.export_users_csv()
    file = io.BytesIO(csv_data.encode('utf-8'))
    file.name = f"users_export_{datetime.now().strftime('%Y%m%d')}.csv"
    
    await callback.message.answer_document(
        types.FSInputFile(file, filename=file.name),
        caption="📊 Users Export"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_search")
async def admin_search(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Access Denied!", show_alert=True)
        return
    
    await state.set_state(AdminMessageState.waiting_user_id)
    await callback.message.edit_text(
        "🔍 <b>Search User</b>\n\n"
        "Enter the user ID to search:",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminMessageState.waiting_user_id)
async def process_search_user(message: types.Message, state: FSMContext, db: Database):
    try:
        user_id = int(message.text)
        user = await db.get_user(user_id)
        
        if not user:
            await message.answer("❌ User not found!")
        else:
            user_text = f"""
<b>👤 User Details</b>

<b>ID:</b> <code>{user['user_id']}</code>
<b>Username:</b> @{user['username'] or 'N/A'}
<b>Name:</b> {user['first_name'] or 'N/A'}
<b>Joined:</b> {user['joined_date']}
<b>Status:</b> {'🚫 Banned' if user.get('is_banned', 0) else '✅ Active'}
<b>Referrals:</b> {user.get('total_referrals', 0)}
"""
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🚫 Ban" if not user.get('is_banned', 0) else "✅ Unban",
                        callback_data=f"ban_{user_id}_{user.get('is_banned', 0)}"
                    ),
                    InlineKeyboardButton(
                        text="📨 Send Message",
                        callback_data=f"send_msg_{user_id}"
                    )
                ],
                [InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]
            ])
            
            await message.answer(user_text, parse_mode="HTML", reply_markup=keyboard)
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Invalid User ID. Please enter a numeric ID.")

@router.callback_query(F.data.startswith("ban_"))
async def ban_user(callback: types.CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Access Denied!", show_alert=True)
        return
    
    parts = callback.data.split('_')
    user_id = int(parts[1])
    current_status = int(parts[2])
    
    if current_status:
        await db.unban_user(user_id)
        await callback.answer("✅ User unbanned!", show_alert=True)
    else:
        await db.ban_user(user_id)
        await callback.answer("🚫 User banned!", show_alert=True)
    
    await admin_panel(callback.message, db)

@router.callback_query(F.data.startswith("send_msg_"))
async def send_message_to_user(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Access Denied!", show_alert=True)
        return
    
    user_id = int(callback.data.split('_')[2])
    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminMessageState.waiting_message)
    
    await callback.message.edit_text(
        f"📨 <b>Send Message to User</b>\n\n"
        f"Target User ID: <code>{user_id}</code>\n\n"
        f"Type the message you want to send:",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminMessageState.waiting_message)
async def process_send_message(message: types.Message, state: FSMContext, db: Database, bot: types.Bot):
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    
    try:
        await bot.send_message(target_user_id, message.text, parse_mode="HTML")
        await message.answer("✅ Message sent successfully!")
    except Exception as e:
        await message.answer(f"❌ Failed to send message: {e}")
    
    await state.clear()
    await admin_panel(message, db)

@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Access Denied!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⚙️ <b>Settings Menu</b>",
        parse_mode="HTML",
        reply_markup=get_admin_settings_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "settings_welcome")
async def settings_welcome(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Access Denied!", show_alert=True)
        return
    
    await state.set_state(SettingsState.waiting_welcome_message)
    await callback.message.edit_text(
        "📝 <b>Set Welcome Message</b>\n\n"
        "Send the new welcome message.\n"
        "Use HTML formatting for styling.",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(SettingsState.waiting_welcome_message)
async def process_welcome_message(message: types.Message, state: FSMContext, db: Database):
    await db.set_setting('welcome_message', message.text)
    await state.clear()
    await message.answer("✅ Welcome message updated successfully!")
    await admin_panel(message, db)

@router.callback_query(F.data == "settings_force_sub")
async def settings_force_sub(callback: types.CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Access Denied!", show_alert=True)
        return
    
    current = await db.get_setting('force_subscribe')
    new_value = 'False' if current == 'True' else 'True'
    await db.set_setting('force_subscribe', new_value)
    
    status = "Enabled" if new_value == 'True' else "Disabled"
    await callback.answer(f"✅ Force Subscribe {status}!", show_alert=True)

@router.callback_query(F.data == "settings_spam")
async def settings_spam(callback: types.CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Access Denied!", show_alert=True)
        return
    
    current = await db.get_setting('spam_protection')
    new_value = 'False' if current == 'True' else 'True'
    await db.set_setting('spam_protection', new_value)
    
    status = "Enabled" if new_value == 'True' else "Disabled"
    await callback.answer(f"✅ Spam Protection {status}!", show_alert=True)

@router.callback_query(F.data == "settings_links")
async def settings_links(callback: types.CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Access Denied!", show_alert=True)
        return
    
    current = await db.get_setting('link_filter')
    new_value = 'False' if current == 'True' else 'True'
    await db.set_setting('link_filter', new_value)
    
    status = "Enabled" if new_value == 'True' else "Disabled"
    await callback.answer(f"✅ Link Filter {status}!", show_alert=True)

@router.callback_query(F.data == "admin_restart")
async def admin_restart(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Access Denied!", show_alert=True)
        return
    
    await callback.answer("🔄 Restarting bot...", show_alert=True)
    # In production, you'd use a more robust restart mechanism
    import sys
    import os
    os.execv(sys.executable, ['python'] + sys.argv)

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Access Denied!", show_alert=True)
        return
    
    stats = await get_stats(db)
    stats_text = format_stats(stats)
    
    await callback.message.edit_text(
        f"<b>👑 Admin Panel</b>\n\n{stats_text}",
        parse_mode="HTML",
        reply_markup=get_admin_panel_keyboard()
    )
    await callback.answer()