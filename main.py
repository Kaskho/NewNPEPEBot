import os
import logging
import time
from flask import Flask, request, abort
import telebot
from waitress import serve
from config import Config
from bot_logic import BotLogic

# === BLOK DIAGNOSTIK BARU ===
# Kode ini akan berjalan pertama kali untuk memeriksa semua variabel lingkungan.
print("="*40)
print("MEMULAI PEMERIKSAAN PAKSA VARIABEL LINGKUNGAN...")
print("="*40)

required_vars = [
    "BOT_TOKEN",
    "WEBHOOK_BASE_URL",
    "DATABASE_URL",
    "GROQ_API_KEY",
    "GROUP_CHAT_ID",
    "GROUP_OWNER_ID"
]

missing_vars = []
for var in required_vars:
    value = os.environ.get(var)
    if not value:
        print(f"HASIL: Variabel '{var}' -> TIDAK DITEMUKAN!")
        missing_vars.append(var)
    else:
        print(f"HASIL: Variabel '{var}' -> Ditemukan.")

if missing_vars:
    print("="*40)
    print(f"FATAL ERROR: Variabel lingkungan berikut hilang: {', '.join(missing_vars)}")
    print("Bot tidak bisa dimulai. Silakan periksa tab 'Environment' di dasbor Render Anda.")
    print("="*40)
    # Sengaja menghentikan program dengan error yang jelas
    raise ValueError(f"Variabel lingkungan penting hilang: {', '.join(missing_vars)}")

print("="*40)
print("PEMERIKSAAN SELESAI: Semua variabel lingkungan penting ditemukan.")
print("="*40)
# === AKHIR BLOK DIAGNOSTIK ===


# ==========================
#  🔧  KONFIGURASI & INISIALISASI
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
    bot = telebot.TeleBot(Config.BOT_TOKEN(), threaded=False)
    bot_logic = BotLogic(bot)
except Exception as e:
    logger.critical(f"Terjadi error saat inisialisasi bot: {e}", exc_info=True)
    raise e

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
    if bot_logic:
        bot_logic.check_and_run_schedules()
    # Mengembalikan respons kosong dengan status 204 (No Content)
    return ('', 204)

@app.route('/', methods=['GET'])
def index():
    return "🐸 Bot Telegram NPEPE hidup — webhook diaktifkan.", 200

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
                logger.info("✅ Webhook berhasil diatur.")
            else:
                logger.error("❌ Gagal mengatur webhook.")
        except Exception as e:
            logger.error(f"Error saat mengkonfigurasi webhook: {e}", exc_info=True)
        
        serve(app, host="0.0.0.0", port=port)
    else:
        logger.error("Bot tidak diinisialisasi. Berjalan dalam mode server terdegradasi.")
        serve(app, host="0.0.0.0", port=port)
