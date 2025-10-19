import os
import logging
import time
from flask import Flask, request, abort
import telebot
from bot_logic import BotLogic, Config
from waitress import serve

# ==========================
#  🔧  KONFIGURASI & INISIALISASI
# ==========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- BLOK DIAGNOSTIK SEMENTARA ---
# Kode ini akan berjalan saat bot dimulai untuk memeriksa env var.
logger.info("="*40)
logger.info("MEMERIKSA SEMUA ENVIRONMENT VARIABLES YANG TERLIHAT")
db_url_from_os = os.environ.get("DATABASE_URL")
bot_token_from_os = os.environ.get("BOT_TOKEN")
webhook_from_os = os.environ.get("WEBHOOK_BASE_URL")

logger.info(f"NILAI 'DATABASE_URL' DARI os.environ: {db_url_from_os}")
logger.info(f"NILAI 'BOT_TOKEN' DARI os.environ: {'Ditemukan' if bot_token_from_os else 'Tidak Ditemukan'}")
logger.info(f"NILAI 'WEBHOOK_BASE_URL' DARI os.environ: {webhook_from_os}")
logger.info("="*40)
# --- AKHIR BLOK DIAGNOSTIK ---

# Inisialisasi aplikasi Flask
app = Flask(__name__)
bot = None
bot_logic = None

if not all([bot_token_from_os, webhook_from_os, db_url_from_os]):
    logger.critical("FATAL: Satu atau lebih variabel lingkungan penting (BOT_TOKEN, WEBHOOK_BASE_URL, DATABASE_URL) tidak ditemukan.")
else:
    try:
        bot = telebot.TeleBot(Config.BOT_TOKEN(), threaded=False)
        bot_logic = BotLogic(bot)
    except Exception as e:
        logger.critical(f"Terjadi error saat inisialisasi bot: {e}", exc_info=True)

# ==========================
#  🌐  RUTE WEB FLASK
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
            logger.error(f"Terjadi pengecualian yang tidak ditangani di webhook: {e}", exc_info=True)
        return "OK", 200
    else:
        abort(403)

@app.route('/health', methods=['GET'])
def health_check():
    logger.info("Ping 'Health Check' diterima. Memeriksa jadwal.")
    if bot_logic:
        bot_logic.check_and_run_schedules()
    return "Bot hidup dan jadwal telah diperiksa.", 200

@app.route('/', methods=['GET'])
def index():
    return " 🐸  Bot Telegram NPEPE hidup — webhook diaktifkan.", 200

# ==========================
#  🚀  TITIK MASUK UTAMA
# ==========================
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
                logger.info("✅ Webhook berhasil diatur ke endpoint token bot.")
            else:
                logger.error("❌ Gagal mengatur webhook.")
        except Exception as e:
            logger.error(f"Error saat mengkonfigurasi webhook: {e}", exc_info=True)
        serve(app, host="0.0.0.0", port=port)
    else:
        logger.error("Bot tidak diinisialisasi. Berjalan dalam mode server terdegradasi.")
        @app.route('/')
        def error_page():
            return "Konfigurasi bot tidak lengkap. Periksa variabel lingkungan.", 500
        serve(app, host="0.0.0.0", port=port)
