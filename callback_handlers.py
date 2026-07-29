from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

router = Router()

@router.callback_query(F.data == "profile_referral")
async def profile_referral(callback: types.CallbackQuery, db):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await callback.answer("❌ User not found!", show_alert=True)
        return
    
    referrals = await db.get_referrals(user_id)
    
    await callback.answer(
        f"📊 Your Referrals: {referrals}\n"
        f"🔗 Referral Code: {user['referral_code']}",
        show_alert=True
    )

@router.callback_query(F.data == "profile_settings")
async def profile_settings(callback: types.CallbackQuery):
    # Show settings options
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 Back to Profile", callback_data="profile_back")]
    ])
    
    await callback.message.edit_text(
        "⚙️ <b>Settings</b>\n\n"
        "No personal settings available yet.",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data == "profile_back")
async def profile_back(callback: types.CallbackQuery, db):
    from handlers.user_handlers import profile_command
    await profile_command(callback.message, db)
    await callback.answer()