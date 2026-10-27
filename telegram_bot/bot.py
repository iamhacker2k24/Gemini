import os
import sys
import time
import re
import threading
from datetime import datetime
import telebot
from telebot import types

import config
import database as db
import internshala_engine as engine

# Initialize Database
db.init_db()

# Check Bot Token
if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    print("=" * 60)
    print("⚠️ WARNING: BOT_TOKEN is not configured in telegram_bot/.env!")
    print("Please open telegram_bot/.env and put your Telegram Bot Token from @BotFather.")
    print("=" * 60)

bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="HTML")

# In-memory user states for multi-step interactions
USER_STATES = {}
ADMIN_BROADCAST_DRAFT = {}


# LOGGING & PRIVATE AUDIT CHANNEL

def log_to_channel(text: str):
    """Sends event logs, user registrations, referral counts, and claims to the private log channel."""
    channel_id = config.LOG_CHANNEL_ID
    if channel_id:
        try:
            bot.send_message(channel_id, text, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            print(f"[!] Warning: Failed to send log to channel {channel_id}: {e}")
            print(f"[!] Tip: Ensure your bot is added as an ADMINISTRATOR in channel {channel_id} with 'Post Messages' permission enabled!")

# Alias for backward compatibility
log_to_group = log_to_channel


# HELPER FUNCTIONS

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


def get_progress_bar(current: int, total: int, length: int = 10) -> str:
    if total <= 0:
        return "░" * length
    fraction = min(1.0, current / total)
    filled = int(fraction * length)
    return "█" * filled + "░" * (length - filled)


def check_user_joined(user_id: int) -> tuple[bool, list]:
    """
    Checks if a user is member of all required channels.
    Returns (is_joined: bool, missing_channels: list)
    """
    if not db.is_force_join_enabled():
        return True, []

    channels = db.get_required_channels()
    if not channels:
        return True, []

    missing = []
    for ch in channels:
        chat_id = ch["chat_id"]
        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status not in ["creator", "administrator", "member", "restricted"]:
                missing.append(ch)
        except Exception as e:
            # If bot is not admin in channel or error, allow through or log
            print(f"[!] Warning checking membership in {chat_id}: {e}")
            pass

    return (len(missing) == 0), missing


def build_force_join_markup(missing_channels: list) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    for idx, ch in enumerate(missing_channels, 1):
        btn_text = f"📢 Join {ch['title'] or f'Channel {idx}'}"
        link = ch.get("invite_link") or f"https://t.me/{ch['chat_id'].replace('@', '')}"
        markup.add(types.InlineKeyboardButton(text=btn_text, url=link))
    markup.add(types.InlineKeyboardButton(text="✅ Verify / Check Joined", callback_data="verify_force_join"))
    return markup


def build_main_menu(user_id: int) -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_claim = types.KeyboardButton("💎 Claim Gemini 12-Month Pro")
    btn_refer = types.KeyboardButton("👥 Refer Friends (Earn Premium)")
    btn_support = types.KeyboardButton("💬 Contact Support")
    btn_account = types.KeyboardButton("👤 My Account & Claims")
    btn_help = types.KeyboardButton("📖 Tutorial & FAQ")

    markup.add(btn_claim)
    markup.add(btn_refer, btn_support)
    markup.add(btn_account, btn_help)

    if is_admin(user_id):
        btn_admin = types.KeyboardButton("🛠️ Admin Dashboard")
        markup.add(btn_admin)

    return markup


# COMMAND HANDLERS

@bot.message_handler(commands=["start"])
def handle_start(message: types.Message):
    user_id = message.from_user.id
    is_bot = getattr(message.from_user, "is_bot", False)

    # Disallow bot accounts from participating or earning referral rewards
    if is_bot:
        return

    username = message.from_user.username or ""
    first_name = message.from_user.first_name or "Friend"
    last_name = message.from_user.last_name or ""

    # Parse potential referral parameter: /start ref_123456
    referrer_id = None
    args = message.text.split()
    if len(args) > 1:
        param = args[1].strip()
        if param.startswith("ref_") and param[4:].isdigit():
            referrer_id = int(param[4:])

    user, is_new = db.register_user(user_id, username, first_name, last_name, referrer_id, is_bot=is_bot)

    # Send log event to private log group if new user
    if is_new:
        log_to_group(
            f"🟢 <b>NEW USER REGISTERED</b>\n\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            f"👤 <b>Name:</b> {first_name} {last_name} (@{username or 'No_Username'})\n"
            f"👥 <b>Referred By:</b> <code>{referrer_id or 'Direct (No Referrer)'}</code>\n"
            f"⏰ <b>Timestamp:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
        )

    # Force Join Check
    is_joined, missing = check_user_joined(user_id)
    if not is_joined:
        text = (
            f"👋 <b>Welcome, {first_name}!</b>\n\n"
            f"⚠️ <b>Action Required:</b> To access this bot and claim your "
            f"<b>Google Gemini 12-Month Pro Free Trial</b>, you must first join our official channel(s) below:\n\n"
            f"👇 Click the button(s) below to join, then press <b>'✅ Verify / Check Joined'</b>!"
        )
        bot.send_message(message.chat.id, text, reply_markup=build_force_join_markup(missing))
        return

    # User is verified or no force join needed
    # If they were just registered with a referrer, verify reward
    reward = db.verify_referral_reward(user_id)
    if reward:
        ref_id, count, reached_prem = reward
        req_ref = db.get_required_referrals()
        try:
            u_tag = f" (@{username})" if username else ""
            bot.send_message(
                ref_id,
                f"🎉 <b>REAL REFERRAL CONFIRMED!</b>\n\n"
                f"👤 <b>{first_name}</b>{u_tag} joined and verified their real Telegram account!\n"
                f"📊 Your Total Real Referrals: <b>{count}/{req_ref}</b>"
            )
            if reached_prem:
                bot.send_message(
                    ref_id,
                    f"👑 <b>CONGRATULATIONS! PREMIUM UNLOCKED!</b>\n\n"
                    f"You have reached <b>{count} verified real referrals</b>! Your account has been upgraded to <b>⭐ PREMIUM</b>!\n"
                    f"You can now claim your <b>12-Month Google Gemini AI & Google One Trial</b> for FREE!\n\n"
                    f"👉 Press <b>'💎 Claim Gemini 12-Month Pro'</b> in the menu below to start!"
                )
        except Exception:
            pass

        log_to_group(
            f"👥 <b>REAL REFERRAL VERIFIED</b>\n\n"
            f"👑 <b>Referrer ID:</b> <code>{ref_id}</code>\n"
            f"👤 <b>Joined Real User:</b> {first_name} (@{username or 'No_Username'})\n"
            f"📊 <b>Referrer Count:</b> <b>{count}/{req_ref}</b>\n"
            f"⭐ <b>Upgraded to Premium:</b> {'YES 🎉' if reached_prem else 'NO'}\n"
            f"⏰ <b>Timestamp:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
        )

    # Send Welcome Message
    welcome_text = (
        f"👋 <b>Welcome, {first_name}!</b>\n\n"
        f"🤖 This bot lets you claim an official <b>Google Gemini 12-Month Trial Offer</b> "
        f"(Includes Gemini Advanced AI + 2TB Google One Cloud Storage) for your Google account!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 <b>Status:</b> {'⭐ PREMIUM USER' if user.get('is_premium') else '🆓 Free User'}\n"
        f"👥 <b>Your Referrals:</b> {user.get('referral_count', 0)}/{db.get_required_referrals()}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👉 <b>How to get Premium access:</b>\n"
        f"Share your referral link with friends. Once you reach <b>{db.get_required_referrals()} referrals</b>, "
        f"Premium access is automatically unlocked!\n\n"
        f"Choose an option from the menu below to get started:"
    )

    bot.send_message(message.chat.id, welcome_text, reply_markup=build_main_menu(user_id))


@bot.callback_query_handler(func=lambda call: call.data == "verify_force_join")
def handle_verify_force_join(call: types.CallbackQuery):
    user_id = call.from_user.id
    first_name = call.from_user.first_name or "Friend"

    is_joined, missing = check_user_joined(user_id)
    if not is_joined:
        bot.answer_callback_query(call.id, "❌ You haven't joined all required channels yet! Please join and try again.", show_alert=True)
        return

    # Rewarded referrer if applicable
    reward = db.verify_referral_reward(user_id)
    if reward:
        ref_id, count, reached_prem = reward
        req_ref = db.get_required_referrals()
        try:
            username_tag = f" (@{call.from_user.username})" if call.from_user.username else ""
            bot.send_message(
                ref_id,
                f"🎉 <b>REAL REFERRAL CONFIRMED!</b>\n\n"
                f"👤 <b>{first_name}</b>{username_tag} verified their real Telegram account!\n"
                f"📊 Your Verified Real Referrals: <b>{count}/{req_ref}</b>"
            )
            if reached_prem:
                bot.send_message(
                    ref_id,
                    f"👑 <b>CONGRATULATIONS! PREMIUM UNLOCKED!</b>\n\n"
                    f"You have reached <b>{count} real referrals</b>! Your account has been upgraded to <b>⭐ PREMIUM</b>!\n"
                    f"You can now claim your <b>12-Month Google Gemini AI & Google One Trial</b> for FREE!\n\n"
                    f"👉 Press <b>'💎 Claim Gemini 12-Month Pro'</b> in the menu below to start!"
                )
        except Exception:
            pass

    bot.answer_callback_query(call.id, "✅ Channels verified successfully! Welcome!")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    user = db.get_user(user_id) or {}
    text = (
        f"🎉 <b>Verification Successful!</b>\n\n"
        f"Welcome aboard, <b>{first_name}</b>!\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 <b>Status:</b> {'⭐ PREMIUM USER' if user.get('is_premium') else '🆓 Free User'}\n"
        f"👥 <b>Your Real Referrals:</b> {user.get('referral_count', 0)}/{db.get_required_referrals()}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Select an option below to proceed:"
    )
    bot.send_message(call.message.chat.id, text, reply_markup=build_main_menu(user_id))


# REFERRAL SYSTEM

@bot.message_handler(func=lambda m: m.text in ["👥 Refer Friends (Earn Premium)", "👥 Referral System", "/refer", "/referral"])
def handle_referral_menu(message: types.Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        user, _ = db.register_user(user_id, message.from_user.username or "", message.from_user.first_name or "", "")

    bot_info = bot.get_me()
    bot_username = bot_info.username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    ref_count = user.get("referral_count", 0)
    req_ref = db.get_required_referrals()
    is_premium = bool(user.get("is_premium", 0))

    progress = get_progress_bar(ref_count, req_ref, length=10)
    percent = min(100, int((ref_count / req_ref) * 100)) if req_ref > 0 else 100

    share_url = f"https://t.me/share/url?url={ref_link}&text=🚀%20Get%20FREE%20Google%20Gemini%2012-Month%20Subscription!%20Join%20here:"

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(text="🚀 Share Invite Link on Telegram", url=share_url))
    markup.add(types.InlineKeyboardButton(text="👥 View My Real Referred Users", callback_data="view_my_referrals"))
    markup.add(types.InlineKeyboardButton(text="🔄 Refresh Referral Stats", callback_data="refresh_referrals"))

    status_str = "👑 <b>PREMIUM UNLOCKED (Active)</b>" if is_premium else f"🔒 <b>FREE</b> (Need {max(0, req_ref - ref_count)} more)"

    msg_text = (
        f"👥 <b>REAL USER REFERRAL CENTER</b>\n\n"
        f"Invite real friends to unlock <b>PREMIUM ACCESS</b> and claim your "
        f"<b>Google Gemini 12-Month Free Trial</b>!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Your Exclusive Referral Link:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"📊 <b>Real Referrals Progress:</b>\n"
        f"<code>[{progress}] {ref_count}/{req_ref} ({percent}%)</code>\n\n"
        f"👑 <b>Current Status:</b> {status_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛡️ <i>Real User Policy: To guarantee quality and prevent fake accounts, each referral must be a real Telegram user who completes channel verification.</i>"
    )

    bot.send_message(message.chat.id, msg_text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "refresh_referrals")
def handle_refresh_referrals(call: types.CallbackQuery):
    user_id = call.from_user.id
    user = db.get_user(user_id) or {}
    ref_count = user.get("referral_count", 0)
    req_ref = db.get_required_referrals()
    is_premium = bool(user.get("is_premium", 0))

    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    progress = get_progress_bar(ref_count, req_ref, length=10)
    percent = min(100, int((ref_count / req_ref) * 100)) if req_ref > 0 else 100

    status_str = "👑 <b>PREMIUM UNLOCKED (Active)</b>" if is_premium else f"🔒 <b>FREE</b> (Need {max(0, req_ref - ref_count)} more)"

    msg_text = (
        f"👥 <b>REAL USER REFERRAL CENTER</b>\n\n"
        f"Invite real friends to unlock <b>PREMIUM ACCESS</b> and claim your "
        f"<b>Google Gemini 12-Month Free Trial</b>!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Your Exclusive Referral Link:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"📊 <b>Real Referrals Progress:</b>\n"
        f"<code>[{progress}] {ref_count}/{req_ref} ({percent}%)</code>\n\n"
        f"👑 <b>Current Status:</b> {status_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛡️ <i>Real User Policy: Each referral must be a real Telegram user who completes channel verification.</i>"
    )

    share_url = f"https://t.me/share/url?url={ref_link}&text=🚀%20Get%20FREE%20Google%20Gemini%2012-Month%20Subscription!%20Join%20here:"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(text="🚀 Share Invite Link on Telegram", url=share_url))
    markup.add(types.InlineKeyboardButton(text="👥 View My Real Referred Users", callback_data="view_my_referrals"))
    markup.add(types.InlineKeyboardButton(text="🔄 Refresh Referral Stats", callback_data="refresh_referrals"))

    try:
        bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id, f"Refreshed! You have {ref_count} verified real referrals.")
    except Exception:
        bot.answer_callback_query(call.id, "Referral stats are up to date!")


