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

# (All message lists and AI initialization code remains the same)
# ...

# ==========================
# ⏰ SCHEDULED GREETING TRIGGERS (NOW UPDATED FOR FREE UPTIMEROBOT)
# ==========================
@app.route(f'/trigger-wisdom-greeting/{Config.TRIGGER_SECRET}', methods=['GET', 'POST']) # <-- CHANGED
def scheduled_wisdom_greeting():
    # ... (function logic is unchanged)
    if not Config.GROUP_CHAT_ID:
        logger.error("Cannot send wisdom: GROUP_CHAT_ID not set.")
        return "Error: Chat ID not configured", 500
    wisdom_message = ""
    use_ai = random.choice([True, False])
    if use_ai and groq_client:
        logger.info("Attempting to generate AI wisdom...")
        try:
            prompt = ("Generate a short, wise, and motivational quote in the style of Pepe the Frog for a crypto community. "
                      "Use words like 'fren', 'moon', 'HODL', 'WAGMI', 'based'. Keep it under 25 words.")
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-8b-8192",)
            wisdom_message = chat_completion.choices[0].message.content
            logger.info("Successfully generated AI wisdom.")
        except Exception as e:
            logger.error(f"AI wisdom generation failed: {e}. Falling back to pre-written.")
            wisdom_message = random.choice(PREWRITTEN_WISDOM)
    else:
        logger.info("Using a pre-written wisdom quote.")
        wisdom_message = random.choice(PREWRITTEN_WISDOM)
    full_message = f"**🐸 Daily Dose of Pepe Wisdom 📜**\n\n_{wisdom_message}_"
    try:
        bot.send_message(Config.GROUP_CHAT_ID, full_message, parse_mode="Markdown")
        logger.info(f"Successfully sent scheduled WISDOM greeting to chat ID {Config.GROUP_CHAT_ID}")
        return "Wisdom greeting sent successfully", 200
    except Exception as e:
        logger.error(f"Failed to send scheduled wisdom message: {e}")
        return f"Error sending wisdom message: {e}", 500


@app.route(f'/trigger-morning-greeting/{Config.TRIGGER_SECRET}', methods=['GET', 'POST']) # <-- CHANGED
def scheduled_morning_greeting():
    # ... (function logic is unchanged)
    if not Config.GROUP_CHAT_ID: return "Error", 500
    try:
        morning_greetings = ["🐸☀️ Rise and shine, Pepe army! Let's make it a great day! 🔥🚀",
            "Good morning, legends! 🐸 Hope your bags are packed for the moon! 🚀🌕",
            "Wakey wakey, frens! 🐸 A new day to pump it! Let's get this digital green! 💚",]
        bot.send_message(Config.GROUP_CHAT_ID, random.choice(morning_greetings))
        return "OK", 200
    except Exception as e: return f"Error: {e}", 500

@app.route(f'/trigger-noon-greeting/{Config.TRIGGER_SECRET}', methods=['GET', 'POST']) # <-- CHANGED
def scheduled_noon_greeting():
    # ... (function logic is unchanged)
    if not Config.GROUP_CHAT_ID: return "Error", 500
    try:
        noon_greetings = ["🐸☀️ Hope you're having a fantastic day so far, Pepe fam!",
            "Just checking in! Keep the energy high this afternoon! 🚀",]
        bot.send_message(Config.GROUP_CHAT_ID, random.choice(noon_greetings))
        return "OK", 200
    except Exception as e: return f"Error: {e}", 500

@app.route(f'/trigger-night-greeting/{Config.TRIGGER_SECRET}', methods=['GET', 'POST']) # <-- CHANGED
def scheduled_night_greeting():
    # ... (function logic is unchanged)
    if not Config.GROUP_CHAT_ID: return "Error", 500
    try:
        night_greetings = ["🐸🌙 Good night, Pepe army! Rest up for another day of wins tomorrow.",
            "Hope you had a legendary day! See you in the Pepeverse tomorrow. 💤",]
        bot.send_message(Config.GROUP_CHAT_ID, random.choice(night_greetings))
        return "OK", 200
    except Exception as e: return f"Error: {e}", 500

@app.route(f'/trigger-random-greeting/{Config.TRIGGER_SECRET}', methods=['GET', 'POST']) # <-- CHANGED
def scheduled_random_greeting():
    # ... (function logic is unchanged)
    if not Config.GROUP_CHAT_ID:
        logger.error("Cannot send scheduled message: GROUP_CHAT_ID not set.")
        return "Error: Chat ID not configured", 500
    try:
        greeting_message = random.choice(RANDOM_HYPE_MESSAGES)
        bot.send_message(Config.GROUP_CHAT_ID, greeting_message)
        logger.info(f"Successfully sent scheduled RANDOM greeting to chat ID {Config.GROUP_CHAT_ID}")
        return "Random greeting sent successfully", 200
    except Exception as e:
        logger.error(f"Failed to send scheduled random message: {e}")
        return f"Error sending random message: {e}", 500

# (The rest of the file, including webhook setup and startup, is the same)
# ...
