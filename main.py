import os
import logging
from flask import Flask, request, abort
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import groq
import random
import time
import json # <-- New import for parsing AI responses

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

# ==========================
# 💬 DYNAMIC MESSAGE LISTS (NOW GLOBAL VARIABLES)
# ==========================
# These lists are now global variables so they can be updated by the AI.
# They start with default values.

WHO_AM_I_REPLIES = [
    "Ribbit! 🐸 Some say I'm just code, but I know the truth. I am the spirit of $NPEPE, manifested in this chat to guide all frens to the moon and spread the glory of the NPEPEVERSE!",
    "Who am I? I am the digital echo of a thousand memes, a prophecy foretold in the ancient texts of the internet. I am the NPEPE bot, here to ensure our path to legendary status is based and bullish. 🚀",
]
AI_FAIL_FALLBACKS = [
    "🐸 Ribbit! My AI brain just short-circuited on that one, fren. Even a based NPEPE like me doesn't know everything. WAGMI!",
    "Oops! My circuits are feeling a bit fuzzy. That question is too powerful for my AI right now. Ask something else while I recover! 🐸⚡️",
]
NEW_MEMBER_GREETINGS = [
    "🐸 Welcome to the NPEPEVERSE, [{first_name}](tg://user?id={member_id})! We're glad to have you with us. LFG! 🚀",
    "A new fren has arrived! Welcome, [{first_name}](tg://user?id={member_id})! Get ready for the moon mission with $NPEPE. 🌕",
]
PREWRITTEN_WISDOM = [
    "The path to the moon is paved with patience, fren. HODL strong.",
    "A dip is just a discount for the faithful. WAGMI.",
]
HYPE_MESSAGES = [
    "Keep the faith, fren! The moon is closer than you think. 🚀🌕",
    "Diamond hands will be rewarded! 💎🙌",
]
HELLO_REPLIES = [
    "👋 Hey fren! Welcome to the $NPEPE community! How can I help you today?",
    "GM, fren! What can I do for you?",
]
RANDOM_HYPE_MESSAGES = [
    "Just a random check-in, frens! Hope you're diamond handing! 💎🙌",
    "Keep the energy high! We're building something special here. 🐸🚀",
]
CTA_BUY_REPLIES = [
    "Don't just stare at it, fren! That's your ticket to the moon. Smash that buy button! 🚀🐸",
    "What are you waiting for? An invitation from the moon itself? WAGMI, but only if you're in! Go get some $NPEPE! 🔥",
]

# (The rest of the bot's code follows, using these global variables)
# ... all other functions from the previous version are here ...

# ==========================
# ⏰ SCHEDULED GREETING TRIGGERS & NEW AI REFRESH
# ==========================

# --- NEW: AI CONTENT REFRESH TRIGGER ---
@app.route(f'/trigger-refresh-lists/{Config.TRIGGER_SECRET}', methods=['GET', 'POST'])
def scheduled_content_refresh():
    if not groq_client:
        logger.error("Cannot refresh content: Groq AI client not initialized.")
        return "Error: AI client not available", 500

    logger.info("🤖 Starting weekly AI content refresh...")

    # Define prompts for each list we want to refresh
    prompts = {
        'HELLO_REPLIES': "Generate 5 fresh, friendly ways to say hello to a user in a crypto meme coin community named $NPEPE. Use words like 'fren', 'GM', 'ribbit'. Return them as a JSON formatted list of strings.",
        'HYPE_MESSAGES': "Generate 5 short, exciting hype messages for the $NPEPE crypto community to be shown when a user clicks a 'Hype Me Up' button. Use emoji and words like 'moon', 'WAGMI', 'diamond hands'. Return them as a JSON formatted list of strings.",
        'RANDOM_HYPE_MESSAGES': "Generate 5 random, spontaneous hype messages for the $NPEPE crypto community to be sent at random times. They should be encouraging and build community spirit. Return them as a JSON formatted list of strings.",
        'CTA_BUY_REPLIES': "Generate 5 funny and urgent call-to-action messages to convince a user to buy the $NPEPE meme coin right after they've asked for the contract address. Be playful and use meme culture language. Return them as a JSON formatted list of strings."
    }

    # Declare which global variables we are going to change
    global HELLO_REPLIES, HYPE_MESSAGES, RANDOM_HYPE_MESSAGES, CTA_BUY_REPLIES

    for list_name, prompt_text in prompts.items():
        try:
            logger.info(f"Refreshing {list_name}...")
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt_text}],
                model="llama3-8b-8192",
            )
            ai_response_str = chat_completion.choices[0].message.content
            
            # Parse the JSON string from the AI into a Python list
            new_list = json.loads(ai_response_str)

            if isinstance(new_list, list) and all(isinstance(item, str) for item in new_list):
                # Update the correct global variable
                globals()[list_name] = new_list
                logger.info(f"✅ Successfully updated {list_name} with {len(new_list)} new items.")
            else:
                logger.warning(f"⚠️ AI did not return a valid list of strings for {list_name}.")

        except Exception as e:
            logger.error(f"❌ Failed to refresh {list_name}: {e}")
        
        time.sleep(5) # Small delay to avoid hitting rate limits

    return "Content refresh cycle completed.", 200

