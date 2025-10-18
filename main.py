import asyncio
import os
import logging
import re
import aiohttp
from urllib.parse import quote
import html
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    FloodWait, SessionPasswordNeeded, PhoneCodeInvalid,
    PasswordHashInvalid, PhoneNumberInvalid, PhoneCodeExpired, UserDeactivated, AuthKeyUnregistered,
    ReactionInvalid
)
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import Flask, request, render_template_string, redirect, session, url_for
from threading import Thread
import random
# کتابخانه لازم برای اتصال به MongoDB
from motor.motor_asyncio import AsyncIOMotorClient

# --- تنظیمات لاگ‌نویسی ---
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')

# =======================================================
# ⚠️ تنظیمات اصلی (API_ID و API_HASH خود را اینجا وارد کنید)
# =======================================================
API_ID = 28190856
API_HASH = "6b9b5309c2a211b526c6ddad6eabb521"
# --- تنظیمات ربات ادمین ---
BOT_TOKEN = "8440383140:AAFoPNkzVlSXoNDs2v1dQF82RTwaQ9oDDzk"
ADMIN_ID = 7423552124


# --- تنظیمات پایگاه داده ---
MONGO_URI = "mongodb+srv://a10247014_db_user:P1ikUZuHNUl8TcMr@cluster0.vpbcosg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
db_client = None
users_collection = None
banned_users_collection = None

if MONGO_URI:
    try:
        db_client = AsyncIOMotorClient(MONGO_URI)
        db = db_client.self_bot
        users_collection = db.users
        banned_users_collection = db.banned_users
        logging.info("Successfully connected to MongoDB.")
    except Exception as e:
        logging.error(f"Failed to connect to MongoDB: {e}")
        MONGO_URI = None # Disable DB features if connection fails
else:
    logging.warning("MONGO_URI environment variable not found. Database features will be disabled.")


