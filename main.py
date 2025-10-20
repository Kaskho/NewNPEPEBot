import os
import logging
import time
from flask import Flask, request, abort
import telebot
from bot_logic import BotLogic
from config import Config
from waitress import serve

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot = None
bot_logic = None

# Inisialisasi Bot
try:
    if all([Config.BOT_TOKEN(), Config.WEBHOOK_BASE_URL(), Config.DATABASE_URL()]):
        bot = telebot.TeleBot(Config.BOT_TOKEN(), threaded=False)
        bot_logic = BotLogic(bot)
    else:
        logger.critical("FATAL: Variabel lingkungan penting tidak ditemukan.")
except Exception as e:
    logger.critical(f"Terjadi error saat inisialisasi bot: {e}", exc_info=True)


# Webhook untuk Telegram
@app.route(f'/{Config.BOT_TOKEN()}', methods=['POST'])
def webhook():
    if bot_logic and request.headers.get('content-type') == 'application/json':
        try:
            bot_logic.check_and_run_schedules()
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
        except Exception as e:
            logger.error(f"Pengecualian di webhook: {e}", exc_info=True)
        return "OK", 200
    else:
        abort(403)

# Endpoint Health Check yang baru dan sangat kecil
@app.route('/health', methods=['GET'])
def health_check():
    logger.info("Ping 'Health Check' diterima.")
    if bot_logic:
        bot_logic.check_and_run_schedules()
    # Mengembalikan respons "204 No Content", yang benar-benar kosong.
    return "", 204

# Halaman utama
@app.route('/')
def index():
    return "🐸 Bot Telegram NPEPE hidup — webhook diaktifkan.", 200

# Fungsi untuk menjalankan server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    if bot and bot_logic:
        webhook_url = f"{Config.WEBHOOK_BASE_URL()}/{Config.BOT_TOKEN()}"
        logger.info("Memulai bot dan mengatur webhook...")
        try:
            bot.remove_webhook()
            time.sleep(0.5)
            success = bot.set_webhook(url=webhook_url)
            if success:
                logger.info("✅ Webhook berhasil diatur.")
            else:
                logger.error("❌ Gagal mengatur webhook.")
        except Exception as e:
            logger.error(f"Error saat mengkonfigurasi webhook: {e}", exc_info=True)
        
        serve(app, host="0.0.0.0", port=port)
    else:
        logger.error("Bot tidak diinisialisasi. Berjalan dalam mode server terdegradasi.")
        serve(app, host="0.0.0.0", port=port)
