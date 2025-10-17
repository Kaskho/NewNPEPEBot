import os
import logging
import time
from flask import Flask, request, abort
import telebot
from bot_logic import BotLogic, Config
from waitress import serve

# ==========================
# 🔧 CONFIGURATION & INITIALIZATION
# ==========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask App and Telebot
app = Flask(__name__)
bot = None
bot_logic = None

try:
    if all([Config.BOT_TOKEN, Config.WEBHOOK_BASE_URL]):
        bot = telebot.TeleBot(Config.BOT_TOKEN, threaded=False)
        bot_logic = BotLogic(bot)
    else:
        logger.critical("FATAL: BOT_TOKEN and WEBHOOK_BASE_URL must be set.")
except Exception as e:
    logger.critical(f"An error occurred during bot initialization: {e}")

# ==========================
# 🌐 FLASK WEB ROUTES
# ==========================

# This endpoint receives updates from Telegram
@app.route(f'/{Config.BOT_TOKEN}', methods=['POST'])
def webhook():
    if bot_logic and request.headers.get('content-type') == 'application/json':
        # On every real message, check the schedule first
        bot_logic.check_and_run_schedules()
        
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        abort(403)

# --- THIS IS THE KEEP-ALIVE ENDPOINT ---
# A simple URL that a free ping service will visit.
@app.route('/health', methods=['GET'])
def health_check():
    """
    This endpoint is pinged by an external service every ~14 minutes.
    1. It keeps the Render free tier service from sleeping.
    2. It triggers our scheduler during quiet periods.
    """
    logger.info("Health check ping received. Checking schedules.")
    if bot_logic:
        # Use this opportunity to check the schedule
        bot_logic.check_and_run_schedules()
    return "Bot is alive and schedules checked.", 200

# Main index page
@app.route('/', methods=['GET'])
def index():
    return "🐸 NPEPE Telegram Bot is live and self-scheduling!", 200

# ==========================
# 🚀 MAIN ENTRY POINT
# ==========================
if __name__ == "__main__":
    if bot and bot_logic:
        logger.info("Starting bot and setting webhook...")
        bot.remove_webhook()
        time.sleep(0.5)
        success = bot.set_webhook(url=Config.WEBHOOK_URL)
        if success:
            logger.info(f"✅ Webhook set successfully to: {Config.WEBHOOK_URL}")
        else:
            logger.error(f"❌ Webhook set failed. Check your WEBHOOK_BASE_URL.")
        
        port = int(os.environ.get("PORT", 10000))
        serve(app, host="0.0.0.0", port=port)
    else:
        logger.error("Bot not initialized. Server will run in a degraded state.")
        # Fallback server to prevent Render from crashing on boot
        @app.route('/')
        def error_page():
            return "Bot configuration is incomplete. Please check environment variables.", 500
        serve(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
