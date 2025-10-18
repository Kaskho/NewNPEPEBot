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
app = Flask(__name__)

bot = None
bot_logic = None

# We check for the presence of keys here as a preliminary check.
# The BotLogic class will handle the real-time fetching.
if not os.environ.get("BOT_TOKEN") or not os.environ.get("WEBHOOK_BASE_URL") or not os.environ.get("DATABASE_URL"):
    logger.critical("FATAL: One or more critical environment variables (BOT_TOKEN, WEBHOOK_BASE_URL, DATABASE_URL) appear to be missing.")
else:
    try:
        bot = telebot.TeleBot(Config.BOT_TOKEN(), threaded=False) # Note the ()
        bot_logic = BotLogic(bot)
    except Exception as e:
        logger.critical(f"An error occurred during bot initialization: {e}", exc_info=True)

# ==========================
# 🌐 FLASK WEB ROUTES
# ==========================
@app.route('/<token>', methods=['POST'])
def webhook(token):
    if token == Config.BOT_TOKEN() and bot_logic and request.headers.get('content-type') == 'application/json':
        try:
            bot_logic.check_and_run_schedules()
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
        except Exception as e:
            logger.error(f"An unhandled exception occurred in the webhook: {e}", exc_info=True)
        return "OK", 200
    else:
        abort(403)

@app.route('/health', methods=['GET'])
def health_check():
    logger.info("Health Check ping received. Checking schedules.")
    if bot_logic:
        bot_logic.check_and_run_schedules()
    return "Bot is alive and schedules checked.", 200

@app.route('/', methods=['GET'])
def index():
    return "🐸 NPEPE Telegram Bot is live — webhooks enabled.", 200

# ==========================
# 🚀 MAIN ENTRY POINT
# ==========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    if bot and bot_logic:
        webhook_url = f"{Config.WEBHOOK_BASE_URL()}/{Config.BOT_TOKEN()}"
        logger.info("Starting bot and setting webhook...")
        try:
            bot.remove_webhook()
            time.sleep(0.5)
            success = bot.set_webhook(url=webhook_url)
            if success:
                logger.info(f"✅ Webhook set successfully to the bot's token endpoint.")
            else:
                logger.error("❌ Failed to set webhook.")
        except Exception as e:
            logger.error(f"Error while configuring webhook: {e}", exc_info=True)
        
        serve(app, host="0.0.0.0", port=port)
    else:
        logger.error("Bot not initialized. Running in a degraded server mode.")
        @app.route('/')
        def error_page():
            return "Bot configuration is incomplete. Check environment variables.", 500
        serve(app, host="0.0.0.0", port=port)
