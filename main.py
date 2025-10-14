import telebot
from telebot import types
from flask import Flask, request
import requests
import random
import datetime
import threading
import time

# --- CONFIG ---
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- IMAGE & LINKS ---
NPEPE_IMAGE = "https://i.ibb.co.com/JwKj10Gw/1760253999798.png"
CONTRACT_ADDRESS = "BJ65ym9UYPkcfLSUuE9j4uXYuiG6TgA4pFn393Eppump"
BUY_LINK = "https://pump.fun/coin/BJ65ym9UYPkcfLSUuE9j4uXYuiG6TgA4pFn393Eppump?s=09"
X_LINK = "https://x.com/NPEPE_Verse?t=tBiSnw3W5a_lm0AN-jdE6w&s=09"

# --- OWNER & GROUP LIST ---
OWNER_ID = [123456789]  # replace with your Telegram ID
GROUP_IDS = [-1001234567890, -1009876543210]  # add all group IDs here

# --- FREE AI REPLY API ---
def get_free_ai_response(prompt):
    try:
        url = "https://api.monkedev.com/fun/chat"
        res = requests.get(url, params={"msg": prompt})
        return res.json().get("response", "🐸 Pepe got distracted by the moon.")
    except:
        return "AI Pepe is croaking... 🐸💭"

# --- DAILY QUOTE (AI + fallback) ---
def get_daily_quote():
    try:
        res = requests.get("https://api.quotable.io/random").json()
        return f"“{res['content']}” — {res['author']}"
    except:
        return random.choice([
            "“Stay green, stay based.” — Pepe 🐸",
            "“Even frogs dream of moonshots.”",
            "“1 Pepe = 1 Pepe.”",
            "“Don’t chase, just vibe.”",
            "“Hold tight, destiny ribbits.”"
        ])

# --- TIME GREETINGS ---
def get_time_greeting():
    hour = datetime.datetime.utcnow().hour
    if 5 <= hour < 12:
        return random.choice(["☀️ Good morning, Pepe army!", "🌅 Rise and shine, frogs!", "🐸 Morning vibe from NPEPE!"])
    elif 12 <= hour < 18:
        return random.choice(["🌞 Good afternoon, frogs!", "🐸 Keep raiding, stay memeing!", "💸 Midday meme power!"])
    else:
        return random.choice(["🌙 Good night, frogs!", "😴 Dream of pumps.", "🌌 Night vibe — hodl tight!"])

# --- AUTO DAILY QUOTE POSTER ---
def daily_quote_poster():
    while True:
        now = datetime.datetime.utcnow()
        if now.hour == 6 and now.minute == 0:
            quote = get_daily_quote()
            greeting = get_time_greeting()
            msg = f"{greeting}\n\n📜 *Pepe Wisdom of the Day:*\n{quote}"
            for gid in GROUP_IDS:
                try:
                    bot.send_photo(gid, NPEPE_IMAGE, caption=msg, parse_mode="Markdown")
                except Exception as e:
                    print(f"❌ Failed to send quote to {gid}: {e}")
            time.sleep(60)  # wait 1 min to avoid re-sending
        time.sleep(30)  # check every 30 sec

# Start background thread for quotes
threading.Thread(target=daily_quote_poster, daemon=True).start()

# --- TELEGRAM COMMANDS ---
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    msg = (
        f"🐸 *Welcome to NPEPEVERSE!*\n\n"
        f"From the swamp to the chain — NextPepe runs the game.\n\n"
        f"💬 Chat with Pepe’s AI brain.\n"
        f"💰 [Buy Here]({BUY_LINK})\n"
        f"🌐 [Official X]({X_LINK})\n"
        f"📜 Contract: `{CONTRACT_ADDRESS}`"
    )
    bot.send_photo(message.chat.id, NPEPE_IMAGE, caption=msg, parse_mode="Markdown")

# --- MESSAGE HANDLER ---
@bot.message_handler(func=lambda msg: True)
def chat_reply(message):
    if message.from_user.id in OWNER_ID or message.from_user.is_bot:
        return

    text = message.text.lower()

    if "contract" in text or "ca" in text:
        bot.reply_to(message, f"🐸 Contract Address:\n`{CONTRACT_ADDRESS}`", parse_mode="Markdown")
    elif "buy" in text:
        bot.reply_to(message, f"💰 You can buy here:\n{BUY_LINK}")
    elif "x" in text or "twitter" in text:
        bot.reply_to(message, f"🌐 Official X:\n{X_LINK}")
    elif "roadmap" in text:
        roadmap = (
            "🚀 *NPEPE ROADMAP*\n\n"
            "1️⃣ Birth of the Meme — $NPEPE rises\n"
            "2️⃣ Frog Awakening — Meme raids & Pepe army\n"
            "3️⃣ Expansion — NPEPEVERSE grows\n"
            "4️⃣ Memetic Ascension — Merch, lore, prophecy\n\n"
            "🐸 'From the swamp to the chain — NextPepe runs the game.'"
        )
        bot.reply_to(message, roadmap, parse_mode="Markdown")
    else:
        ai_reply = get_free_ai_response(message.text)
        if random.random() < 0.25:
            ai_reply += "\n\n" + get_time_greeting()
        bot.reply_to(message, ai_reply)

# --- WEBHOOK SETUP ---
@app.route("/")
def index():
    bot.remove_webhook()
    bot.set_webhook(url=f"https://newnpepebot.onrender.com/{BOT_TOKEN}")
    return "Webhook set successfully!", 200

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.data.decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

# --- RUN APP ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
