
import os
import logging
from flask import Flask, request, abort
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import google.generativeai as genai

# ==========================
# 🔧 CONFIGURATION
# ==========================
# Set up basic logging to see bot activity and errors.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Config:
    """
    Configuration class for the bot.
    Using a class keeps all settings neatly organized.
    """
    # Load settings from environment variables for security.
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

    # Validate essential configuration.
    if not BOT_TOKEN:
        logger.error("FATAL: BOT_TOKEN environment variable not set.")
    if not WEBHOOK_BASE_URL:
        logger.error("FATAL: WEBHOOK_BASE_URL environment variable not set.")
    if not GEMINI_API_KEY:
        # Warning instead of error, so the bot can run without AI features.
        logger.warning("GEMINI_API_KEY not set. AI chat features will be disabled.")

    # Construct the full webhook URL.
    WEBHOOK_URL = f"{WEBHOOK_BASE_URL}/{BOT_TOKEN}" if BOT_TOKEN and WEBHOOK_BASE_URL else ""

    # 🐸 Project Details
    CONTRACT_ADDRESS = "BJ65ym9UYPkcfLSUuE9j4uXYuiG6TgA4pFn393Eppump"
    PUMP_FUN_LINK = f"https://pump.fun/{CONTRACT_ADDRESS}"
    WEBSITE_URL = "https://example.com"
    TELEGRAM_URL = "https://t.me/yourchannel"
    TWITTER_URL = "https://twitter.com/yourprofile"


# ==========================
# 🧠 AI INITIALIZATION
# ==========================
ai_model = None
if Config.GEMINI_API_KEY:
    try:
        genai.configure(api_key=Config.GEMINI_API_KEY)
        # Initialize the Gemini Pro model for conversation.
        ai_model = genai.GenerativeModel('gemini-pro')
        logger.info("✅ Gemini AI model initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Gemini AI model: {e}")
else:
    logger.info("ℹ️ No GEMINI_API_KEY found, AI chat is disabled.")


# Initialize bot & app
bot = telebot.TeleBot(Config.BOT_TOKEN, threaded=False)
app = Flask(__name__)


# ==========================
# ⌨️ INTERACTIVE KEYBOARDS
# ==========================
def main_menu_keyboard():
    """Creates an inline keyboard with the main menu options."""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🚀 About $NPEPE", callback_data="about"),
        InlineKeyboardButton("🔗 Contract Address", callback_data="ca"),
        InlineKeyboardButton("💰 Buy on Pump.fun", url=Config.PUMP_FUN_LINK),
        InlineKeyboardButton("🌐 Website", url=Config.WEBSITE_URL),
        InlineKeyboardButton("✈️ Telegram", url=Config.TELEGRAM_URL),
        InlineKeyboardButton("🐦 Twitter", url=Config.TWITTER_URL)
    )
    return keyboard


# ==========================
# 🤖 BOT COMMAND HANDLERS
# ==========================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Handles /start and /help commands, showing the main menu."""
    welcome_text = (
        "🐸 *Welcome to the NextPepe Bot!* 🔥\n\n"
        "I can help you with project info or we can just chat. "
        "Use the buttons below or ask me anything!"
    )
    bot.reply_to(message, welcome_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")


# ==========================
# CALLBACK QUERY HANDLER
# ==========================
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    """Handles button presses from the inline keyboards."""
    try:
        bot.answer_callback_query(call.id)
        message = call.message
        if call.data == "about":
            about_text = (
                "🚀 *$NPEPE* is the new era of meme power!\n"
                "Born from pure community hype on *Pump.fun*.\n\n"
                "No utility, no roadmaps, just 100% meme energy. 🐸"
            )
            bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id,
                                  text=about_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        elif call.data == "ca":
            ca_text = f"🔗 *Contract Address:*\n`{Config.CONTRACT_ADDRESS}`"
            bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id,
                                  text=ca_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")


# ==========================
# 💬 KEYWORD & AI CHAT REPLIES
# ==========================
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_all_text_messages(message):
    """
    Handles any text message. First checks for specific keywords,
    then falls back to the Gemini AI for a conversational reply.
    """
    text = message.text.lower()
    chat_id = message.chat.id

    try:
        # --- Keyword-based replies ---
        if "ca" in text or "contract" in text or "address" in text:
            reply_text = f"Here is the contract address, fren:\n\n`{Config.CONTRACT_ADDRESS}`"
            bot.send_message(chat_id, reply_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
        elif "buy" in text or "how to buy" in text:
            reply_text = f"💰 You can buy *$NPEPE* on Pump.fun! Click the button below to join the ride to the moon! 🚀"
            bot.send_message(chat_id, reply_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
        elif any(greeting in text for greeting in ["hello", "hi", "hey"]):
            reply_text = "👋 Hey fren! Welcome to the $NPEPE community! How can I help you today?"
            bot.send_message(chat_id, reply_text, reply_markup=main_menu_keyboard())
        elif "pump" in text or "moon" in text or "wen moon" in text:
            reply_text = "🌕🐸 Pepe is always on the way to the moon! Keep the hype alive! 🔥"
            bot.send_message(chat_id, reply_text, reply_markup=main_menu_keyboard())
        elif "thank" in text:
            reply_text = "🐸 You're welcome, fren! Glad I could help."
            bot.send_message(chat_id, reply_text)

        # --- AI Fallback Reply ---
        else:
            if not ai_model:
                reply_text = "I'm not sure what you mean, fren. Try using one of the buttons below to navigate!"
                bot.send_message(chat_id, reply_text, reply_markup=main_menu_keyboard())
                return

            # Let the user know the AI is working on a response.
            thinking_message = bot.send_message(chat_id, "🐸 AI is thinking...")

            # Generate the AI response.
            response = ai_model.generate_content(message.text)
            
            # Edit the "thinking" message with the final AI response for a cleaner chat experience.
            bot.edit_message_text(chat_id=chat_id, message_id=thinking_message.message_id, text=response.text)

    except Exception as e:
        logger.error(f"Error in message handler: {e}")
        # Send a user-friendly error message if AI fails.
        bot.send_message(chat_id, "Sorry, my AI brain is taking a break right now. Please try again in a bit!")


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
    return "🐸 NPEPE Telegram Bot is live and connected to AI!", 200


# ==========================
# 🚀 MAIN ENTRY POINT
# ==========================
if __name__ == "__main__":
    if not Config.BOT_TOKEN or not Config.WEBHOOK_URL:
        logger.error("Bot cannot start. Please set BOT_TOKEN and WEBHOOK_BASE_URL environment variables.")
    else:
        logger.info("Starting bot...")
        bot.remove_webhook()
        success = bot.set_webhook(url=Config.WEBHOOK_URL, timeout=5)
        if success:
            logger.info(f"✅ Webhook set successfully to: {Config.WEBHOOK_URL}")
        else:
            logger.error("❌ Webhook set failed. Check your WEBHOOK_BASE_URL.")
        
        logger.info("🐸 Bot is running on Flask server...")
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)

