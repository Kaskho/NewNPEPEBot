Import os
import logging
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import groq
import random
import time
import json
from datetime import datetime
import httpx # <-- ADD THIS LINE

# ==========================
# 🔧 CONFIGURATION
# ==========================
load_dotenv()  # Load variables from .env file

class Config:
    """Configuration variables for the bot."""
    BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    # For production, set this to your app's public URL
    WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')

# ==========================
# 📝 LOGGING SETUP
# ==========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        # By explicitly creating an httpx.Client, we bypass an issue in some
        # versions of the groq library that incorrectly handle proxy settings.
        http_client = httpx.Client()
        groq_client = groq.Groq(
            api_key=Config.GROQ_API_KEY,
            http_client=http_client
        )
        logger.info("✅ Groq AI client initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Groq AI client: {e}")
else:
    logger.info("ℹ️ No GROQ_API_KEY found, AI chat and AI wisdom are disabled.")

# ==========================
# 💬 DYNAMIC MESSAGE LISTS
# ==========================
class BotPersona:
    """Stores personality-related text to make the bot more lively."""
    GREETINGS = [
        "Hello there! How can I brighten your day?",
        "Greetings! What adventures shall we have today?",
        "Hi! I'm ready to help. What's on your mind?",
    ]
    WAITING_MESSAGES = [
        "Let me ponder that for a moment...",
        "Thinking... please hold the line!",
        "Accessing my digital brain...",
        "One moment, I'm brewing a fresh thought.",
    ]
    AI_ERROR_MESSAGES = [
        "Oops, my circuits got a little tangled. Could you try asking in a different way?",
        "My apologies, I seem to be having a moment of digital slowness. Please try again shortly.",
        "It seems my connection to the great AI mind is a bit fuzzy. Let's try that again.",
    ]

# ==========================
# 🛠️ HELPER FUNCTIONS
# ==========================
def get_time_based_greeting():
    """Returns a greeting based on the current time in Indonesia (WIB - Western Indonesian Time, UTC+7)."""
    # WIB is UTC+7. We get UTC time and add 7 hours.
    hour_wib = (datetime.utcnow().hour + 7) % 24
    if 4 <= hour_wib < 11:
        return "Good morning!"
    elif 11 <= hour_wib < 15:
        return "Good afternoon!"
    elif 15 <= hour_wib < 19:
        return "Good evening!"
    else:
        return "Hope you're having a good night!"

def create_main_menu():
    """Creates the main menu inline keyboard."""
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🤔 Ask AI a Question", callback_data="cb_ask_ai"),
        InlineKeyboardButton("💡 Get AI Wisdom", callback_data="cb_get_wisdom")
    )
    return markup

def get_ai_wisdom(chat_id):
    """Fetches and sends a piece of AI wisdom to a given chat."""
    if not groq_client:
        bot.send_message(chat_id, "I'm sorry, my AI features are currently offline.")
        return

    wait_msg = bot.send_message(chat_id, random.choice(BotPersona.WAITING_MESSAGES))
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a wise and slightly quirky philosopher. Provide a short, insightful, and memorable piece of wisdom or a thought-provoking quote. Make it unique. Keep it to one or two sentences."},
                {"role": "user", "content": "Share some wisdom."},
            ],
            model="llama3-8b-8192",
        )
        wisdom = chat_completion.choices[0].message.content
        bot.edit_message_text(f"💡 **AI Wisdom:**\n\n_{wisdom}_", chat_id, wait_msg.message_id, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error fetching AI wisdom: {e}")
        bot.edit_message_text(random.choice(BotPersona.AI_ERROR_MESSAGES), chat_id, wait_msg.message_id)

# ==========================
# 🤖 TELEGRAM HANDLERS
# ==========================
@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    """Handles the /start and /hello commands."""
    greeting = get_time_based_greeting()
    welcome_text = (
        f"{greeting} {random.choice(BotPersona.GREETINGS)}\n\n"
        "I'm a bot with a bit of personality, powered by Groq AI. "
        "You can chat with me directly, or use the buttons below."
    )
    bot.reply_to(message, welcome_text, reply_markup=create_main_menu())

@bot.message_handler(commands=['wisdom'])
def send_wisdom_command(message):
    """Handles the /wisdom command directly."""
    get_ai_wisdom(message.chat.id)

@bot.callback_query_handler(func=lambda call: True)
def callback_query_handler(call):
    """Handles all inline button presses."""
    if call.data == "cb_get_wisdom":
        bot.answer_callback_query(call.id, "Summoning some wisdom...")
        get_ai_wisdom(call.message.chat.id)
    elif call.data == "cb_ask_ai":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Of course! What would you like to ask me? Just type your question.")

@bot.message_handler(func=lambda message: True)
def handle_chat(message):
    """Handles general text messages for AI interaction."""
    if not groq_client:
        bot.reply_to(message, "My AI brain isn't connected right now, so I can't chat. Sorry!")
        return

    wait_msg = bot.reply_to(message, random.choice(BotPersona.WAITING_MESSAGES))
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful, friendly, and slightly witty conversational AI assistant. Use contractions to sound more human."},
                {"role": "user", "content": message.text},
            ],
            model="llama3-8b-8192",
        )
        response = chat_completion.choices[0].message.content
        bot.edit_message_text(response, message.chat.id, wait_msg.message_id)
    except Exception as e:
        logger.error(f"Error in AI chat handler: {e}")
        bot.edit_message_text(random.choice(BotPersona.AI_ERROR_MESSAGES), message.chat.id, wait_msg.message_id)

# ==========================
# 🌐 FLASK WEBHOOK ROUTES
# ==========================
@app.route('/' + Config.BOT_TOKEN, methods=['POST'])
def process_webhook():
    """Process incoming updates from Telegram."""
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def set_webhook():
    """Sets the webhook for the bot (for production)."""
    if Config.WEBHOOK_URL:
        bot.remove_webhook()
        time.sleep(0.1)
        bot.set_webhook(url=Config.WEBHOOK_URL + Config.BOT_TOKEN)
        logger.info(f"Webhook set to {Config.WEBHOOK_URL}")
        return "Webhook set!", 200
    return "Webhook URL not configured.", 404

# ==========================
# 🚦 MAIN EXECUTION
# ==========================
if __name__ == "__main__":
    if Config.WEBHOOK_URL:
        # Production mode: Use webhook
        logger.info(f"Starting bot in webhook mode.")
        port = int(os.environ.get('PORT', 5000))
        app.run(host="0.0.0.0", port=port)
    else:
        # Development mode: Use polling
        logger.info("No WEBHOOK_URL found. Starting bot in polling mode.")
        bot.remove_webhook()
        bot.polling(none_stop=True)
