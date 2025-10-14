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

    if not all([BOT_TOKEN, WEBHOOK_BASE_URL, GROUP_CHAT_ID]):
        logger.error("FATAL: One or more essential environment variables are missing.")

    WEBHOOK_URL = f"{WEBHOOK_BASE_URL}/{BOT_TOKEN}"

    # --- UPDATED PROJECT DETAILS ---
    CONTRACT_ADDRESS = "BJ65ym9UYPkcfLSUuE9j4uXYuiG6TgA4pFn393Eppump"
    PUMP_FUN_LINK = f"https://pump.fun/{CONTRACT_ADDRESS}" # Corrected URL structure
    WEBSITE_URL = "https://next-pepe-launchpad-2b8b3071.base44.app"
    TELEGRAM_URL = "https://t.me/NPEPEVERSE"
    TWITTER_URL = "https://x.com/NPEPE_Verse?t=rFeVwGRDJpxwiwjQ8P67Xw&s=09"

# ==========================
# 💬 MESSAGE LISTS FOR RANDOMIZATION
# ==========================
PREWRITTEN_WISDOM = [
    "The path to the moon is paved with patience, fren. HODL strong.",
    "A dip is just a discount for the faithful. WAGMI.",
    "In the river of memes, be the Pepe that swims upstream. Based and bullish.",
    "True wealth is not the coin, but the community we build along the way.",
    "Diamond hands are forged in the fires of FUD. Stay green, frens."
]

HYPE_MESSAGES = [
    "Keep the faith, fren! The moon is closer than you think. 🚀🌕",
    "Diamond hands will be rewarded! 💎🙌",
    "We're not just a coin, we're a movement! 🐸",
    "Buy the dip, ride the rip! Let's go! 🔥",
    "Every Pepe counts. We're building this together, one meme at a time!",
    "Stay hyped, stay green! 💚"
]

HELLO_REPLIES = [
    "👋 Hey fren! Welcome to the $NPEPE community! How can I help you today?",
    "GM, fren! What can I do for you?",
    "🐸 Ribbit! Glad to see you here. Ask me anything!",
    "Hi there! Ready to join the Pepeverse?"
]

RANDOM_HYPE_MESSAGES = [
    "Just a random check-in, frens! Hope you're diamond handing! 💎🙌",
    "Keep the energy high! We're building something special here. 🐸🚀",
    "Don't forget why you're here. For the memes, for the community, for the moon! 🌕",
    "Who's feeling bullish today? Let me hear you! 🔥",
    "This is your random reminder that $NPEPE is the future. LFG! 💚",
    "Patience is key. Greatness takes time. Stay strong, Pepe army!"
]

# ==========================
# 🧠 AI INITIALIZATION
# ==========================
groq_client = None
if Config.GROQ_API_KEY:
    try:
        groq_client = groq.Groq(api_key=Config.GROQ_API_KEY)
        logger.info("✅ Groq AI client initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Groq AI client: {e}")
else:
    logger.info("ℹ️ No GROQ_API_KEY found, AI chat and AI wisdom are disabled.")

# Initialize bot & app
bot = telebot.TeleBot(Config.BOT_TOKEN, threaded=False)
app = Flask(__name__)

# ==========================
# ⌨️ INTERACTIVE KEYBOARDS
# ==========================
def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🚀 About $NPEPE", callback_data="about"),
        InlineKeyboardButton("🔗 Contract Address", callback_data="ca"),
        InlineKeyboardButton("💰 Buy on Pump.fun", url=Config.PUMP_FUN_LINK),
        InlineKeyboardButton("🌐 Website", url=Config.WEBSITE_URL),
        InlineKeyboardButton("✈️ Telegram", url=Config.TELEGRAM_URL),
        InlineKeyboardButton("🐦 Twitter", url=Config.TWITTER_URL),
        InlineKeyboard
