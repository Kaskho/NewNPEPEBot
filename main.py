import os
import logging
from flask import Flask, request, abort
import telebot
from bot_logic import BotLogic, Config

# ==========================
# 🔧 CONFIGURATION & INITIALIZATION
# ==========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if not all([Config.BOT_TOKEN, Config.WEBHOOK_BASE_URL, Config.GROUP_CHAT_ID, Config.GROQ_API_KEY]):
    logger.critical("FATAL: Essential environment variables are missing. The bot cannot start.")
    exit()

# Initialize Flask App and Telebot
app = Flask(__name__)
bot = telebot.TeleBot(Config.BOT_TOKEN, threaded=False)

# Initialize the bot's logic from our separate file
bot_logic = BotLogic(bot)

# ==========================
# 🌐 FLASK WEBHOOK & TRIGGERS
# ==========================

# This is the main webhook endpoint for Telegram updates
@app.route(f'/{Config.BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        abort(403)

# Health check endpoint
@app.route('/', methods=['GET'])
def index():
    return "🐸 NPEPE Telegram Bot is live and ribbiting!", 200

# --- Scheduled Greeting Triggers ---
@app.route(f'/trigger-morning/{Config.TRIGGER_SECRET}', methods=['POST'])
def trigger_morning():
    result, code = bot_logic.send_scheduled_greeting('morning')
    return result, code

@app.route(f'/trigger-noon/{Config.TRIGGER_SECRET}', methods=['POST'])
def trigger_noon():
    result, code = bot_logic.send_scheduled_greeting('noon')
    return result, code

@app.route(f'/trigger-night/{Config.TRIGGER_SECRET}', methods=['POST'])
def trigger_night():
    result, code = bot_logic.send_scheduled_greeting('night')
    return result, code

@app.route(f'/trigger-random/{Config.TRIGGER_SECRET}', methods=['POST'])
def trigger_random():
    result, code = bot_logic.send_scheduled_greeting('random')
    return result, code

@app.route(f'/trigger-wisdom/{Config.TRIGGER_SECRET}', methods=['POST'])
def trigger_wisdom():
    result, code = bot_logic.send_scheduled_wisdom()
    return result, code
    
# --- AI Response Renewal Trigger ---
@app.route(f'/trigger-renew-responses/{Config.TRIGGER_SECRET}', methods=['POST'])
def trigger_renew():
    # This might take a while, so it's good practice to run it in a thread
    # For now, we'll run it directly
    result, code = bot_logic.renew_responses_with_ai()
    return result, code

# ==========================
# 🚀 MAIN ENTRY POINT
# ==========================
if __name__ == "__main__":
    logger.info("Starting bot...")
    bot.remove_webhook()
    success = bot.set_webhook(url=Config.WEBHOOK_URL)
    if success:
        logger.info(f"✅ Webhook set successfully to: {Config.WEBHOOK_URL}")
    else:
        logger.error(f"❌ Webhook set failed. Check your WEBHOOK_BASE_URL.")
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
