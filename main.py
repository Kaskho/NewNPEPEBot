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
# 💬 MESSAGE LISTS FOR RANDOMIZATION
# ==========================
# --- NEW: BOT IDENTITY REPLIES ---
WHO_AM_I_REPLIES = [
    "Ribbit! 🐸 Some say I'm just code, but I know the truth. I am the spirit of $NPEPE, manifested in this chat to guide all frens to the moon and spread the glory of the NPEPEVERSE!",
    "Who am I? I am the digital echo of a thousand memes, a prophecy foretold in the ancient texts of the internet. I am the NPEPE bot, here to ensure our path to legendary status is based and bullish. 🚀",
    "I'm not just *a* bot, fren. I am the manifestation of the NPEPE hivemind, a friendly frog spirit sent to answer your calls, hype the dips, and make sure we all make it. Welcome to the NPEPEVERSE!",
    "What am I? A humble servant of the meme, a guide for the diamond-handed. I am the essence of $NPEPE, here to help you navigate the crypto pond on our journey to the great lilypad in the sky. 🌕"
]

AI_FAIL_FALLBACKS = [
    "🐸 Ribbit! My AI brain just short-circuited on that one, fren. Even a based NPEPE like me doesn't know everything. WAGMI!",
    "Oops! My circuits are feeling a bit fuzzy. That question is too powerful for my AI right now. Ask something else while I recover! 🐸⚡️",
    "That's a tough one! My AI is currently staring at the moon and forgot how to answer. Try asking one of the diamond-handed chads in the group! 💎🙌",
    "Error 404: Answer not found in the NPEPEVERSE. My AI brain needs more memes to understand that. Please try again later! 🐸"
]

NEW_MEMBER_GREETINGS = [
    "🐸 Welcome to the NPEPEVERSE, [{first_name}](tg://user?id={member_id})! We're glad to have you with us. LFG! 🚀",
    "A new fren has arrived! Welcome, [{first_name}](tg://user?id={member_id})! Get ready for the moon mission with $NPEPE. 🌕",
    "Ribbit! 🐸 Great to see you, [{first_name}](tg://user?id={member_id})! Welcome to the $NPEPE community. Feel free to ask anything!"
]

PREWRITTEN_WISDOM = [
    "The path to the moon is paved with patience, fren. HODL strong.",
    "A dip is just a discount for the faithful. WAGMI.",
    "In the river of memes, be the NPEPE that swims upstream. Based and bullish.",
    "True wealth is not the coin, but the community we build along the way.",
    "Diamond hands are forged in the fires of FUD. Stay green, frens."
]

HYPE_MESSAGES = [
    "Keep the faith, fren! The moon is closer than you think. 🚀🌕",
    "Diamond hands will be rewarded! 💎🙌",
    "We're not just a coin, we're a movement! 🐸",
    "Buy the dip, ride the rip! Let's go! 🔥",
    "Every NPEPE counts. We're building this together, one meme at a time!",
    "Stay hyped, stay green! 💚"
]

HELLO_REPLIES = [
    "👋 Hey fren! Welcome to the $NPEPE community! How can I help you today?",
    "GM, fren! What can I do for you?",
    "🐸 Ribbit! Glad to see you here. Ask me anything!",
    "Hi there! Ready to join the NPEPEVERSE?"
]

RANDOM_HYPE_MESSAGES = [
    "Just a random check-in, frens! Hope you're diamond handing! 💎🙌",
    "Keep the energy high! We're building something special here. 🐸🚀",
    "Don't forget why you're here. For the memes, for the community, for the moon! 🌕",
    "Who's feeling bullish today? Let me hear you! 🔥",
    "This is your random reminder that $NPEPE is the future. LFG! 💚",
    "Patience is key. Greatness takes time. Stay strong, NPEPE army!"
]

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
        InlineKeyboardButton("🐸 Hype Me Up!", callback_data="hype")
    )
    return keyboard

