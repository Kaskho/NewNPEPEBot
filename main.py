import os
import logging
from flask import Flask, request, abort
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import groq
import random

# ==========================
# 🔧 CONFIGURATION
# ==========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Config:
    """Configuration class for the bot."""
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    GROUP_CHAT_ID = os.environ.get("GROUP_CHAT_ID")
    TRIGGER_SECRET = os.environ.get("TRIGGER_SECRET", "default-secret-key-change-me")
    GROUP_OWNER_ID = os.environ.get("GROUP_OWNER_ID")

    if not all([BOT_TOKEN, WEBHOOK_BASE_URL, GROUP_CHAT_ID]):
        logger.error("FATAL: One or more essential environment variables are missing.")

    WEBHOOK_URL = f"{WEBHOOK_BASE_URL}/{BOT_TOKEN}"

    # Project Details
    CONTRACT_ADDRESS = "BJ65ym9UYPkcfLSUuE9j4uXYuiG6TgA4pFn393Eppump"
    PUMP_FUN_LINK = f"https://pump.fun/{CONTRACT_ADDRESS}"
    WEBSITE_URL = "https://next-pepe-launchpad-2b8b3071.base44.app"
    TELEGRAM_URL = "https://t.me/NPEPEVERSE"
    TWITTER_URL = "https://x.com/NPEPE_Verse?t=rFeVwGRDJpxwiwjQ8P67Xw&s=09"

# ==========================
# 🚀 INITIALIZE APP & BOT
# ==========================
bot = telebot.TeleBot(Config.BOT_TOKEN, threaded=False)
app = Flask(__name__)

# (All other code sections like AI init, message lists, keyboards, etc. remain the same)
# ...

# ==========================
# 🤖 BOT COMMAND HANDLERS
# ==========================

# --- NEW: Greet New Members ---
@bot.message_handler(content_types=['new_chat_members'])
def greet_new_members(message):
    for new_member in message.new_chat_members:
        # Get the new member's first name, sanitize it for Markdown
        first_name = new_member.first_name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
        
        welcome_message = (
            f"🐸 Welcome to the Pepeverse, [{first_name}](tg://user?id={new_member.id})!\n\n"
            "We're glad to have you with us. Feel free to ask any questions or use the /start command to see what I can do. LFG! 🚀"
        )
        try:
            bot.send_message(message.chat.id, welcome_message, parse_mode="Markdown")
            logger.info(f"Welcomed new member: {first_name} (ID: {new_member.id})")
        except Exception as e:
            logger.error(f"Failed to welcome new member: {e}")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    # ... (rest of the code is unchanged)
    pass

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    # ... (rest of the code is unchanged)
    pass

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_all_text_messages(message):
    # ... (rest of the code is unchanged)
    pass

# (All scheduled greeting triggers and webhook setup remain the same)
# ...
