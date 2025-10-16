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

# Initialize Flask app
app = Flask(__name__)

# Initialize Telegram Bot
if not Config.BOT_TOKEN:
    logger.fatal("FATAL: BOT_TOKEN environment variable is not set. The bot cannot start.")
    exit()

bot = telebot.TeleBot(Config.BOT_TOKEN, threaded=False)

# Initialize Bot Logic Handler
bot_logic = BotLogic(bot)

# ==========================
# 🌐 FLASK WEBHOOK & ROUTES
# ==========================
@app.route(f'/{Config.BOT_TOKEN}', methods=['POST'])
def webhook():
    """Processes incoming updates from Telegram."""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        logger.warning("Webhook received a request with an invalid content-type.")
        abort(403)

@app.route('/', methods=['GET'])
def index():
    """A simple endpoint to confirm the bot is live."""
    return "🐸 NPEPE Telegram Bot is live and hopping!", 200

# ==========================
# ⏰ SCHEDULED TASK TRIGGERS
# ==========================
# These endpoints are designed to be called by a scheduling service (like cron-job.org).
# The TRIGGER_SECRET adds a layer of security to prevent unauthorized calls.

@app.route(f'/trigger-wisdom/{Config.TRIGGER_SECRET}', methods=['POST'])
def trigger_wisdom():
    """Triggers the bot to send a wisdom message."""
    return bot_logic.send_scheduled_wisdom()

@app.route(f'/trigger-morning/{Config.TRIGGER_SECRET}', methods=['POST'])
def trigger_morning():
    """Triggers the bot to send a morning greeting."""
    return bot_logic.send_scheduled_greeting('morning')

@app.route(f'/trigger-noon/{Config.TRIGGER_SECRET}', methods=['POST'])
def trigger_noon():
    """Triggers the bot to send a noon greeting."""
    return bot_logic.send_scheduled_greeting('noon')

@app.route(f'/trigger-night/{Config.TRIGGER_SECRET}', methods=['POST'])
def trigger_night():
    """Triggers the bot to send a night greeting."""
    return bot_logic.send_scheduled_greeting('night')

@app.route(f'/trigger-random-hype/{Config.TRIGGER_SECRET}', methods=['POST'])
def trigger_random_hype():
    """Triggers the bot to send a random hype message."""
    return bot_logic.send_scheduled_greeting('random')

@app.route(f'/trigger-renew-responses/{Config.TRIGGER_SECRET}', methods=['POST'])
def trigger_renew_responses():
    """Triggers the AI to rewrite the bot's response lists."""
    logger.info("Received request to renew bot responses via trigger URL.")
    return bot_logic.renew_responses_with_ai()


# ==========================
# 🚀 MAIN ENTRY POINT
# ==========================
if __name__ == "__main__":
    if not Config.WEBHOOK_BASE_URL:
        logger.error("Bot cannot start in webhook mode. Please set the WEBHOOK_BASE_URL environment variable.")
    else:
        logger.info("Starting bot in webhook mode...")
        bot.remove_webhook()
        # Set the webhook
        success = bot.set_webhook(url=Config.WEBHOOK_URL)
        if success:
            logger.info(f"✅ Webhook set successfully to: {Config.WEBHOOK_URL}")
        else:
            logger.error(f"❌ Webhook set failed. Please check your WEBHOOK_BASE_URL and BOT_TOKEN.")

        # Get port from environment variable or default to 10000
        port = int(os.environ.get("PORT", 10000))
        # Run the Flask app
        app.run(host="0.0.0.0", port=port)