@bot.callback_query_handler(func=lambda call: call.data == "view_my_referrals")
def handle_view_my_referrals(call: types.CallbackQuery):
    user_id = call.from_user.id
    referrals = db.get_user_referrals_list(user_id)
    req_ref = db.get_required_referrals()

    verified_count = sum(1 for r in referrals if r.get("is_verified") == 1)

    text = (
        f"👥 <b>YOUR REAL REFERRED USERS</b>\n\n"
        f"📊 <b>Total Registered:</b> {len(referrals)}\n"
        f"✅ <b>Real Verified Members:</b> {verified_count}/{req_ref}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )

    if referrals:
        for idx, r in enumerate(referrals[:15], 1):
            status_emoji = "✅" if r.get("is_verified") == 1 else "⏳"
            status_desc = "Verified (Counted)" if r.get("is_verified") == 1 else "Pending Channel Join"
            u_name = f"@{r['username']}" if r.get("username") else "No Username"
            name = f"{r.get('first_name', '')} {r.get('last_name', '')}".strip() or "Telegram User"
            text += f"{idx}. {status_emoji} <b>{name}</b> ({u_name})\n   Status: <i>{status_desc}</i>\n"
        if len(referrals) > 15:
            text += f"\n<i>...and {len(referrals) - 15} more real users!</i>\n"
    else:
        text += "<i>No friends have joined via your link yet. Share your invite link to get started!</i>\n"

    text += (
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛡️ <b>Anti-Cheat & Real User Protection:</b>\n"
        f"Only real accounts that complete mandatory channel verification count towards your Premium upgrade!"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    share_url = f"https://t.me/share/url?url={ref_link}&text=🚀%20Get%20FREE%20Google%20Gemini%2012-Month%20Subscription!%20Join%20here:"
    markup.add(types.InlineKeyboardButton(text="🚀 Share Invite Link Now", url=share_url))
    markup.add(types.InlineKeyboardButton(text="🔙 Back to Referral Center", callback_data="refresh_referrals"))

    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        pass


# CUSTOMER SUPPORT SYSTEM

@bot.message_handler(func=lambda m: m.text in ["💬 Contact Support", "/support"])
def handle_support(message: types.Message):
    user_id = message.from_user.id
    USER_STATES[user_id] = {
        "state": "WAITING_SUPPORT_MESSAGE",
        "data": {}
    }

    cancel_markup = types.InlineKeyboardMarkup()
    cancel_markup.add(types.InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_claim"))

    support_text = (
        f"💬 <b>DIRECT ADMIN SUPPORT DESK</b>\n\n"
        f"Have a question, feedback, or need help claiming your <b>Google Gemini Pro</b> trial?\n\n"
        f"👉 <b>Type and send your message below.</b>\n"
        f"Your message will be sent directly to our Administrator team, and we will reply to you directly right here in this chat!\n\n"
        f"<i>Send /cancel to return to the main menu.</i>"
    )
    bot.send_message(message.chat.id, support_text, reply_markup=cancel_markup)


# MY ACCOUNT & FAQ

@bot.message_handler(func=lambda m: m.text in ["👤 My Account & Claims", "👤 My Account", "/account"])
def handle_my_account(message: types.Message):
    user_id = message.from_user.id
    user = db.get_user(user_id) or {}
    claims = db.get_user_claims(user_id)

    claims_text = ""
    if claims:
        claims_text = f"\n\n🎁 <b>Claimed Offers ({len(claims)}):</b>\n"
        for idx, cl in enumerate(claims[:3], 1):
            claims_text += f"{idx}. 📧 <code>{cl['email']}</code>\n🔗 <a href='{cl['offer_url']}'>Open Gemini Link</a>\n"
    else:
        claims_text = "\n\n🎁 <b>Claimed Offers:</b> None yet."

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(text="👥 View My Real Referred Users", callback_data="view_my_referrals"))

    text = (
        f"👤 <b>MY ACCOUNT PROFILE</b>\n\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"👤 <b>Name:</b> {message.from_user.full_name}\n"
        f"👑 <b>Status:</b> {'⭐ PREMIUM USER' if user.get('is_premium') else '🆓 Free User'}\n"
        f"👥 <b>Verified Real Referrals:</b> {user.get('referral_count', 0)}\n"
        f"📅 <b>Joined Date:</b> {user.get('joined_at', 'Recently')}"
        f"{claims_text}"
    )

    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.message_handler(func=lambda m: m.text in ["📖 Tutorial & FAQ", "❓ How It Works / FAQ", "/help"])
def handle_help(message: types.Message):
    req_ref = db.get_required_referrals()
    text = (
        f"📖 <b>STEP-BY-STEP TUTORIAL & FAQ</b>\n\n"
        f"<b>1. What does this bot do?</b>\n"
        f"This bot automatically registers and activates an official "
        f"<b>12-Month Google Gemini Advanced + Google One 2TB Cloud Storage Trial Offer</b> for your Google account.\n\n"
        f"<b>2. How does the real referral system work?</b>\n"
        f"Invite <b>{req_ref} real friends</b> using your unique invite link from <b>'👥 Refer Friends (Earn Premium)'</b>. "
        f"When they join and verify the required channel, your referral counter increases. Reach the goal to unlock Premium instantly!\n\n"
        f"<b>3. What happens after I enter my Gmail?</b>\n"
        f"• The bot registers your trial claim request with authorized education partners.\n"
        f"• A 6-digit verification OTP code is dispatched to your Gmail inbox.\n"
        f"• You send the 6-digit OTP here, and the bot completes automated activation and sends you your direct Google One activation link!\n\n"
        f"<b>4. Is it safe?</b>\n"
        f"Yes, 100% safe! We never ask for your Google account password or login credentials. Only a temporary 6-digit verification OTP code."
    )
    bot.send_message(message.chat.id, text)


# CLAIM GOOGLE GEMINI TRIAL CONVERSATION FLOW

@bot.message_handler(func=lambda m: m.text in ["💎 Claim Gemini 12-Month Pro", "💎 Claim Gemini 12-Month Trial", "/claim"])
def handle_claim_start(message: types.Message):
    user_id = message.from_user.id
    user = db.get_user(user_id) or {}

    # STEP 1: STRICT FORCE JOIN CHECK FIRST
    is_joined, missing = check_user_joined(user_id)
    if not is_joined:
        bot.send_message(
            message.chat.id,
            "⚠️ <b>Action Required:</b> To claim your <b>Google Gemini 12-Month Pro Free Trial</b>, "
            "you must join our official channel(s) first!\n\n"
            "Please join using the button(s) below, then press <b>'✅ Verify / Check Joined'</b> to continue:",
            reply_markup=build_force_join_markup(missing)
        )
        return

    # STEP 2: REFERRAL / PREMIUM CHECK
    is_referral_required = db.get_setting("referral_system_enabled", "1") == "1"
    is_premium = bool(user.get("is_premium", 0))

    if is_referral_required and not is_premium and not is_admin(user_id):
        ref_count = user.get("referral_count", 0)
        req_ref = db.get_required_referrals()
        needed = max(0, req_ref - ref_count)

        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
        share_url = f"https://t.me/share/url?url={ref_link}&text=🚀%20Get%20FREE%20Google%20Gemini%2012-Month%20Subscription!%20Join%20here:"

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton(text="👥 Share Referral Link Now", url=share_url))
        markup.add(types.InlineKeyboardButton(text="🔄 Check Referral Progress", callback_data="refresh_referrals"))

        text = (
            f"🔒 <b>PREMIUM FEATURE LOCKED</b>\n\n"
            f"To prevent server overload and abuse, claiming the <b>12-Month Google Gemini AI Trial</b> "
            f"requires <b>Premium Access</b>!\n\n"
            f"🎁 <b>How to unlock for FREE:</b>\n"
            f"Invite <b>{req_ref} real friends</b> using your referral link. You currently have <b>{ref_count}/{req_ref}</b>.\n"
            f"You only need <b>{needed} more referral(s)</b>!\n\n"
            f"🔗 <b>Your Link:</b>\n<code>{ref_link}</code>"
        )
        bot.send_message(message.chat.id, text, reply_markup=markup)
        return

    # User is Premium or Admin or referral requirement disabled!
    USER_STATES[user_id] = {
        "state": "WAITING_EMAIL",
        "data": {}
    }

    cancel_markup = types.InlineKeyboardMarkup()
    cancel_markup.add(types.InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_claim"))

    prompt_text = (
        f"💎 <b>GOOGLE GEMINI 12-MONTH TRIAL CLAIM WIZARD</b>\n\n"
        f"👑 <b>Welcome, Premium Member!</b>\n\n"
        f"Please enter your <b>Gmail address</b> where you want to receive your 6-digit activation code:\n\n"
        f"<i>Example: yourname@gmail.com</i>\n\n"
        f"⚠️ <i>Note: Only active @gmail.com addresses are supported.</i>"
    )
    bot.send_message(message.chat.id, prompt_text, reply_markup=cancel_markup)
    bot.send_message(message.chat.id, prompt_text, reply_markup=cancel_markup)


@bot.callback_query_handler(func=lambda call: call.data == "cancel_claim")
def handle_cancel_claim(call: types.CallbackQuery):
    user_id = call.from_user.id
    if user_id in USER_STATES:
        del USER_STATES[user_id]
    bot.answer_callback_query(call.id, "Process cancelled.")
    try:
        bot.edit_message_text("❌ Claiming process has been cancelled.", call.message.chat.id, call.message.message_id)
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data == "resend_claim_otp")
def handle_resend_claim_otp(call: types.CallbackQuery):
    user_id = call.from_user.id
    state_info = USER_STATES.get(user_id)
    if not state_info or state_info.get("state") != "WAITING_OTP":
        bot.answer_callback_query(call.id, "Session expired. Please start again.", show_alert=True)
        return

    session = state_info["data"].get("session")
    email = state_info["data"].get("email")

    bot.answer_callback_query(call.id, "Requesting new verification OTP code...")
    res = engine.resend_email_otp(session, email)

    if res and res.get("success") is True:
        bot.send_message(call.message.chat.id, f"✅ <b>New OTP sent!</b> Please check your inbox/spam for <code>{email}</code>.")
    else:
        err = (res and (res.get("errorThrown") or res.get("errorCode"))) or "Unable to resend OTP at this time."
        bot.send_message(call.message.chat.id, f"⚠️ Notice: {err}")


# MESSAGE DISPATCHER FOR MULTI-STEP CONVERSATIONS

@bot.message_handler(func=lambda m: m.from_user.id in USER_STATES)
def handle_user_states(message: types.Message):
    user_id = message.from_user.id
    state_info = USER_STATES.get(user_id)
    if not state_info:
        return

    current_state = state_info.get("state")
    text = (message.text or "").strip()

    # Cancel check
    if text.lower() in ["/cancel", "cancel"]:
        del USER_STATES[user_id]
        bot.send_message(message.chat.id, "❌ Action cancelled.", reply_markup=build_main_menu(user_id))
        return

    # STEP: WAITING FOR SUPPORT MESSAGE
    if current_state == "WAITING_SUPPORT_MESSAGE":
        USER_STATES.pop(user_id, None)
        ticket_id = db.save_support_message(
            user_id,
            message.from_user.username or "",
            message.from_user.first_name or "",
            text
        )

        bot.send_message(
            message.chat.id,
            "✅ <b>Message Delivered to Admin!</b>\n\n"
            "Your support inquiry has been received. Our administrators will review your message "
            "and reply directly to you right here in this chat shortly!\n\n"
            f"🎫 <b>Ticket Reference:</b> <code>#{ticket_id}</code>",
            reply_markup=build_main_menu(user_id)
        )

        # Notify Admins with reply button
        admin_markup = types.InlineKeyboardMarkup()
        admin_markup.add(types.InlineKeyboardButton(text="✍️ Reply to User", callback_data=f"adm_rep_{ticket_id}_{user_id}"))

        for adm_id in config.ADMIN_IDS:
            try:
                bot.send_message(
                    adm_id,
                    f"💬 <b>NEW USER SUPPORT INQUIRY (Ticket #{ticket_id})</b>\n\n"
                    f"👤 <b>From:</b> {message.from_user.full_name} (@{message.from_user.username or 'No_Username'})\n"
                    f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
                    f"⏰ <b>Time:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n\n"
                    f"📝 <b>Message:</b>\n{text}",
                    reply_markup=admin_markup
                )
            except Exception:
                pass

        # Log to private log group
        log_to_group(
            f"💬 <b>NEW SUPPORT INQUIRY #{ticket_id}</b>\n\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            f"👤 <b>User:</b> {message.from_user.full_name} (@{message.from_user.username or 'No_Username'})\n"
            f"⏰ <b>Timestamp:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n\n"
            f"📝 <b>Message:</b>\n{text}"
        )
        return

    # STEP 1: WAITING FOR EMAIL
    if current_state == "WAITING_EMAIL":
        # Strict Force Join Check before proceeding
        is_joined, missing = check_user_joined(user_id)
        if not is_joined:
            USER_STATES.pop(user_id, None)
            bot.send_message(
                message.chat.id,
                "⚠️ <b>Action Required:</b> You must join our official channels before claiming the Gemini Pro offer!\n\n"
                "Please join the channels below and press <b>'✅ Verify / Check Joined'</b>:",
                reply_markup=build_force_join_markup(missing)
            )
            return

        email = text.lower()

        # Validate Gmail
        email_pattern = r"^[a-zA-Z0-9_.+-]+@gmail\.com$"
        if not re.match(email_pattern, email):
            bot.send_message(
                message.chat.id,
                "❌ <b>Invalid Email Address!</b>\n"
                "Please enter a valid email ending with <b>@gmail.com</b>\n"
                "Or send /cancel to stop."
            )
            return

        status_msg = bot.send_message(
            message.chat.id,
            f"🔄 <b>Processing claim request...</b>\n"
            f"• Generating verified student profile\n"
            f"• Sending OTP code to <code>{email}</code>\n\n"
            f"⏳ <i>Please wait a few seconds...</i>"
        )

        # Execute session & registration in thread to keep bot responsive
        def do_register():
            try:
                session = engine.create_session()
                profile = engine.build_dynamic_student_profile(session)
                reg_resp = engine.register_account(session, email, profile=profile)

                if reg_resp is None:
                    bot.edit_message_text(
                        "❌ <b>Connection Error:</b> Failed to connect to verification server.\n"
                        "Please check server proxy or try again later.",
                        message.chat.id,
                        status_msg.message_id
                    )
                    USER_STATES.pop(user_id, None)
                    return

                try:
                    reg_json = reg_resp.json()
                except Exception:
                    bot.edit_message_text(
                        "❌ <b>Server Error:</b> Unexpected response from verification server. Please try again.",
                        message.chat.id,
                        status_msg.message_id
                    )
                    USER_STATES.pop(user_id, None)
                    return

                is_success = reg_json.get("success")
                error_code = str(reg_json.get("errorCode", ""))
                error_thrown = str(reg_json.get("errorThrown", ""))

                proceed = False
                notice = ""

                if is_success is True:
                    proceed = True
                    notice = "OTP sent successfully to your inbox!"
                elif (
                    "registered but not yet verified" in error_code
                    or "registered but not yet verified" in error_thrown
                    or "already been sent to you thrice" in error_code
                    or "already been sent to you thrice" in error_thrown
                ):
                    proceed = True
                    if "already been sent to you thrice" in error_code or "already been sent to you thrice" in error_thrown:
                        notice = "This email is registered. Verification emails were already sent thrice. Please enter the OTP from your inbox/spam folder."
                    else:
                        engine.resend_email_otp(session, email)
                        notice = "Account is registered but unverified. A fresh OTP has been sent!"
                else:
                    err_msg = error_thrown or error_code or "Registration failed."
                    bot.edit_message_text(
                        f"❌ <b>Registration Notice:</b>\n{err_msg}\n\n"
                        f"If this email is already registered, try using another Gmail address.",
                        message.chat.id,
                        status_msg.message_id
                    )
                    USER_STATES.pop(user_id, None)
                    return

                if proceed:
                    USER_STATES[user_id] = {
                        "state": "WAITING_OTP",
                        "data": {
                            "session": session,
                            "email": email,
                            "profile": profile
                        }
                    }

                    otp_markup = types.InlineKeyboardMarkup(row_width=2)
                    otp_markup.add(
                        types.InlineKeyboardButton(text="🔄 Resend OTP", callback_data="resend_claim_otp"),
                        types.InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_claim")
                    )

                    bot.edit_message_text(
                        f"📩 <b>OTP VERIFICATION CODE SENT!</b>\n\n"
                        f"📧 <b>Target Email:</b> <code>{email}</code>\n"
                        f"ℹ️ {notice}\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"👉 <b>Please enter the 6-digit OTP code below:</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"💡 <i>Check your Spam, Promotions, or Primary tab in Gmail.</i>",
                        message.chat.id,
                        status_msg.message_id,
                        reply_markup=otp_markup
                    )

                    # Log to private group
                    log_to_group(
                        f"📩 <b>CLAIM OTP REQUESTED</b>\n\n"
                        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
                        f"👤 <b>User:</b> {message.from_user.full_name} (@{message.from_user.username or 'No_Username'})\n"
                        f"📧 <b>Target Gmail:</b> <code>{email}</code>\n"
                        f"⏰ <b>Timestamp:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
                    )
            except Exception as e:
                bot.edit_message_text(f"❌ An error occurred: {str(e)}", message.chat.id, status_msg.message_id)
                USER_STATES.pop(user_id, None)

        threading.Thread(target=do_register).start()
        return

    # STEP 2: WAITING FOR OTP
    if current_state == "WAITING_OTP":
        otp = text.replace(" ", "")

        if not (otp.isdigit() and len(otp) == 6):
            bot.send_message(
                message.chat.id,
                "⚠️ <b>Invalid OTP format!</b>\n"
                "Please enter a valid <b>6-digit numeric OTP</b> code (e.g., <code>123456</code>):"
            )
            return

        session = state_info["data"]["session"]
        email = state_info["data"]["email"]
        profile = state_info["data"]["profile"]

        verifying_msg = bot.send_message(
            message.chat.id,
            f"🔄 <b>Verifying OTP & Claiming Gemini Offer...</b>\n\n"
            f"1️⃣ Verifying 6-digit OTP code\n"
            f"2️⃣ Setting up verified student profile (IIT Kharagpur, B.Tech CSE)\n"
            f"3️⃣ Generating official Google Gemini 12-Month Trial Offer Link\n\n"
            f"⏳ <i>Please wait 10-15 seconds...</i>"
        )

        def do_verify_and_claim():
            try:
                # Verify OTP
                verify_result = engine.verify_email_otp(session, email, otp)
                if not verify_result:
                    bot.edit_message_text(
                        "❌ Network error while submitting OTP. Please try re-entering the OTP code:",
                        message.chat.id,
                        verifying_msg.message_id
                    )
                    return

                if verify_result.get("success") is not True:
                    err = verify_result.get("errorThrown")
                    if isinstance(err, dict):
                        err_msg = ", ".join(f"{k}: {v}" for k, v in err.items())
                    else:
                        err_msg = str(err or verify_result.get("errorCode") or "Invalid or expired OTP.")
                    bot.edit_message_text(
                        f"❌ <b>OTP Verification Failed:</b>\n{err_msg}\n\n"
                        f"👉 <b>Please enter the correct 6-digit OTP code:</b>\n"
                        f"(Or use 🔄 Resend OTP if needed)",
                        message.chat.id,
                        verifying_msg.message_id
                    )
                    return

                # OTP is verified! Complete onboarding and claim offer
                offer_url = engine.complete_onboarding_and_claim(session, profile)

                if offer_url:
                    db.record_claim(user_id, email, offer_url)
                    USER_STATES.pop(user_id, None)

                    success_markup = types.InlineKeyboardMarkup(row_width=1)
                    success_markup.add(types.InlineKeyboardButton(text="🎉 Open Google Gemini Offer Link", url=offer_url))

                    congrats_text = (
                        f"🎉 <b>CONGRATULATIONS! GOOGLE GEMINI CLAIMED!</b>\n\n"
                        f"Your <b>12-Month Google Gemini AI & Google One Subscription</b> has been claimed successfully!\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"📧 <b>Account:</b> <code>{email}</code>\n"
                        f"🎁 <b>Plan:</b> 12-Month Google One + Gemini Advanced (2TB Cloud)\n"
                        f"🔗 <b>Offer Link:</b>\n<code>{offer_url}</code>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"👉 <b>How to activate:</b>\n"
                        f"1. Click the button below to open your unique Google One offer page.\n"
                        f"2. Sign in with your Google account and follow the simple activation prompt!\n\n"
                        f"Enjoy your 12 Months of Gemini Advanced AI! 🚀"
                    )

                    bot.edit_message_text(congrats_text, message.chat.id, verifying_msg.message_id, reply_markup=success_markup)

                    # Log to private group
                    log_to_group(
                        f"🎉 <b>GEMINI PRO CLAIMED SUCCESSFULLY!</b>\n\n"
                        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
                        f"👤 <b>User:</b> {message.from_user.full_name} (@{message.from_user.username or 'No_Username'})\n"
                        f"📧 <b>Gmail:</b> <code>{email}</code>\n"
                        f"🔗 <b>Offer Link:</b>\n<code>{offer_url}</code>\n"
                        f"⏰ <b>Timestamp:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
                    )
                else:
                    bot.edit_message_text(
                        f"⚠️ <b>Account Verified, But Offer Link Could Not Be Retrieved</b>\n\n"
                        f"Your email <code>{email}</code> was verified successfully, but the server did not return an offer link.\n"
                        f"This could happen if the email has already claimed the offer previously or campaign quota is full.\n\n"
                        f"Try claiming with a fresh Gmail address!",
                        message.chat.id,
                        verifying_msg.message_id
                    )
                    USER_STATES.pop(user_id, None)
            except Exception as e:
                bot.edit_message_text(f"❌ Error occurred: {str(e)}", message.chat.id, verifying_msg.message_id)
                USER_STATES.pop(user_id, None)

        threading.Thread(target=do_verify_and_claim).start()
        return

    # ADMIN STATE HANDLERS
    if is_admin(user_id):
        handle_admin_state_input(message, current_state, text)


# ADMIN PANEL & MANAGEMENT

@bot.message_handler(func=lambda m: m.text in ["🛠️ Admin Dashboard", "🛠️ Admin Panel", "/admin"])
def handle_admin_panel(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(message.chat.id, "⛔ Access denied. You are not an administrator.")
        return

    stats = db.get_bot_stats()
    force_join_status = "ENABLED ✅" if db.is_force_join_enabled() else "DISABLED ❌"
    req_refs = db.get_required_referrals()
    ref_sys_status = "ENABLED ✅" if db.get_setting("referral_system_enabled", "1") == "1" else "DISABLED ❌"

    text = (
        f"🛠️ <b>BOT ADMINISTRATOR DASHBOARD</b>\n\n"
        f"📊 <b>Bot Overview & Statistics:</b>\n"
        f"• Total Users: <b>{stats['total_users']}</b>\n"
        f"• Premium Users: <b>{stats['premium_users']}</b>\n"
        f"• Free Users: <b>{stats['free_users']}</b>\n"
        f"• Gemini Claims: <b>{stats['total_claims']}</b>\n"
        f"• Real Referrals: <b>{stats['total_referrals']}</b>\n"
        f"• Force-Join Channels: <b>{stats['total_channels']}</b>\n\n"
        f"⚙️ <b>Current Settings:</b>\n"
        f"• Force Join: <b>{force_join_status}</b>\n"
        f"• Referral System: <b>{ref_sys_status}</b>\n"
        f"• Referrals for Premium: <b>{req_refs}</b>\n\n"
        f"Select an administrative task below:"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(text="📢 Send Global Broadcast", callback_data="admin_broadcast_start"),
        types.InlineKeyboardButton(text="📊 Live System Analytics", callback_data="admin_stats")
    )
    markup.add(
        types.InlineKeyboardButton(text="📢 Force-Join Channels", callback_data="admin_channels"),
        types.InlineKeyboardButton(text="⚙️ Referral Gate Settings", callback_data="admin_ref_settings")
    )
    markup.add(
        types.InlineKeyboardButton(text="👑 Manage VIP Members", callback_data="admin_manage_prem"),
        types.InlineKeyboardButton(text="🔍 User Account Inspector", callback_data="admin_user_lookup")
    )
    markup.add(types.InlineKeyboardButton(text="❌ Close Dashboard", callback_data="admin_close"))

    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "admin_close")
def handle_admin_close(call: types.CallbackQuery):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def handle_admin_back(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return

    stats = db.get_bot_stats()
    force_join_status = "ENABLED ✅" if db.is_force_join_enabled() else "DISABLED ❌"
    req_refs = db.get_required_referrals()
    ref_sys_status = "ENABLED ✅" if db.get_setting("referral_system_enabled", "1") == "1" else "DISABLED ❌"

    text = (
        f"🛠️ <b>BOT ADMINISTRATOR DASHBOARD</b>\n\n"
        f"📊 <b>Bot Overview & Statistics:</b>\n"
        f"• Total Users: <b>{stats['total_users']}</b>\n"
        f"• Premium Users: <b>{stats['premium_users']}</b>\n"
        f"• Free Users: <b>{stats['free_users']}</b>\n"
        f"• Gemini Claims: <b>{stats['total_claims']}</b>\n"
        f"• Real Referrals: <b>{stats['total_referrals']}</b>\n"
        f"• Force-Join Channels: <b>{stats['total_channels']}</b>\n\n"
        f"⚙️ <b>Current Settings:</b>\n"
        f"• Force Join: <b>{force_join_status}</b>\n"
        f"• Referral System: <b>{ref_sys_status}</b>\n"
        f"• Referrals for Premium: <b>{req_refs}</b>\n\n"
        f"Select an administrative task below:"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(text="📢 Send Global Broadcast", callback_data="admin_broadcast_start"),
        types.InlineKeyboardButton(text="📊 Live System Analytics", callback_data="admin_stats")
    )
    markup.add(
        types.InlineKeyboardButton(text="📢 Force-Join Channels", callback_data="admin_channels"),
        types.InlineKeyboardButton(text="⚙️ Referral Gate Settings", callback_data="admin_ref_settings")
    )
    markup.add(
        types.InlineKeyboardButton(text="👑 Manage VIP Members", callback_data="admin_manage_prem"),
        types.InlineKeyboardButton(text="🔍 User Account Inspector", callback_data="admin_user_lookup")
    )
    markup.add(types.InlineKeyboardButton(text="❌ Close Dashboard", callback_data="admin_close"))

    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)


# ADMIN STATS

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def handle_admin_detailed_stats(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    stats = db.get_bot_stats()
    text = (
        f"📊 <b>DETAILED SYSTEM METRICS</b>\n\n"
        f"👥 <b>User Growth:</b>\n"
        f"• Total Registered Users: <b>{stats['total_users']}</b>\n"
        f"• ⭐ Premium Members: <b>{stats['premium_users']}</b>\n"
        f"• 🆓 Free Members: <b>{stats['free_users']}</b>\n\n"
        f"📈 <b>Performance:</b>\n"
        f"• 💎 Total Gemini Offers Claimed: <b>{stats['total_claims']}</b>\n"
        f"• 🔗 Total Verified Referrals: <b>{stats['total_referrals']}</b>\n"
        f"• 📢 Mandatory Channels: <b>{stats['total_channels']}</b>"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="🔙 Back to Dashboard", callback_data="admin_back"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)


# ADMIN CHANNELS MANAGER

@bot.callback_query_handler(func=lambda call: call.data == "admin_channels")
def handle_admin_channels_menu(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    channels = db.get_required_channels()
    is_fj_enabled = db.is_force_join_enabled()

    text = (
        f"📢 <b>FORCE-JOIN CHANNELS MANAGER</b>\n\n"
        f"Status: <b>{'ENABLED ✅' if is_fj_enabled else 'DISABLED ❌'}</b>\n\n"
        f"<b>Currently Configured Channels ({len(channels)}):</b>\n"
    )

    if channels:
        for idx, ch in enumerate(channels, 1):
            text += f"{idx}. <b>{ch['title']}</b> (<code>{ch['chat_id']}</code>)\n   Link: {ch['invite_link']}\n"
    else:
        text += "<i>No channels configured. Add at least one channel below.</i>\n"

    markup = types.InlineKeyboardMarkup(row_width=1)
    toggle_text = "❌ Disable Force Join" if is_fj_enabled else "✅ Enable Force Join"
    markup.add(types.InlineKeyboardButton(text=toggle_text, callback_data="admin_toggle_force_join"))
    markup.add(types.InlineKeyboardButton(text="➕ Add New Channel/Group", callback_data="admin_add_channel"))
    if channels:
        markup.add(types.InlineKeyboardButton(text="🗑️ Remove A Channel", callback_data="admin_remove_channel_list"))
    markup.add(types.InlineKeyboardButton(text="🔙 Back to Dashboard", callback_data="admin_back"))

    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "admin_toggle_force_join")
def handle_admin_toggle_force_join(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    current = db.is_force_join_enabled()
    new_val = "0" if current else "1"
    db.set_setting("force_join_enabled", new_val)
    bot.answer_callback_query(call.id, f"Force Join is now {'ENABLED' if new_val == '1' else 'DISABLED'}!")
    handle_admin_channels_menu(call)


@bot.callback_query_handler(func=lambda call: call.data == "admin_add_channel")
def handle_admin_add_channel_prompt(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return

    USER_STATES[user_id] = {"state": "ADMIN_ADD_CHANNEL", "data": {}}
    text = (
        f"➕ <b>ADD REQUIRED CHANNEL / GROUP</b>\n\n"
        f"Please send the channel details in this exact format:\n\n"
        f"<code>CHAT_ID | TITLE | INVITE_LINK</code>\n\n"
        f"<b>Examples:</b>\n"
        f"• <code>@myofficialchannel | Official Channel | https://t.me/myofficialchannel</code>\n"
        f"• <code>-1001234567890 | VIP Chat | https://t.me/+AbCdEfGh</code>\n\n"
        f"⚠️ <b>Important:</b> Make sure the bot is an <b>ADMINISTRATOR</b> in the channel so it can check members!\n\n"
        f"Send /cancel to abort."
    )
    bot.send_message(call.message.chat.id, text)


@bot.callback_query_handler(func=lambda call: call.data == "admin_remove_channel_list")
def handle_admin_remove_channel_list(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    channels = db.get_required_channels()
    if not channels:
        handle_admin_channels_menu(call)
        return

    text = "🗑️ <b>Choose a channel to remove:</b>"
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in channels:
        markup.add(types.InlineKeyboardButton(text=f"❌ Remove {ch['title']}", callback_data=f"admin_del_ch_{ch['id']}"))
    markup.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="admin_channels"))

    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_del_ch_"))
def handle_admin_delete_channel(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    ch_id = int(call.data.replace("admin_del_ch_", ""))
    db.remove_required_channel(ch_id)
    bot.answer_callback_query(call.id, "Channel removed successfully!")
    handle_admin_channels_menu(call)


# ADMIN REFERRAL SETTINGS

@bot.callback_query_handler(func=lambda call: call.data == "admin_ref_settings")
def handle_admin_ref_settings(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    req_refs = db.get_required_referrals()
    ref_sys_status = "ENABLED ✅" if db.get_setting("referral_system_enabled", "1") == "1" else "DISABLED ❌"

    text = (
        f"⚙️ <b>REFERRAL SYSTEM SETTINGS</b>\n\n"
        f"• Referral Gate System: <b>{ref_sys_status}</b>\n"
        f"• Referrals Required For Premium: <b>{req_refs}</b>\n\n"
        f"💡 <i>When Referral Gate is ENABLED, users must invite {req_refs} friends to unlock the Gemini claim feature.</i>\n"
        f"<i>When DISABLED, all users can claim Gemini trial immediately without referrals.</i>"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    toggle_text = "❌ Disable Referral Gate (Free For All)" if ref_sys_status.startswith("ENABLED") else "✅ Enable Referral Gate"
    markup.add(types.InlineKeyboardButton(text=toggle_text, callback_data="admin_toggle_ref_sys"))
    markup.add(types.InlineKeyboardButton(text="✏️ Change Required Referrals Count", callback_data="admin_change_req_refs"))
    markup.add(types.InlineKeyboardButton(text="🔙 Back to Dashboard", callback_data="admin_back"))

    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "admin_toggle_ref_sys")
def handle_admin_toggle_ref_sys(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    current = db.get_setting("referral_system_enabled", "1") == "1"
    new_val = "0" if current else "1"
    db.set_setting("referral_system_enabled", new_val)
    bot.answer_callback_query(call.id, f"Referral system is now {'ENABLED' if new_val == '1' else 'DISABLED'}!")
    handle_admin_ref_settings(call)


@bot.callback_query_handler(func=lambda call: call.data == "admin_change_req_refs")
def handle_admin_change_req_refs_prompt(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return

    USER_STATES[user_id] = {"state": "ADMIN_SET_REFS", "data": {}}
    bot.send_message(
        call.message.chat.id,
        "✏️ <b>Enter new number of required referrals</b> (e.g., <code>1</code>, <code>2</code>, <code>3</code>, <code>5</code>):\n\n"
        "Send /cancel to abort."
    )


# ADMIN MANAGE PREMIUM & USER LOOKUP

@bot.callback_query_handler(func=lambda call: call.data == "admin_manage_prem")
def handle_admin_manage_prem_prompt(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return

    USER_STATES[user_id] = {"state": "ADMIN_PREMIUM_USER", "data": {}}
    bot.send_message(
        call.message.chat.id,
        "👑 <b>GRANT OR REVOKE PREMIUM</b>\n\n"
        "Send the Telegram User ID followed by 1 (give premium) or 0 (remove premium):\n\n"
        "<code>USER_ID 1</code>  (To give Premium)\n"
        "<code>USER_ID 0</code>  (To revoke Premium)\n\n"
        "<b>Example:</b> <code>123456789 1</code>\n\n"
        "Send /cancel to abort."
    )


@bot.callback_query_handler(func=lambda call: call.data == "admin_user_lookup")
def handle_admin_user_lookup_prompt(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return

    USER_STATES[user_id] = {"state": "ADMIN_LOOKUP_USER", "data": {}}
    bot.send_message(
        call.message.chat.id,
        "🔍 <b>USER LOOKUP</b>\n\n"
        "Send the <b>Telegram User ID</b> to inspect details and claims history:\n\n"
        "Send /cancel to abort."
    )


# ADMIN BROADCAST SYSTEM

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast_start")
def handle_admin_broadcast_start(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return

    USER_STATES[user_id] = {"state": "ADMIN_WAITING_BROADCAST_MSG", "data": {}}
    bot.send_message(
        call.message.chat.id,
        "📢 <b>BROADCAST TO ALL USERS</b>\n\n"
        "Send any message you want to broadcast.\n\n"
        "Supported formats:\n"
        "• Text message (with HTML formatting)\n"
        "• Photo with caption\n"
        "• Forwarded message\n\n"
        "Send /cancel to abort."
    )


@bot.callback_query_handler(func=lambda call: call.data == "admin_confirm_broadcast")
def handle_admin_confirm_broadcast(call: types.CallbackQuery):
    admin_id = call.from_user.id
    if not is_admin(admin_id):
        return

    draft = ADMIN_BROADCAST_DRAFT.get(admin_id)
    if not draft:
        bot.answer_callback_query(call.id, "No active broadcast draft found.")
        return

    bot.answer_callback_query(call.id, "🚀 Broadcast started!")
    progress_msg = bot.send_message(call.message.chat.id, "⏳ <b>Broadcasting in progress...</b>\nSent: 0 | Failed: 0")

    def run_broadcast():
        user_ids = db.get_all_user_ids()
        total = len(user_ids)
        sent = 0
        failed = 0

        for idx, u_id in enumerate(user_ids, 1):
            try:
                if draft["type"] == "text":
                    bot.send_message(u_id, draft["text"])
                elif draft["type"] == "photo":
                    bot.send_photo(u_id, draft["photo_id"], caption=draft.get("caption"))
                elif draft["type"] == "forward":
                    bot.forward_message(u_id, draft["from_chat_id"], draft["message_id"])
                sent += 1
            except Exception:
                failed += 1

            # Update progress every 50 users or at the end
            if idx % 50 == 0 or idx == total:
                try:
                    pct = int((idx / total) * 100) if total > 0 else 100
                    bot.edit_message_text(
                        f"⏳ <b>Broadcasting...</b>\n"
                        f"Progress: [{get_progress_bar(idx, total)}] {idx}/{total} ({pct}%)\n"
                        f"✅ Sent: <b>{sent}</b> | ❌ Blocked/Failed: <b>{failed}</b>",
                        call.message.chat.id,
                        progress_msg.message_id
                    )
                except Exception:
                    pass
            time.sleep(0.04)  # Prevent Telegram rate limits (max ~30 msgs/sec)

        db.record_broadcast(admin_id, sent, failed)
        ADMIN_BROADCAST_DRAFT.pop(admin_id, None)

        bot.send_message(
            call.message.chat.id,
            f"🎉 <b>BROADCAST COMPLETED!</b>\n\n"
            f"• Total Targeted: <b>{total}</b>\n"
            f"• Successfully Delivered: <b>{sent}</b>\n"
            f"• Failed / Blocked: <b>{failed}</b>"
        )

    threading.Thread(target=run_broadcast).start()


@bot.callback_query_handler(func=lambda call: call.data == "admin_cancel_broadcast")
def handle_admin_cancel_broadcast(call: types.CallbackQuery):
    admin_id = call.from_user.id
    ADMIN_BROADCAST_DRAFT.pop(admin_id, None)
    bot.answer_callback_query(call.id, "Broadcast cancelled.")
    try:
        bot.edit_message_text("❌ Broadcast cancelled.", call.message.chat.id, call.message.message_id)
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_rep_"))
def handle_admin_reply_callback(call: types.CallbackQuery):
    admin_id = call.from_user.id
    if not is_admin(admin_id):
        bot.answer_callback_query(call.id, "Access denied.")
        return

    parts = call.data.split("_")
    # adm_rep_{ticket_id}_{user_id}
    if len(parts) >= 4:
        ticket_id = int(parts[2])
        target_user_id = int(parts[3])

        USER_STATES[admin_id] = {
            "state": "ADMIN_REPLY_SUPPORT",
            "data": {
                "ticket_id": ticket_id,
                "target_user_id": target_user_id
            }
        }
        bot.answer_callback_query(call.id, f"Replying to Ticket #{ticket_id}")
        bot.send_message(
            call.message.chat.id,
            f"✍️ <b>Type and send your reply to User <code>{target_user_id}</code> (Ticket #{ticket_id}):</b>\n\n"
            f"Send /cancel to abort."
        )


@bot.message_handler(commands=["reply"])
def handle_admin_reply_command(message: types.Message):
    admin_id = message.from_user.id
    if not is_admin(admin_id):
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        bot.send_message(message.chat.id, "❌ <b>Usage:</b> <code>/reply USER_ID Your reply message</code>")
        return

    target_user_id = int(parts[1])
    reply_text = parts[2].strip()

    try:
        bot.send_message(
            target_user_id,
            f"💬 <b>OFFICIAL SUPPORT TEAM REPLY</b>\n\n"
            f"{reply_text}"
        )
        bot.send_message(message.chat.id, f"✅ <b>Reply successfully sent to User <code>{target_user_id}</code>!</b>")

        log_to_group(
            f"💬 <b>DIRECT ADMIN MESSAGE SENT</b>\n\n"
            f"👑 <b>Admin:</b> {message.from_user.full_name}\n"
            f"👤 <b>To User ID:</b> <code>{target_user_id}</code>\n"
            f"📝 <b>Reply:</b> {reply_text}\n"
            f"⏰ <b>Timestamp:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Failed to deliver message to user: {e}")


def handle_admin_state_input(message: types.Message, current_state: str, text: str):
    admin_id = message.from_user.id
    state_info = USER_STATES.get(admin_id, {})

    # Reply to User Support Ticket
    if current_state == "ADMIN_REPLY_SUPPORT":
        data = state_info.get("data", {})
        target_user_id = data.get("target_user_id")
        ticket_id = data.get("ticket_id")
        USER_STATES.pop(admin_id, None)

        try:
            bot.send_message(
                target_user_id,
                f"💬 <b>OFFICIAL SUPPORT TEAM REPLY</b>\n\n"
                f"{text}\n\n"
                f"<i>(Reference Ticket #{ticket_id})</i>"
            )
            db.save_admin_reply(ticket_id, text)
            bot.send_message(message.chat.id, f"✅ <b>Reply successfully sent to user <code>{target_user_id}</code>!</b>")

            log_to_group(
                f"💬 <b>SUPPORT TICKET #{ticket_id} RESOLVED</b>\n\n"
                f"👑 <b>Admin:</b> {message.from_user.full_name}\n"
                f"👤 <b>To User ID:</b> <code>{target_user_id}</code>\n"
                f"📝 <b>Reply:</b> {text}\n"
                f"⏰ <b>Timestamp:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
            )
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Failed to deliver message to user: {e}")
        return

    # Add channel
    if current_state == "ADMIN_ADD_CHANNEL":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 3:
            bot.send_message(
                message.chat.id,
                "❌ <b>Invalid format!</b> Must be:\n<code>CHAT_ID | TITLE | INVITE_LINK</code>\n\n"
                "Example:\n<code>@mychannel | Official News | https://t.me/mychannel</code>"
            )
            return

        chat_id, title, link = parts
        success = db.add_required_channel(chat_id, title, link)
        USER_STATES.pop(admin_id, None)
        if success:
            bot.send_message(
                message.chat.id,
                f"✅ <b>Channel Added Successfully!</b>\n\n"
                f"• Title: <b>{title}</b>\n"
                f"• Chat ID: <code>{chat_id}</code>\n"
                f"• Link: {link}\n\n"
                f"Users will now be required to join this channel before using the bot."
            )
        else:
            bot.send_message(message.chat.id, "❌ Error saving channel into database.")
        return

    # Set required referrals
    if current_state == "ADMIN_SET_REFS":
        if not text.isdigit() or int(text) < 0:
            bot.send_message(message.chat.id, "❌ Please enter a valid non-negative integer (e.g. 1, 2, 3, 5):")
            return
        num = int(text)
        db.set_setting("required_referrals", str(num))
        USER_STATES.pop(admin_id, None)
        bot.send_message(message.chat.id, f"✅ Required referrals successfully set to: <b>{num}</b>")
        return

    # Premium User modification
    if current_state == "ADMIN_PREMIUM_USER":
        parts = text.split()
        if len(parts) != 2 or not parts[0].isdigit() or parts[1] not in ["0", "1"]:
            bot.send_message(
                message.chat.id,
                "❌ <b>Invalid format!</b> Please use:\n<code>USER_ID 1</code> (give premium) or <code>USER_ID 0</code> (revoke premium)"
            )
            return

        target_id = int(parts[0])
        val = parts[1] == "1"
        target_user = db.get_user(target_id)
        if not target_user:
            bot.send_message(message.chat.id, f"❌ User with ID <code>{target_id}</code> not found in database.")
            return

        db.set_user_premium(target_id, val)
        USER_STATES.pop(admin_id, None)
        status_name = "⭐ PREMIUM" if val else "🆓 FREE"
        bot.send_message(message.chat.id, f"✅ User <code>{target_id}</code> is now set to <b>{status_name}</b>!")
        try:
            bot.send_message(
                target_id,
                f"👑 <b>Admin Notice:</b> Your account status has been updated to <b>{status_name}</b>!"
            )
        except Exception:
            pass
        return

    # User lookup
    if current_state == "ADMIN_LOOKUP_USER":
        if not text.isdigit():
            bot.send_message(message.chat.id, "❌ Please enter a valid numeric Telegram ID:")
            return

        target_id = int(text)
        user = db.get_user(target_id)
        USER_STATES.pop(admin_id, None)

        if not user:
            bot.send_message(message.chat.id, f"❌ No user found with ID <code>{target_id}</code>.")
            return

        claims = db.get_user_claims(target_id)
        claims_str = ""
        if claims:
            for idx, c in enumerate(claims, 1):
                claims_str += f"\n  {idx}. 📧 {c['email']} ({c['claimed_at']})"
        else:
            claims_str = " None"

        text_info = (
            f"🔍 <b>USER RECORD:</b> <code>{target_id}</code>\n\n"
            f"• Username: @{user.get('username') or 'None'}\n"
            f"• Name: {user.get('first_name', '')} {user.get('last_name', '')}\n"
            f"• Status: <b>{'⭐ PREMIUM' if user.get('is_premium') else '🆓 FREE'}</b>\n"
            f"• Referral Count: <b>{user.get('referral_count', 0)}</b>\n"
            f"• Referred By: <code>{user.get('referrer_id') or 'Direct'}</code>\n"
            f"• Claims Count: <b>{user.get('claims_count', 0)}</b>\n"
            f"• Joined: {user.get('joined_at')}\n"
            f"• Claims History:{claims_str}"
        )
        bot.send_message(message.chat.id, text_info)
        return

    # Broadcast draft
    if current_state == "ADMIN_WAITING_BROADCAST_MSG":
        USER_STATES.pop(admin_id, None)

        draft = {}
        if message.photo:
            draft = {
                "type": "photo",
                "photo_id": message.photo[-1].file_id,
                "caption": message.caption or ""
            }
        elif message.forward_date:
            draft = {
                "type": "forward",
                "from_chat_id": message.chat.id,
                "message_id": message.message_id
            }
        else:
            draft = {
                "type": "text",
                "text": message.text or ""
            }

        ADMIN_BROADCAST_DRAFT[admin_id] = draft

        stats = db.get_bot_stats()
        confirm_markup = types.InlineKeyboardMarkup(row_width=2)
        confirm_markup.add(
            types.InlineKeyboardButton(text="🚀 Send Broadcast Now", callback_data="admin_confirm_broadcast"),
            types.InlineKeyboardButton(text="❌ Cancel", callback_data="admin_cancel_broadcast")
        )

        bot.send_message(
            message.chat.id,
            f"📢 <b>BROADCAST CONFIRMATION</b>\n\n"
            f"Target Audience: <b>{stats['total_users']} total users</b>\n\n"
            f"Are you sure you want to send this broadcast to all users?",
            reply_markup=confirm_markup
        )
        return


# MAIN BOT RUNNER

def run_bot():
    print("\n" + "=" * 60)
    print("🤖 TELEGRAM BOT STARTED")
    print(f"📡 Database: {config.DB_PATH}")
    print(f"👑 Admins: {config.ADMIN_IDS}")
    print(f"👥 Default Required Referrals: {config.DEFAULT_REQUIRED_REFERRALS}")
    print("=" * 60 + "\n")

    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=20)
        except Exception as e:
            print(f"[!] Bot Polling Exception: {e}")
            time.sleep(5)


if __name__ == "__main__":
    run_bot()