# (All other scheduled triggers like morning, noon, night, etc. remain the same)
# ...
@app.route(f'/trigger-wisdom-greeting/{Config.TRIGGER_SECRET}', methods=['GET', 'POST'])
def scheduled_wisdom_greeting():
    if not Config.GROUP_CHAT_ID:
        logger.error("Cannot send wisdom: GROUP_CHAT_ID not set.")
        return "Error: Chat ID not configured", 500
    wisdom_message = ""
    use_ai = random.choice([True, False])
    if use_ai and groq_client:
        logger.info("Attempting to generate AI wisdom...")
        try:
            prompt = ("Generate a short, wise, and motivational quote in the style of NPEPE for a crypto community. "
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
    full_message = f"**🐸 Daily Dose of NPEPE Wisdom 📜**\n\n_{wisdom_message}_"
    try:
        bot.send_message(Config.GROUP_CHAT_ID, full_message, parse_mode="Markdown")
        logger.info(f"Successfully sent scheduled WISDOM greeting to chat ID {Config.GROUP_CHAT_ID}")
        return "Wisdom greeting sent successfully", 200
    except Exception as e:
        logger.error(f"Failed to send scheduled wisdom message: {e}")
        return f"Error sending wisdom message: {e}", 500

@app.route(f'/trigger-morning-greeting/{Config.TRIGGER_SECRET}', methods=['GET', 'POST'])
def scheduled_morning_greeting():
    if not Config.GROUP_CHAT_ID: return "Error", 500
    try:
        morning_greetings = ["🐸☀️ Rise and shine, NPEPE army! Let's make it a great day! 🔥🚀",
            "Good morning, legends! 🐸 Hope your bags are packed for the moon! 🚀🌕",
            "Wakey wakey, frens! 🐸 A new day to pump it! Let's get this digital green! 💚",]
        bot.send_message(Config.GROUP_CHAT_ID, random.choice(morning_greetings))
        return "OK", 200
    except Exception as e: return f"Error: {e}", 500

@app.route(f'/trigger-noon-greeting/{Config.TRIGGER_SECRET}', methods=['GET', 'POST'])
def scheduled_noon_greeting():
    if not Config.GROUP_CHAT_ID: return "Error", 500
    try:
        noon_greetings = ["🐸☀️ Hope you're having a fantastic day so far, NPEPE fam!",
            "Just checking in! Keep the energy high this afternoon! 🚀",]
        bot.send_message(Config.GROUP_CHAT_ID, random.choice(noon_greetings))
        return "OK", 200
    except Exception as e: return f"Error: {e}", 500

@app.route(f'/trigger-night-greeting/{Config.TRIGGER_SECRET}', methods=['GET', 'POST'])
def scheduled_night_greeting():
    if not Config.GROUP_CHAT_ID: return "Error", 500
    try:
        night_greetings = ["🐸🌙 Good night, NPEPE army! Rest up for another day of wins tomorrow.",
            "Hope you had a legendary day! See you in the NPEPEVERSE tomorrow. 💤",]
        bot.send_message(Config.GROUP_CHAT_ID, random.choice(night_greetings))
        return "OK", 200
    except Exception as e: return f"Error: {e}", 500

@app.route(f'/trigger-random-greeting/{Config.TRIGGER_SECRET}', methods=['GET', 'POST'])
def scheduled_random_greeting():
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