# --- متغیرهای برنامه ---
TEHRAN_TIMEZONE = ZoneInfo("Asia/Tehran")
app_flask = Flask(__name__)
app_flask.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))
admin_bot = None
if BOT_TOKEN:
    admin_bot = Client("admin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# --- دیکشنری فونت‌ها برای ساعت ---
FONT_STYLES = {
    "cursive":      {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':'},
    "stylized":     {'0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵',':':':'},
    "doublestruck": {'0':'𝟘','1':'𝟙','2':'𝟚','3':'𝟛','4':'𝟜','5':'𝟝','6':'𝟞','7':'𝟟','8':'𝟠','9':'𝟡',':':':'},
    "monospace":    {'0':'𝟶','1':'𝟷','2':'𝟸','3':'𝟹','4':'𝟺','5':'𝟻','6':'𝟼','7':'𝟽','8':'𝟾','9':'𝟿',':':':'},
    "normal":       {'0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'6','7':'7','8':'8','9':'9',':':':'},
}
FONT_KEYS_ORDER = ["cursive", "stylized", "doublestruck", "monospace", "normal"]
FONT_DISPLAY_NAMES = {
    "cursive": "کشیده", "stylized": "فانتزی", "doublestruck": "توخالی",
    "monospace": "کامپیوتری", "normal": "ساده"
}
ALL_DIGITS = "".join(set(char for font in FONT_STYLES.values() for char in font.values()))

# --- متغیرهای مربوط به قابلیت‌ها ---
ENEMY_REPLIES = [
   "کیرم تو رحم اجاره ای و خونی مالی مادرت", "دو میلیون شبی پول ویلا بدم تا مادرتو تو گوشه کناراش بگام و اب کوسشو بریزم کف خونه تا فردا صبح کارگرای افغانی برای نظافت اومدن با بوی اب کس مادرت بجقن و ابکیراشون نثار قبر مرده هات بشه", "احمق مادر کونی من کس مادرت گذاشتم تو بازم داری کسشر میگی", "هی بیناموس کیرم بره تو کس ننت واس بابات نشآخ مادر کیری کیرم بره تو کس اجدادت کسکش بیناموس کس ول نسل شوتی ابجی کسده کیرم تو کس مادرت بیناموس کیری کیرم تو کس نسلت ابجی کونی کس نسل سگ ممبر کونی ابجی سگ ممبر سگ کونی کیرم تو کس ننت کیر تو کس مادرت کیر خاندان  تو کس نسلت مادر کونی ابجی کونی کیری ناموس ابجیتو گاییدم سگ حرومی خارکسه مادر کیری با کیر بزنم تو رحم مادرت ناموستو بگام لاشی کونی ابجی کس  خیابونی مادرخونی ننت کیرمو میماله تو میای کص میگی شاخ نشو ییا ببین شاخو کردم تو کون ابجی جندت کس ابجیتو پاره کردم تو شاخ میشی اوبی",
   "کیرم تو کس سیاه مادرت خارکصده", "حروم زاده باک کص ننت با ابکیرم پر میکنم", "منبع اب ایرانو با اب کص مادرت تامین میکنم", "خارکسته میخای مادرتو بگام بعد بیای ادعای شرف کنی کیرم تو شرف مادرت",
   "کیرم تویه اون خرخره مادرت بیا اینحا ببینم تویه نوچه کی دانلود شدی کیفیتت پایینه صدات نمیاد فقط رویه حالیت بی صدا داری امواج های بی ارزش و بیناموسانه از خودت ارسال میکنی که ناگهان دیدی من روانی شدم دست از پا خطا کردم با تبر کائنات کوبیدم رو سر مادرت نمیتونی مارو تازه بالقه گمان کنی", "کیرم تویه اون خرخره مادرت بیا اینحا ببینم تویه نوچه کی دانلود شدی کیفیتت پایینه صدات نمیاد فقط رویه حالیت بی صدا داری امواج های بی ارزش و بیناموسانه از خودت ارسال میکنی که ناگهان دیدی من روانی شدم دست از پا خطا کردم با تبر کائنات کوبیدم رو سر مادرت نمیتونی مارو تازه بالقه گمان کنی",
]
SECRETARY_REPLY_MESSAGE = "سلام! در حال حاضر آفلاین هستم و پیام شما را دریافت کردم. در اولین فرصت پاسخ خواهم داد. ممنون از پیامتون."
HELP_TEXT = """
** راهنمای کامل دستورات سلف بات **

---
** وضعیت و قالب‌بندی **
 • `اینگیلیسی روشن`: ترجمه خودکار پیام‌های ارسالی به انگلیسی.
 • `اینگیلیسی خاموش`: غیرفعال‌سازی ترجمه خودکار.
 • `بولد روشن`: برجسته (بولد) کردن خودکار تمام پیام‌ها.
 • `بولد خاموش`: غیرفعال‌سازی حالت بولد.
 • `سین روشن`: سین خودکار پیام‌ها در چت شخصی (PV).
 • `سین خاموش`: غیرفعال‌سازی سین خودکار.

---
** ساعت پروفایل **
 • `ساعت روشن`: نمایش ساعت در نام پروفایل شما.
 • `ساعت خاموش`: حذف ساعت از نام پروفایل شما.
 • `فونت`: نمایش لیست فونت‌های موجود برای ساعت.
 • `فونت [عدد]`: (مثال: `فونت 2`) انتخاب فونت جدید.

---
** مدیریت پیام و کاربر (با ریپلای) **
 • `ذخیره`: ذخیره کردن پیام مورد نظر در Saved Messages.
 • `تکرار [عدد]`: (مثال: `تکرار 10`) تکرار پیام تا سقف 100 بار.
 • `دشمن روشن`: پاسخ خودکار به کاربر در چت فعلی.
 • `دشمن خاموش`: غیرفعال‌سازی حالت دشمن.
 • `بلاک روشن`: بلاک کردن کاربر.
 • `بلاک خاموش`: آنبلاک کردن کاربر.
 • `سکوت روشن`: حذف خودکار پیام‌های کاربر در چت فعلی.
 • `سکوت خاموش`: غیرفعال‌سازی حالت سکوت.
 • `ریاکشن [ایموجی]`: واکنش خودکار به پیام‌های کاربر با ایموجی دلخواه.
 • `ریاکشن خاموش`: غیرفعال‌سازی واکنش خودکار.

---
** حالت منشی **
 • `منشی روشن`: فعال‌سازی پاسخ خودکار در PV.
 • `منشی خاموش`: غیرفعال‌سازی حالت منشی.
"""
COMMAND_REGEX = r"^(راهنما|فونت|فونت \d+|ساعت روشن|ساعت خاموش|بولد روشن|بولد خاموش|دشمن روشن|دشمن خاموش|منشی روشن|منشی خاموش|بلاک روشن|بلاک خاموش|سکوت روشن|سکوت خاموش|ذخیره|تکرار \d+|سین روشن|سین خاموش|ریاکشن .*|ریاکشن خاموش|اینگیلیسی روشن|اینگیلیسی خاموش)$"


# --- مدیریت وضعیت کاربران (بر اساس ID کاربر) ---
ACTIVE_ENEMIES = {}
ENEMY_REPLY_QUEUES = {}
SECRETARY_MODE_STATUS = {}
USERS_REPLIED_IN_SECRETARY = {}
MUTED_USERS = {}
USER_FONT_CHOICES = {}
CLOCK_STATUS = {}
BOLD_MODE_STATUS = {}
AUTO_SEEN_STATUS = {}
AUTO_REACTION_TARGETS = {}
AUTO_TRANSLATE_STATUS = {}


EVENT_LOOP = asyncio.new_event_loop()
ACTIVE_CLIENTS = {}
ACTIVE_BOTS = {}

# --- توابع کمکی پایگاه داده ---
async def update_db_settings(user_id, settings_update):
    if users_collection is not None:
        try:
            await users_collection.update_one({'_id': user_id}, {'$set': settings_update}, upsert=False)
        except Exception as e:
            logging.error(f"Could not update DB for user {user_id}: {e}")

# --- توابع اصلی ربات ---
def stylize_time(time_str: str, style: str) -> str:
    font_map = FONT_STYLES.get(style, FONT_STYLES["stylized"])
    return ''.join(font_map.get(char, char) for char in time_str)

async def update_profile_clock(client: Client, user_id: int):
    log_message = f"Starting bot loop for user_id {user_id}..."
    logging.info(log_message)
    
    while user_id in ACTIVE_BOTS:
        try:
            if not client.is_connected:
                logging.warning(f"Client for user {user_id} disconnected. Attempting to reconnect...")
                await client.start()
                if not client.is_connected:
                    logging.error(f"Failed to reconnect for user {user_id}. Stopping loop.")
                    break

            if CLOCK_STATUS.get(user_id, True):
                current_font_style = USER_FONT_CHOICES.get(user_id, 'stylized')
                me = await client.get_me()
                current_name = me.first_name
                
                parts = current_name.rsplit(' ', 1)
                base_name = parts[0].strip() if len(parts) > 1 and ':' in parts[-1] and any(char in ALL_DIGITS for char in parts[-1]) else current_name.strip()

                tehran_time = datetime.now(TEHRAN_TIMEZONE)
                current_time_str = tehran_time.strftime("%H:%M")
                stylized_time = stylize_time(current_time_str, current_font_style)
                new_name = f"{base_name} {stylized_time}"
                
                if new_name != current_name:
                    await client.update_profile(first_name=new_name)
            
            now = datetime.now(TEHRAN_TIMEZONE)
            sleep_duration = 60 - now.second + 0.1
            await asyncio.sleep(sleep_duration)
        except (UserDeactivated, AuthKeyUnregistered) as e:
            logging.error(f"Session for user_id {user_id} is invalid. Stopping bot. Reason: {e}")
            if users_collection is not None:
                await users_collection.delete_one({'_id': user_id})
                logging.info(f"Removed invalid session for user {user_id} from database.")
            break
        except FloodWait as e:
            logging.warning(f"Flood wait of {e.value}s for user_id {user_id}.")
            await asyncio.sleep(e.value + 5)
        except Exception as e:
            logging.error(f"An error occurred in the main loop for user_id {user_id}: {e}", exc_info=True)
            await asyncio.sleep(60)
    
    if client and client.is_connected:
        await client.stop()
    for user_dict in [ACTIVE_BOTS, ACTIVE_ENEMIES, SECRETARY_MODE_STATUS, ENEMY_REPLY_QUEUES, 
                       USERS_REPLIED_IN_SECRETARY, MUTED_USERS, USER_FONT_CHOICES, CLOCK_STATUS, 
                       BOLD_MODE_STATUS, AUTO_SEEN_STATUS, AUTO_REACTION_TARGETS, AUTO_TRANSLATE_STATUS]:
        user_dict.pop(user_id, None)
    logging.info(f"Bot for user_id {user_id} has been stopped and cleaned up.")


# --- هندلرهای قابلیت‌ها ---
async def translate_to_english(text: str) -> str:
    if not text: return ""
    encoded_text = quote(text)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q={encoded_text}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data[0][0][0]
    except Exception as e:
        logging.error(f"Translation failed: {e}")
    return text

async def outgoing_message_modifier(client, message):
    user_id = client.me.id
    if not message.text or re.match(COMMAND_REGEX, message.text.strip(), re.IGNORECASE):
        return
        
    original_text = message.text
    modified_text = original_text
    
    if AUTO_TRANSLATE_STATUS.get(user_id, False):
        modified_text = await translate_to_english(modified_text)
    
    if BOLD_MODE_STATUS.get(user_id, False):
        if not modified_text.startswith(('`', '**', '__', '~~', '||')):
            modified_text = f"**{modified_text}**"
            
    if modified_text != original_text:
        try:
            await message.edit_text(modified_text)
        except Exception as e:
            logging.warning(f"Could not modify outgoing message for user {user_id}: {e}")
    
async def enemy_handler(client, message):
    user_id = client.me.id
    if user_id not in ENEMY_REPLY_QUEUES or not ENEMY_REPLY_QUEUES[user_id]:
        shuffled_replies = random.sample(ENEMY_REPLIES, len(ENEMY_REPLIES))
        ENEMY_REPLY_QUEUES[user_id] = shuffled_replies
    reply_text = ENEMY_REPLY_QUEUES[user_id].pop(0)
    try:
        await message.reply_text(reply_text)
    except Exception as e:
        logging.warning(f"Could not reply to enemy for user_id {user_id}: {e}")

async def secretary_auto_reply_handler(client, message):
    owner_user_id = client.me.id
    if message.from_user:
        target_user_id = message.from_user.id
        if SECRETARY_MODE_STATUS.get(owner_user_id, False):
            replied_users = USERS_REPLIED_IN_SECRETARY.get(owner_user_id, set())
            if target_user_id in replied_users:
                return
            try:
                await message.reply_text(SECRETARY_REPLY_MESSAGE)
                replied_users.add(target_user_id)
                USERS_REPLIED_IN_SECRETARY[owner_user_id] = replied_users
            except Exception as e:
                logging.warning(f"Could not auto-reply for user_id {owner_user_id}: {e}")

async def incoming_message_manager(client, message):
    if not message.from_user: return
    user_id = client.me.id
    
    reaction_map = AUTO_REACTION_TARGETS.get(user_id, {})
    target_key = (message.from_user.id, message.chat.id)
    if target_key in reaction_map:
        emoji = reaction_map[target_key]
        try:
            await client.send_reaction(message.chat.id, message.id, emoji)
        except ReactionInvalid:
            logging.warning(f"Invalid reaction emoji '{emoji}' for user {user_id}.")
            if AUTO_REACTION_TARGETS.get(user_id, {}).pop(target_key, None):
                asyncio.create_task(update_db_settings(user_id, {'auto_reaction_targets': AUTO_REACTION_TARGETS[user_id]}))
            try:
                await client.send_message(user_id, f"⚠️ **خطا:** ایموجی `{emoji}` نامعتبر بود و حذف شد.")
            except Exception as e2:
                logging.warning(f"Could not send error message to user {user_id}: {e2}")
        except Exception as e:
            logging.warning(f"Could not send reaction for user {user_id}: {e}")

    muted_list = MUTED_USERS.get(user_id, set())
    if (message.from_user.id, message.chat.id) in muted_list:
        try: 
            await message.delete()
            return
        except Exception as e: logging.warning(f"Could not delete muted message for owner {user_id}: {e}")

async def auto_seen_handler(client, message):
    user_id = client.me.id
    if AUTO_SEEN_STATUS.get(user_id, False):
        try: await client.read_chat_history(message.chat.id)
        except Exception as e: logging.warning(f"Could not mark history as read for chat {message.chat.id}: {e}")

# --- کنترلرهای دستورات ---
async def help_controller(client, message):
    await message.edit_text(HELP_TEXT)

async def font_controller(client, message):
    user_id = client.me.id
    command = message.text.strip().split()

    if len(command) == 1:
        sample_time = "12:34"
        font_list_text = "🔢 **فونت خود را انتخاب کنید:**\n\n"
        for i, style_key in enumerate(FONT_KEYS_ORDER, 1):
            font_list_text += f"`{stylize_time(sample_time, style_key)}` **{FONT_DISPLAY_NAMES[style_key]}** ({i})\n"
        font_list_text += "\nبرای انتخاب، دستور `فونت [عدد]` را ارسال کنید."
        await message.edit_text(font_list_text)

    elif len(command) == 2 and command[1].isdigit():
        choice = int(command[1])
        if 1 <= choice <= len(FONT_KEYS_ORDER):
            selected_style = FONT_KEYS_ORDER[choice - 1]
            USER_FONT_CHOICES[user_id] = selected_style
            CLOCK_STATUS[user_id] = True 
            asyncio.create_task(update_db_settings(user_id, {"font_style": selected_style, "clock_status": True}))
            await message.edit_text(f"✅ فونت به **{FONT_DISPLAY_NAMES[selected_style]}** تغییر یافت و ساعت فعال شد.")
        else:
            await message.edit_text("⚠️ عدد وارد شده معتبر نیست.")

async def clock_controller(client, message):
    user_id = client.me.id
    command = message.text.strip()
    if command == "ساعت روشن":
        CLOCK_STATUS[user_id] = True
        asyncio.create_task(update_db_settings(user_id, {"clock_status": True}))
        await message.edit_text("✅ ساعت پروفایل فعال شد.")
    elif command == "ساعت خاموش":
        CLOCK_STATUS[user_id] = False
        asyncio.create_task(update_db_settings(user_id, {"clock_status": False}))
        try:
            me = await client.get_me()
            current_name = me.first_name
            parts = current_name.rsplit(' ', 1)
            base_name = parts[0].strip() if len(parts) > 1 and ':' in parts[-1] and any(char in ALL_DIGITS for char in parts[-1]) else current_name.strip()
            if base_name != current_name:
                await client.update_profile(first_name=base_name)
            await message.edit_text("❌ ساعت پروفایل غیرفعال و از نام شما حذف شد.")
        except Exception as e:
            logging.error(f"Could not remove clock for user {user_id}: {e}")
            await message.edit_text("❌ ساعت پروفایل غیرفعال شد (خطا در حذف از نام).")
            
async def enemy_controller(client, message):
    if not message.reply_to_message or not message.reply_to_message.from_user: return
    user_id = client.me.id
    target_user, chat_id = message.reply_to_message.from_user, message.chat.id
    command = message.text.strip()
    
    if user_id not in ACTIVE_ENEMIES: ACTIVE_ENEMIES[user_id] = set()
    
    target_tuple = (target_user.id, chat_id)
    if command == "دشمن روشن":
        ACTIVE_ENEMIES[user_id].add(target_tuple)
        await message.edit_text(f"✅ **حالت دشمن برای {target_user.first_name} فعال شد.**")
    elif command == "دشمن خاموش":
        ACTIVE_ENEMIES[user_id].discard(target_tuple)
        await message.edit_text(f"❌ **حالت دشمن برای {target_user.first_name} خاموش شد.**")
    
    db_enemies = [{"user_id": u, "chat_id": c} for u, c in ACTIVE_ENEMIES[user_id]]
    asyncio.create_task(update_db_settings(user_id, {"active_enemies": db_enemies}))

async def block_unblock_controller(client, message):
    if not message.reply_to_message or not message.reply_to_message.from_user: return
    target_user = message.reply_to_message.from_user
    command = message.text.strip()
    try:
        if command == "بلاک روشن":
            await client.block_user(target_user.id)
            await message.edit_text(f"🚫 **کاربر {target_user.first_name} بلاک شد.**")
        elif command == "بلاک خاموش":
            await client.unblock_user(target_user.id)
            await message.edit_text(f"✅ **کاربر {target_user.first_name} آنبلاک شد.**")
    except Exception as e:
        await message.edit_text(f"⚠️ **خطا:** {e}")

async def mute_unmute_controller(client, message):
    if not message.reply_to_message or not message.reply_to_message.from_user: return
    user_id = client.me.id
    target_user, chat_id = message.reply_to_message.from_user, message.chat.id
    command = message.text.strip()
    
    target_tuple = (target_user.id, chat_id)
    if user_id not in MUTED_USERS: MUTED_USERS[user_id] = set()

    if command == "سکوت روشن":
        MUTED_USERS[user_id].add(target_tuple)
        await message.edit_text(f"🔇 **کاربر {target_user.first_name} در این چت سایلنت شد.**")
    elif command == "سکوت خاموش":
        MUTED_USERS[user_id].discard(target_tuple)
        await message.edit_text(f"🔊 **کاربر {target_user.first_name} از سایلنت خارج شد.**")
    
    db_muted = [{"user_id": u, "chat_id": c} for u, c in MUTED_USERS[user_id]]
    asyncio.create_task(update_db_settings(user_id, {"muted_users": db_muted}))

async def auto_reaction_controller(client, message):
    if not message.reply_to_message or not message.reply_to_message.from_user: return
    user_id = client.me.id
    target_user, chat_id = message.reply_to_message.from_user, message.chat.id
    command = message.text.strip()
    
    target_key = f"{target_user.id}_{chat_id}"
    if user_id not in AUTO_REACTION_TARGETS: AUTO_REACTION_TARGETS[user_id] = {}

    if command.startswith("ریاکشن") and command != "ریاکشن خاموش":
        parts = command.split(" ", 1)
        if len(parts) > 1:
            AUTO_REACTION_TARGETS[user_id][target_key] = parts[1]
            await message.edit_text(f"✅ واکنش خودکار با {parts[1]} برای {target_user.first_name} فعال شد.")
        else:
            await message.edit_text("⚠️ لطفا یک ایموجی مشخص کنید. مثال: `ریاکشن ❤️`")
    elif command == "ریاکشن خاموش":
        if AUTO_REACTION_TARGETS.get(user_id, {}).pop(target_key, None):
            await message.edit_text(f"❌ واکنش خودکار برای {target_user.first_name} غیرفعال شد.")
    
    asyncio.create_task(update_db_settings(user_id, {"auto_reaction_targets": AUTO_REACTION_TARGETS[user_id]}))

async def save_message_controller(client, message):
    if not message.reply_to_message: return
    try:
        await message.edit_text("⏳ در حال ذخیره...")
        if message.reply_to_message.media:
            file_path = await client.download_media(message.reply_to_message)
            caption = "ذخیره شده با سلف بات"
            if message.reply_to_message.photo: await client.send_photo("me", file_path, caption=caption)
            elif message.reply_to_message.video: await client.send_video("me", file_path, caption=caption)
            else: await client.send_document("me", file_path, caption=caption)
            os.remove(file_path)
        else:
            await message.reply_to_message.copy("me")
        await message.edit_text("✅ با موفقیت در Saved Messages ذخیره شد.")
    except Exception as e:
        await message.edit_text(f"⚠️ خطا در ذخیره: {e}")
        logging.error(f"Could not save message: {e}", exc_info=True)

async def repeat_message_controller(client, message):
    if not message.reply_to_message: return
    try:
        count = int(message.text.split()[1])
        if count > 100:
            await message.edit_text("⚠️ حداکثر تکرار 100 است.")
            return

        await message.delete()
        for _ in range(count):
            await message.reply_to_message.copy(message.chat.id)
            await asyncio.sleep(0.1)
    except Exception as e:
        logging.error(f"Error in repeat command: {e}")

async def toggle_controller(client, message):
    user_id = client.me.id
    command = message.text.strip()
    
    toggle_map = {
        "اینگیلیسی روشن": ("ترجمه اینگیلیسی", AUTO_TRANSLATE_STATUS, True, "auto_translate_status"),
        "اینگیلیسی خاموش": ("ترجمه اینگیلیسی", AUTO_TRANSLATE_STATUS, False, "auto_translate_status"),
        "بولد روشن": ("بولد خودکار", BOLD_MODE_STATUS, True, "bold_mode_status"),
        "بولد خاموش": ("بولد خودکار", BOLD_MODE_STATUS, False, "bold_mode_status"),
        "سین روشن": ("سین خودکار", AUTO_SEEN_STATUS, True, "auto_seen_status"),
        "سین خاموش": ("سین خودکار", AUTO_SEEN_STATUS, False, "auto_seen_status"),
        "منشی روشن": ("منشی", SECRETARY_MODE_STATUS, True, "secretary_mode_status"),
        "منشی خاموش": ("منشی", SECRETARY_MODE_STATUS, False, "secretary_mode_status"),
    }

    if command in toggle_map:
        feature_name, status_dict, new_status, db_key = toggle_map[command]
        status_dict[user_id] = new_status
        asyncio.create_task(update_db_settings(user_id, {db_key: new_status}))

        if command == "منشی روشن":
            USERS_REPLIED_IN_SECRETARY[user_id] = set()
        
        status_text = "فعال" if new_status else "غیرفعال"
        await message.edit_text(f"✅ **{feature_name} {status_text} شد.**")


# --- فیلترها و راه اندازی ربات ---
async def is_enemy_filter(_, client, message):
    user_id = client.me.id
    return message.from_user and (message.from_user.id, message.chat.id) in ACTIVE_ENEMIES.get(user_id, set())

is_enemy = filters.create(is_enemy_filter)

async def start_bot_instance(user_id: int, session_string: str, user_settings: dict):
    try:
        phone_number = user_settings.get("phone_number", f"user_{user_id}")
        client = Client(f"bot_{phone_number}", api_id=API_ID, api_hash=API_HASH, session_string=session_string, in_memory=True)
        await client.start()
        
        # Load settings from DB into memory
        USER_FONT_CHOICES[user_id] = user_settings.get("font_style", "stylized")
        CLOCK_STATUS[user_id] = user_settings.get("clock_status", True)
        BOLD_MODE_STATUS[user_id] = user_settings.get("bold_mode_status", False)
        AUTO_SEEN_STATUS[user_id] = user_settings.get("auto_seen_status", False)
        SECRETARY_MODE_STATUS[user_id] = user_settings.get("secretary_mode_status", False)
        AUTO_TRANSLATE_STATUS[user_id] = user_settings.get("auto_translate_status", False)
        ACTIVE_ENEMIES[user_id] = set(tuple(d.values()) for d in user_settings.get("active_enemies", []))
        MUTED_USERS[user_id] = set(tuple(d.values()) for d in user_settings.get("muted_users", []))
        
        db_reactions = user_settings.get("auto_reaction_targets", {})
        mem_reactions = {}
        for k, v in db_reactions.items():
            try:
                user_part, chat_part = map(int, k.split('_'))
                mem_reactions[(user_part, chat_part)] = v
            except (ValueError, AttributeError):
                continue
        AUTO_REACTION_TARGETS[user_id] = mem_reactions
        
        # Handlers Registration
        client.add_handler(MessageHandler(auto_seen_handler, filters.private & ~filters.me), group=-4)
        client.add_handler(MessageHandler(incoming_message_manager, filters.all & ~filters.me), group=-3)
        client.add_handler(MessageHandler(outgoing_message_modifier, filters.text & filters.me & ~filters.reply), group=-1)
        
        client.add_handler(MessageHandler(help_controller, filters.text & filters.me & filters.regex("^راهنما$")))
        client.add_handler(MessageHandler(toggle_controller, filters.text & filters.me & filters.regex("^(اینگیلیسی روشن|اینگیلیسی خاموش|بولد روشن|بولد خاموش|سین روشن|سین خاموش|منشی روشن|منشی خاموش)$")))
        client.add_handler(MessageHandler(font_controller, filters.text & filters.me & filters.regex(r"^(فونت|فونت \d+)$")))
        client.add_handler(MessageHandler(clock_controller, filters.text & filters.me & filters.regex("^(ساعت روشن|ساعت خاموش)$")))
        client.add_handler(MessageHandler(enemy_controller, filters.text & filters.reply & filters.me & filters.regex("^(دشمن روشن|دشمن خاموش)$")))
        client.add_handler(MessageHandler(block_unblock_controller, filters.text & filters.reply & filters.me & filters.regex("^(بلاک روشن|بلاک خاموش)$")))
        client.add_handler(MessageHandler(mute_unmute_controller, filters.text & filters.reply & filters.me & filters.regex("^(سکوت روشن|سکوت خاموش)$")))
        client.add_handler(MessageHandler(auto_reaction_controller, filters.text & filters.reply & filters.me & filters.regex("^(ریاکشن .*|ریاکشن خاموش)$")))
        client.add_handler(MessageHandler(save_message_controller, filters.text & filters.reply & filters.me & filters.regex("^ذخیره$")))
        client.add_handler(MessageHandler(repeat_message_controller, filters.text & filters.reply & filters.me & filters.regex(r"^تکرار \d+$")))
        
        client.add_handler(MessageHandler(enemy_handler, is_enemy & ~filters.me), group=1)
        client.add_handler(MessageHandler(secretary_auto_reply_handler, filters.private & ~filters.me), group=1)

        if user_id in ACTIVE_BOTS:
            if task := ACTIVE_BOTS.pop(user_id, None): task.cancel()
        ACTIVE_BOTS[user_id] = asyncio.create_task(update_profile_clock(client, user_id))
        logging.info(f"Successfully started bot instance from DB for user_id {user_id}.")
    except (AuthKeyUnregistered, UserDeactivated) as e:
        logging.error(f"FAILED to start bot instance for user {user_id} due to invalid session: {e}")
        if users_collection is not None:
            await users_collection.delete_one({'_id': user_id})
            logging.info(f"Removed invalid session for user {user_id} from database.")
            if admin_bot and ADMIN_ID:
                await admin_bot.send_message(ADMIN_ID, f"⚠️ جلسه برای کاربر با آیدی `{user_id}` منقضی شده بود و به طور خودکار از پایگاه داده حذف شد. کاربر باید مجدداً وارد شود.")
    except Exception as e:
        logging.error(f"An unexpected error occurred while starting bot for user {user_id}: {e}", exc_info=True)


# --- Admin Bot Handlers ---
async def disconnect_and_delete_user(user_id_to_disconnect: int):
    """Helper function to stop a bot and delete user data."""
    # Stop the running bot instance
    if task := ACTIVE_BOTS.pop(user_id_to_disconnect, None):
        task.cancel()
        logging.info(f"Admin disconnected bot for user {user_id_to_disconnect}.")
    
    # Remove from database
    if users_collection is not None:
        result = await users_collection.delete_one({'_id': user_id_to_disconnect})
        return result.deleted_count > 0
    return False

async def delete_user_handler(client, message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.reply_text("استفاده صحیح: `/delete <user_id>`")
        return
    
    user_id = int(parts[1])
    if await disconnect_and_delete_user(user_id):
        await message.reply_text(f"✅ کاربر با آیدی `{user_id}` با موفقیت حذف و اتصالش قطع شد.")
    else:
        await message.reply_text(f"⚠️ کاربر با آیدی `{user_id}` یافت نشد.")

async def ban_user_handler(client, message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.reply_text("استفاده صحیح: `/ban <user_id>`")
        return

    user_id = int(parts[1])
    
    # First, disconnect and delete them
    deleted = await disconnect_and_delete_user(user_id)
    
    # Then, add to ban list
    if banned_users_collection is not None:
        await banned_users_collection.update_one(
            {'_id': user_id},
            {'$set': {'banned_at': datetime.now(timezone.utc)}},
            upsert=True
        )
    
    if deleted:
        await message.reply_text(f"🚫 کاربر با آیدی `{user_id}` حذف و برای همیشه بن شد.")
    else:
        await message.reply_text(f"🚫 کاربر با آیدی `{user_id}` در لیست کاربران فعال نبود، اما به لیست بن اضافه شد.")

async def unban_user_handler(client, message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.reply_text("استفاده صحیح: `/unban <user_id>`")
        return

    user_id = int(parts[1])
    if banned_users_collection is not None:
        result = await banned_users_collection.delete_one({'_id': user_id})
        if result.deleted_count > 0:
            await message.reply_text(f"✅ کاربر با آیدی `{user_id}` از لیست بن حذف شد و اکنون می‌تواند دوباره وارد شود.")
        else:
            await message.reply_text(f"⚠️ کاربر با آیدی `{user_id}` در لیست بن یافت نشد.")
    else:
        await message.reply_text("⚠️ سرویس پایگاه داده برای لیست بن در دسترس نیست.")

async def get_users_panel():
    """Generates the text and keyboard for the admin panel."""
    if users_collection is None:
        return "پایگاه داده متصل نیست.", None
    
    users = await users_collection.find({}).to_list(length=None)
    if not users:
        return "هیچ کاربری متصل نیست.", None

    keyboard = []
    text = "👤 **لیست کاربران متصل:**\n\n"
    for user in users:
        user_id = user['_id']
        phone = user.get('phone_number', 'N/A')
        name = user.get('first_name', 'N/A')
        username = user.get('username', 'N/A')
        
        text += f"▪️ نام: {name}\n"
        text += f"▫️ یوزرنیم: @{username}\n"
        text += f"📱 شماره: `{phone}`\n"
        text += f"🆔 آیدی: `{user_id}`\n"
        text += "-"*20 + "\n"
        
        keyboard.append([InlineKeyboardButton(f"❌ قطع اتصال {name}", callback_data=f"disconnect_{user_id}")])
    
    return text, InlineKeyboardMarkup(keyboard)

async def admin_panel_handler(client, message):
    if message.from_user.id != ADMIN_ID:
        return
    text, keyboard = await get_users_panel()
    await message.reply_text(text, reply_markup=keyboard)

async def callback_query_handler(client, callback_query):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("شما ادمین نیستید!", show_alert=True)
        return
    
    data = callback_query.data
    
    if data.startswith("disconnect_"):
        try:
            user_id_to_disconnect = int(data.split("_")[1])
            
            if await disconnect_and_delete_user(user_id_to_disconnect):
                await callback_query.answer(f"کاربر {user_id_to_disconnect} با موفقیت قطع و حذف شد.", show_alert=True)
                # Refresh the panel
                text, keyboard = await get_users_panel()
                await callback_query.message.edit_text(text, reply_markup=keyboard)
            else:
                await callback_query.answer(f"کاربر {user_id_to_disconnect} در پایگاه داده یافت نشد.", show_alert=True)

        except Exception as e:
            logging.error(f"Error during disconnect callback: {e}")
            await callback_query.answer("خطایی رخ داد.", show_alert=True)

if admin_bot:
    admin_bot.add_handler(MessageHandler(admin_panel_handler, filters.command("admin") & filters.private))
    admin_bot.add_handler(MessageHandler(delete_user_handler, filters.command("delete") & filters.private))
    admin_bot.add_handler(MessageHandler(ban_user_handler, filters.command("ban") & filters.private))
    admin_bot.add_handler(MessageHandler(unban_user_handler, filters.command("unban") & filters.private))
    admin_bot.add_handler(CallbackQueryHandler(callback_query_handler))


# --- بخش وب (Flask) ---
HTML_TEMPLATE = """
<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>سلف بات ساعت تلگرام</title><style>@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap');body{font-family:'Vazirmatn',sans-serif;background-color:#f0f2f5;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;padding:20px;box-sizing:border-box;}.container{background:white;padding:30px 40px;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.1);text-align:center;width:100%;max-width:480px;}h1{color:#333;margin-bottom:20px;font-size:1.5em;}p{color:#666;line-height:1.6;}form{display:flex;flex-direction:column;gap:15px;margin-top:20px;}input[type="tel"],input[type="text"],input[type="password"]{padding:12px;border:1px solid #ddd;border-radius:8px;font-size:16px;text-align:left;direction:ltr;}button{padding:12px;background-color:#007bff;color:white;border:none;border-radius:8px;font-size:16px;cursor:pointer;transition:background-color .2s;}.error{color:#d93025;margin-top:15px;font-weight:bold;}label{font-weight:bold;color:#555;display:block;margin-bottom:5px;text-align:right;}.font-options{border:1px solid #ddd;border-radius:8px;overflow:hidden;}.font-option{display:flex;align-items:center;padding:12px;border-bottom:1px solid #ddd;cursor:pointer;}.font-option:last-child{border-bottom:none;}.font-option input[type="radio"]{margin-left:15px;}.font-option label{display:flex;justify-content:space-between;align-items:center;width:100%;font-weight:normal;cursor:pointer;}.font-option .preview{font-size:1.3em;font-weight:bold;direction:ltr;color:#0056b3;}.success{color:#1e8e3e;}.checkbox-option{display:flex;align-items:center;justify-content:flex-end;gap:10px;margin-top:10px;padding:8px;background-color:#f8f9fa;border-radius:8px;}.checkbox-option label{margin-bottom:0;font-weight:normal;cursor:pointer;color:#444;}</style></head><body><div class="container">
{% if step == 'GET_PHONE' %}<h1>ورود به سلف بات</h1><p>شماره و تنظیمات خود را انتخاب کنید تا ربات فعال شود.</p>{% if error_message %}<p class="error">{{ error_message }}</p>{% endif %}<form action="{{ url_for('login') }}" method="post"><input type="hidden" name="action" value="phone"><div><label for="phone">شماره تلفن (با کد کشور)</label><input type="tel" id="phone" name="phone_number" placeholder="+989123456789" required autofocus></div><div><label>استایل فونت ساعت</label><div class="font-options">{% for name, data in font_previews.items() %}<div class="font-option" onclick="document.getElementById('font-{{ data.style }}').checked = true;"><input type="radio" name="font_style" value="{{ data.style }}" id="font-{{ data.style }}" {% if loop.first %}checked{% endif %}><label for="font-{{ data.style }}"><span>{{ name }}</span><span class="preview">{{ data.preview }}</span></label></div>{% endfor %}</div></div><div class="checkbox-option"><input type="checkbox" id="disable_clock" name="disable_clock"><label for="disable_clock">فعال‌سازی بدون ساعت</label></div><button type="submit">ارسال کد تایید</button></form>
{% elif step == 'GET_CODE' %}<h1>کد تایید</h1><p>کدی به تلگرام شما با شماره <strong>{{ phone_number }}</strong> ارسال شد.</p>{% if error_message %}<p class="error">{{ error_message }}</p>{% endif %}<form action="{{ url_for('login') }}" method="post"><input type="hidden" name="action" value="code"><input type="text" name="code" placeholder="Verification Code" required><button type="submit">تایید کد</button></form>
{% elif step == 'GET_PASSWORD' %}<h1>رمز دو مرحله‌ای</h1><p>حساب شما نیاز به رمز تایید دو مرحله‌ای دارد.</p>{% if error_message %}<p class="error">{{ error_message }}</p>{% endif %}<form action="{{ url_for('login') }}" method="post"><input type="hidden" name="action" value="password"><input type="password" name="password" placeholder="2FA Password" required><button type="submit">ورود</button></form>
{% elif step == 'SHOW_SUCCESS' %}<h1 class="success">✅ ربات فعال شد!</h1><p>ربات با موفقیت فعال شد. برای دسترسی به قابلیت‌ها، در تلگرام پیام `راهنما` را ارسال کنید.</p><form action="{{ url_for('home') }}" method="get" style="margin-top: 20px;"><button type="submit">خروج و ورود مجدد</button></form>{% endif %}</div></body></html>
"""

def get_font_previews():
    sample_time = "12:34"
    return {FONT_DISPLAY_NAMES[key]: {"style": key, "preview": stylize_time(sample_time, key)} for key in FONT_KEYS_ORDER}

async def cleanup_client(phone):
    if client := ACTIVE_CLIENTS.pop(phone, None):
        if client.is_connected: await client.disconnect()

@app_flask.route('/')
def home():
    session.clear()
    return render_template_string(HTML_TEMPLATE, step='GET_PHONE', font_previews=get_font_previews())

@app_flask.route('/login', methods=['POST'])
def login():
    action = request.form.get('action')
    phone = session.get('phone_number')
    try:
        if users_collection is None and action in ['code', 'password']:
            raise Exception("پایگاه داده متصل نیست. لطفا متغیر MONGO_URI را تنظیم کنید.")

        if action == 'phone':
            session['phone_number'] = request.form.get('phone_number')
            session['font_style'] = request.form.get('font_style')
            session['disable_clock'] = 'on' == request.form.get('disable_clock')
            asyncio.run_coroutine_threadsafe(send_code_task(session['phone_number']), EVENT_LOOP).result(45)
            return render_template_string(HTML_TEMPLATE, step='GET_CODE', phone_number=session['phone_number'])
        elif action == 'code':
            next_step = asyncio.run_coroutine_threadsafe(sign_in_task(phone, request.form.get('code')), EVENT_LOOP).result(45)
            if next_step == 'GET_PASSWORD':
                return render_template_string(HTML_TEMPLATE, step='GET_PASSWORD', phone_number=phone)
            return render_template_string(HTML_TEMPLATE, step='SHOW_SUCCESS')
        elif action == 'password':
            asyncio.run_coroutine_threadsafe(check_password_task(phone, request.form.get('password')), EVENT_LOOP).result(45)
            return render_template_string(HTML_TEMPLATE, step='SHOW_SUCCESS')
    except Exception as e:
        if phone: asyncio.run_coroutine_threadsafe(cleanup_client(phone), EVENT_LOOP)
        logging.error(f"Error during '{action}': {e}", exc_info=True)
        error_map = {
            (PhoneCodeInvalid, PasswordHashInvalid): "کد یا رمز وارد شده اشتباه است.",
            (PhoneNumberInvalid, TypeError): "شماره تلفن نامعتبر است.",
            PhoneCodeExpired: "کد تایید منقضی شده، دوباره تلاش کنید.",
            FloodWait: f"محدودیت تلگرام. لطفا {getattr(e, 'value', 5)} ثانیه دیگر تلاش کنید."
        }
        error_msg = str(e)
        current_step = 'GET_PHONE'
        for err_types, msg in error_map.items():
            if isinstance(e, err_types):
                error_msg = msg
                break
        
        if "بن شده‌اید" in error_msg:
             current_step = 'GET_PHONE'
             session.clear()
        elif isinstance(e, PhoneCodeInvalid): current_step = 'GET_CODE'
        elif isinstance(e, PasswordHashInvalid): current_step = 'GET_PASSWORD'
        
        if current_step == 'GET_PHONE': session.clear()
        return render_template_string(HTML_TEMPLATE, step=current_step, error_message=error_msg, phone_number=phone, font_previews=get_font_previews())
    return redirect(url_for('home'))

async def send_code_task(phone):
    await cleanup_client(phone)
    client = Client(f"user_{phone}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
    ACTIVE_CLIENTS[phone] = client
    await client.connect()
    session['phone_code_hash'] = (await client.send_code(phone)).phone_code_hash

async def process_successful_login(client: Client, phone: str):
    me = await client.get_me()
    user_id = me.id

    # Check if user is banned
    if banned_users_collection is not None:
        is_banned = await banned_users_collection.find_one({'_id': user_id})
        if is_banned:
            logging.warning(f"Banned user {user_id} tried to log in.")
            raise Exception("شما توسط ادمین بن شده‌اید و اجازه ورود ندارید.")

    session_str = await client.export_session_string()
    
    user_settings = {
        "phone_number": phone,
        "font_style": session.get('font_style', 'stylized'),
        "clock_status": not session.get('disable_clock', False),
        "session_string": session_str,
        "first_name": me.first_name,
        "username": me.username or "N/A"
    }
    
    await users_collection.update_one(
        {'_id': user_id},
        {'$set': user_settings},
        upsert=True
    )
    
    # Notify Admin
    if admin_bot and ADMIN_ID:
        try:
            admin_message = (
                f"✅ **کاربر جدید متصل شد**\n\n"
                f"👤 **نام:** {me.first_name}\n"
                f"✒️ **یوزرنیم:** @{me.username}\n"
                f"📞 **شماره:** `{phone}`\n"
                f"🆔 **آیدی:** `{user_id}`\n\n"
                f"💾 اطلاعات با موفقیت در MongoDB ذخیره شد."
            )
            await admin_bot.send_message(ADMIN_ID, admin_message)
        except Exception as e:
            logging.error(f"Could not send admin notification: {e}")

    await start_bot_instance(user_id, session_str, user_settings)
    await cleanup_client(phone)

async def sign_in_task(phone, code):
    client = ACTIVE_CLIENTS.get(phone)
    if not client: raise Exception("Session expired.")
    try:
        await client.sign_in(phone, session['phone_code_hash'], code)
        await process_successful_login(client, phone)
    except SessionPasswordNeeded:
        return 'GET_PASSWORD'

async def check_password_task(phone, password):
    client = ACTIVE_CLIENTS.get(phone)
    if not client: raise Exception("Session expired.")
    try:
        await client.check_password(password)
        await process_successful_login(client, phone)
    finally:
        pass

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port)

async def load_and_start_bots():
    if users_collection is None:
        logging.warning("Skipping bot auto-start because database is not connected.")
        return
    
    logging.info("Loading users from database and starting bots...")
    try:
        async for user_data in users_collection.find({}):
            user_id = user_data['_id']
            session_string = user_data.get('session_string')
            if not session_string:
                logging.warning(f"No session string found for user {user_id}, skipping.")
                continue
            
            if user_id in ACTIVE_BOTS:
                logging.info(f"Bot for user {user_id} is already running or starting.")
                continue
            
            await start_bot_instance(user_id, session_string, user_data)
    except Exception as e:
        logging.error(f"An error occurred while loading bots from DB: {e}", exc_info=True)

async def start_admin_bot():
    if admin_bot:
        try:
            await admin_bot.start()
            logging.info("Admin bot started successfully.")
            if ADMIN_ID:
                await admin_bot.send_message(
                    ADMIN_ID,
                    "🤖 **ربات ادمین آنلاین است.**\n\n"
                    "دستورات موجود:\n"
                    "`/admin` - نمایش پنل مدیریت کاربران\n"
                    "`/delete <user_id>` - حذف کاربر\n"
                    "`/ban <user_id>` - بن کردن دائمی کاربر\n"
                    "`/unban <user_id>` - حذف کاربر از لیست بن"
                )
        except Exception as e:
            logging.error(f"Failed to start admin bot: {e}")

def run_asyncio_loop():
    try:
        asyncio.set_event_loop(EVENT_LOOP)
        if MONGO_URI:
            EVENT_LOOP.create_task(load_and_start_bots())
        if BOT_TOKEN and ADMIN_ID:
             EVENT_LOOP.create_task(start_admin_bot())
        EVENT_LOOP.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if admin_bot and admin_bot.is_connected:
            EVENT_LOOP.run_until_complete(admin_bot.stop())
        logging.info("Closing asyncio event loop.")
        EVENT_LOOP.close()

if __name__ == "__main__":
    if not all([BOT_TOKEN, ADMIN_ID]):
        logging.warning("BOT_TOKEN or ADMIN_ID is not set. Admin features will be disabled.")
    logging.info("Starting Telegram Clock Bot Service...")
    loop_thread = Thread(target=run_asyncio_loop, daemon=True)
    loop_thread.start()
    run_flask()

