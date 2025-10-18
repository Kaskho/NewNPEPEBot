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

try:
    if all([Config.BOT_TOKEN, Config.WEBHOOK_BASE_URL]):
        # Use threaded=False for telebot webhook safety in this context
        bot = telebot.TeleBot(Config.BOT_TOKEN, threaded=False)
        bot_logic = BotLogic(bot)
    else:
        logger.critical("FATAL: BOT_TOKEN and WEBHOOK_BASE_URL must be set.")
except Exception as e:
    logger.critical(f"An error occurred during bot initialization: {e}", exc_info=True)

# ==========================
# 🌐 FLASK WEB ROUTES
# ==========================

# This endpoint receives updates from Telegram
@app.route(f'/{Config.BOT_TOKEN}', methods=['POST'])
def webhook():
    # Only accept JSON from Telegram
    if bot_logic and request.headers.get('content-type') == 'application/json':
        try:
            # Always check schedules on every webhook call (this is a cheap check)
            bot_logic.check_and_run_schedules()

            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            # Process updates synchronously to avoid losing them during quick redeploys
            bot.process_new_updates([update])
        except Exception as e:
            logger.error(f"An unhandled exception occurred in the webhook: {e}", exc_info=True)

        # Always return HTTP 200/OK to Telegram to prevent it from re-sending updates
        return "OK", 200
    else:
        abort(403)


# "Keep-Alive" endpoint to prevent the bot from sleeping
@app.route('/health', methods=['GET'])
def health_check():
    logger.info("Health Check ping received. Checking schedules.")
    if bot_logic:
        bot_logic.check_and_run_schedules()
    return "Bot is alive and schedules checked.", 200


# Main index page
@app.route('/', methods=['GET'])
def index():
    return "🐸 NPEPE Telegram Bot is live — webhooks enabled.", 200


# ==========================
# 🚀 MAIN ENTRY POINT
# ==========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    if bot and bot_logic:
        logger.info("Starting bot and setting webhook...")
        try:
            # Remove any existing webhook and set a fresh one
            bot.remove_webhook()
            time.sleep(0.5)
            success = bot.set_webhook(url=Config.WEBHOOK_URL)
            if success:
                logger.info(f"✅ Webhook set successfully to: {Config.WEBHOOK_URL}")
            else:
                logger.error("❌ Failed to set webhook. Check WEBHOOK_BASE_URL and BOT_TOKEN.")
        except Exception as e:
            logger.error(f"Error while configuring webhook: {e}", exc_info=True)

        # Serve the Flask app
        serve(app, host="0.0.0.0", port=port)
    else:
        logger.error("Bot not initialized. Running in a degraded server mode.")
        @app.route('/')
        def error_page():
            return "Bot configuration is incomplete. Check environment variables.", 500
        serve(app, host="0.0.0.0", port=port)
