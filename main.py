import os
import logging
import time
from flask import Flask, request, abort
import telebot
from bot_logic import BotLogic, Config
from waitress import serve

# ==========================
# 🔧 KONFIGURASI & INISIALISASI
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
        bot = telebot.TeleBot(Config.BOT_TOKEN, threaded=False)
        bot_logic = BotLogic(bot)
    else:
        logger.critical("FATAL: BOT_TOKEN dan WEBHOOK_BASE_URL harus diatur.")
except Exception as e:
    logger.critical(f"Terjadi error saat inisialisasi bot: {e}")

# ==========================
# 🌐 RUTE WEB FLASK
# ==========================

# Endpoint ini menerima pembaruan dari Telegram
@app.route(f'/{Config.BOT_TOKEN}', methods=['POST'])
def webhook():
    if bot_logic and request.headers.get('content-type') == 'application/json':
        try:
            # Pada setiap pesan, periksa jadwal terlebih dahulu
            bot_logic.check_and_run_schedules()
            
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
        except Exception as e:
            # Jaring pengaman untuk menangkap crash yang tidak terduga
            logger.error(f"Terjadi pengecualian yang tidak ditangani di webhook: {e}", exc_info=True)
        
        # Selalu kembalikan "OK" ke Telegram
        return "OK", 200
    else:
        abort(403)

# Endpoint "Keep-Alive" untuk mencegah bot tertidur
@app.route('/health', methods=['GET'])
def health_check():
    logger.info("Ping 'Health Check' diterima. Memeriksa jadwal.")
    if bot_logic:
        bot_logic.check_and_run_schedules()
    return "Bot hidup dan jadwal telah diperiksa.", 200

# Halaman indeks utama
@app.route('/', methods=['GET'])
def index():
    return "🐸 Bot Telegram NPEPE hidup dan menjadwalkan dirinya sendiri!", 200

# ==========================
# 🚀 TITIK MASUK UTAMA
# ==========================
if __name__ == "__main__":
    if bot and bot_logic:
        logger.info("Memulai bot dan mengatur webhook...")
        bot.remove_webhook()
        time.sleep(0.5)
        success = bot.set_webhook(url=Config.WEBHOOK_URL)
        if success:
            logger.info(f"✅ Webhook berhasil diatur ke: {Config.WEBHOOK_URL}")
        else:
            logger.error(f"❌ Pengaturan webhook gagal. Periksa WEBHOOK_BASE_URL Anda.")
        
        port = int(os.environ.get("PORT", 10000))
        serve(app, host="0.0.0.0", port=port)
    else:
        logger.error("Bot tidak diinisialisasi. Server akan berjalan dalam mode terdegradasi.")
        @app.route('/')
        def error_page():
            return "Konfigurasi bot tidak lengkap. Silakan periksa variabel lingkungan.", 500
        serve(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