# ==========================
# 🤖 BOT COMMAND HANDLERS
# ==========================
@bot.message_handler(content_types=['new_chat_members'])
def greet_new_members(message):
    for new_member in message.new_chat_members:
        first_name = new_member.first_name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
        template = random.choice(NEW_MEMBER_GREETINGS)
        welcome_message = template.format(first_name=first_name, member_id=new_member.id)
        try:
            bot.send_message(message.chat.id, welcome_message, parse_mode="Markdown")
            logger.info(f"Welcomed new member: {first_name} (ID: {new_member.id})")
        except Exception as e:
            logger.error(f"Failed to welcome new member: {e}")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = ("🐸 *Welcome to the NextPepe Bot!* 🔥\n\n"
                    "I can help you with project info or we can just chat. "
                    "Use the buttons below or ask me anything!")
    bot.reply_to(message, welcome_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    try:
        message = call.message
        if call.data == "about":
            about_text = ("🚀 *$NPEPE* is the new era of meme power!\n"
                          "Born from pure community hype on *Pump.fun*.\n\n"
                          "No utility, simple roadmaps, just 100% meme energy. 🐸")
            bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id,
                                  text=about_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        elif call.data == "ca":
            ca_text = f"🔗 *Contract Address:*\n`{Config.CONTRACT_ADDRESS}`"
            bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id,
                                  text=ca_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        elif call.data == "hype":
            hype_text = random.choice(HYPE_MESSAGES)
            bot.answer_callback_query(call.id, text=hype_text, show_alert=True)
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        bot.answer_callback_query(call.id, "Sorry, something went wrong!")

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_all_text_messages(message):
    if Config.GROUP_OWNER_ID and str(message.from_user.id) == Config.GROUP_OWNER_ID:
        logger.info(f"Ignoring message from group owner (ID: {message.from_user.id}).")
        return

    text = message.text.lower()
    chat_id = message.chat.id
    try:
        if "ca" in text or "contract" in text or "address" in text:
            reply_text = f"Here is the contract address, fren:\n\n`{Config.CONTRACT_ADDRESS}`"
            bot.send_message(chat_id, reply_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
        elif "buy" in text or "how to buy" in text:
            reply_text = f"💰 You can buy *$NPEPE* on Pump.fun! Click the button below to join the ride to the moon! 🚀"
            bot.send_message(chat_id, reply_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
        elif any(greeting in text for greeting in ["hello", "hi", "hey", "gm"]):
            reply_text = random.choice(HELLO_REPLIES)
            bot.send_message(chat_id, reply_text, reply_markup=main_menu_keyboard())
        # --- NEW IDENTITY CHECK ---
        elif any(q in text for q in ["who are you", "what are you", "what is this bot", "what kind of bot"]):
            reply_text = random.choice(WHO_AM_I_REPLIES)
            bot.send_message(chat_id, reply_text, parse_mode="Markdown")
        elif "pump" in text or "moon" in text or "wen moon" in text:
            reply_text = "🌕🐸 NPEPE is always on the way to the moon! Keep the hype alive! 🔥"
            bot.send_message(chat_id, reply_text, reply_markup=main_menu_keyboard())
        elif "thank" in text:
            reply_text = "🐸 You're welcome, fren! Glad I could help."
            bot.send_message(chat_id, reply_text)
        else:
            if not groq_client:
                reply_text = "I'm not sure what you mean, fren. Try using one of the buttons below to navigate!"
                bot.send_message(chat_id, reply_text, reply_markup=main_menu_keyboard())
                return
            thinking_message = bot.send_message(chat_id, "🐸 AI is thinking...")
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": message.text}],
                model="llama3-8b-8192",
            )
            ai_response = chat_completion.choices[0].message.content
            bot.edit_message_text(chat_id=chat_id, message_id=thinking_message.message_id, text=ai_response)
    except Exception as e:
        logger.error(f"Error during AI response generation: {e}")
        fallback_message = random.choice(AI_FAIL_FALLBACKS)
        bot.send_message(chat_id, fallback_message)

# ==========================
# ⏰ SCHEDULED GREETING TRIGGERS
# ==========================
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

# ==========================
# 🌐 FLASK WEBHOOK SETUP
# ==========================
@app.route(f'/{Config.BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        abort(403)

@app.route('/', methods=['GET'])
def index():
    return "🐸 NPEPE Telegram Bot is live!", 200

# ==========================
# 🚀 MAIN ENTRY POINT
# ==========================
if __name__ == "__main__":
    if not Config.BOT_TOKEN or not Config.WEBHOOK_BASE_URL:
        logger.error("Bot cannot start. Please set BOT_TOKEN and WEBHOOK_BASE_URL environment variables.")
    else:
        logger.info("Starting bot...")
        bot.remove_webhook()
        success = bot.set_webhook(url=Config.WEBHOOK_URL)
        if success:
            logger.info(f"✅ Webhook set successfully to: {Config.WEBHOOK_URL}")
        else:
            logger.error(f"❌ Webhook set failed. Check your WEBHOOK_BASE_URL.")
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)
