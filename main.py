# main.py
import os
import time
import random
import requests
import threading
import datetime
from io import BytesIO

import telebot
from flask import Flask, request

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Official links & image (your provided image)
BUY_LINK = "https://pump.fun/coin/BJ65ym9UYPkcfLSUuE9j4uXYuiG6TgA4pFn393Eppump?s=09"
OFFICIAL_X = "https://x.com/NPEPE_Verse?t=tBiSnw3W5a_lm0AN-jdE6w&s=09"
OFFICIAL_WEBSITE = "https://t.co/4UziPz99j8"
NPEPE_IMAGE_URL = "https://i.ibb.co.com/JwKj10Gw/1760253999798.png"  # your image

# Tenor defaults and container for refreshed GIFs
default_gifs = [
    "https://media.tenor.com/UcCjvPq4RrYAAAAC/pepe-dance.gif",
    "https://media.tenor.com/5cMtt1lB9CkAAAAC/pepe-spin.gif",
    "https://media.tenor.com/E4zKcgJP6nkAAAAd/pepe-happy.gif",
    "https://media.tenor.com/whhPVq8hUUMAAAAC/pepe-smile.gif",
]
pepe_gifs = []

# Active chats to broadcast scheduled posts
active_chats = set()

# Local quote seeds (used as input for AI to expand/remix)
PEPE_QUOTE_SEEDS = [
    "Even frogs dream of the moon.",
    "Chaos is the path to glory.",
    "A frog that hesitates is lost.",
    "Hold tight; the pond has tides.",
    "When the world goes quiet, meme louder.",
    "From the swamp we rise, for the meme we fight.",
    "Every red candle is a lesson, not an end.",
    "There’s no roadmap, only ribbits of destiny.",
    "Meme first. Think later.",
    "If it’s stupid and it works — it’s $NPEPE."
]

# Message pools
MORNING = [
    "🌅 GM fam! Another day, another meme. $NPEPE never sleeps!",
    "☀️ Wake up frogs! Let’s pump some joy today 🐸💚",
    "Rise and shine! The swamp is awake and ready to meme!",
    "Good morning legends 🌞 Remember: 1 Pepe = 1 Pepe.",
    "🪩 Morning vibes! Grab your coffee and open pump.fun 😎",
]
NOON = [
    "🍜 Lunchtime meme fuel activated! Keep the vibes high.",
    "☀️ Midday check-in — the frogs still winning?",
    "🐸 If you’re reading this, you’re early. Stay memed!",
    "🔥 Keep the timeline hot, it’s $NPEPE o’clock!",
    "💪 Degen energy check! The swamp is never quiet!",
]
NIGHT = [
    "🌙 Night vibes in the swamp — dream green, fren.",
    "💤 Rest well, but never stop memeing 🐸",
    "Good night, frogs. May your dreams be full of 100x charts 🌕",
    "✨ NPEPE sleeps, but the memes never do.",
    "🕯️ Whisper to the moon: ‘We are inevitable.’ 💚",
]
ENGAGEMENT_LINES = [
    "So, what’s the wildest thing $NPEPE did today? 😂",
    "Drop your favorite Pepe meme below 👇",
    "Frogs of the swamp, unite! 🐸💥",
    "I heard someone said 'sell'… we don’t do that here 😎",
    "What’s your entry price, anon? 👀",
    "Someone say meme war incoming? 🧠",
]

# Free AI endpoint (community GPT-like)
FREE_AI_URL = "https://api.mdcgpt.com/api/gpt"

# ---------------- UTILITIES ----------------
def safe_get(url, timeout=10):
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.content
    except Exception as e:
        print(f"[safe_get] error fetching {url}: {e}")
    return None

def send_npepe_image(chat_id, caption=None):
    """Send the uploaded NPEPE image with caption. Fallback to text if can't fetch image."""
    try:
        data = safe_get(NPEPE_IMAGE_URL)
        if data:
            bio = BytesIO(data)
            bio.name = "npepe.png"
            bot.send_photo(chat_id, bio, caption=caption or "")
            return True
    except Exception as e:
        print(f"[send_npepe_image] error: {e}")
    # fallback to text
    if caption:
        try:
            bot.send_message(chat_id, caption, parse_mode="Markdown")
            return True
        except Exception as e:
            print(f"[send_npepe_image fallback] send text error: {e}")
    return False

def send_random_gif(chat_id):
    try:
        if pepe_gifs:
            url = random.choice(pepe_gifs)
        else:
            url = random.choice(default_gifs)
        bot.send_animation(chat_id, url)
    except Exception as e:
        print(f"[send_random_gif] error: {e}")

def call_free_ai(prompt_text, timeout=8):
    """Call free AI endpoint and return string reply."""
    try:
        payload = {"prompt": prompt_text}
        r = requests.post(FREE_AI_URL, json=payload, timeout=timeout)
        data = r.json()
        # expected shape: {"response": "..."} or other shapes
        if isinstance(data, dict) and "response" in data:
            return data["response"]
        if isinstance(data, list) and data:
            first = data[0]
            for key in ("generated_text", "response", "text"):
                if key in first:
                    return first[key]
        if isinstance(data, str):
            return data
    except Exception as e:
        print(f"[call_free_ai] error: {e}")
    return None

# ---------------- ADMIN CHECKS ----------------
def is_admin_or_creator(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ("creator", "administrator")
    except Exception as e:
        # if we cannot check, safer to not reply
        print(f"[is_admin_or_creator] error: {e}")
        return False

def should_reply(message):
    if getattr(message.from_user, "is_bot", False):
        return False
    if message.chat.type in ("group", "supergroup"):
        if is_admin_or_creator(message.chat.id, message.from_user.id):
            return False
    return True

# ---------------- HANDLERS & COMMANDS ----------------
@bot.message_handler(commands=["buy"])
def cmd_buy(m):
    bot.reply_to(m, f"💰 Buy $NPEPE here:\n{BUY_LINK}")

@bot.message_handler(commands=["x", "twitter"])
def cmd_x(m):
    bot.reply_to(m, f"🐦 Official X: {OFFICIAL_X}")

@bot.message_handler(commands=["wisdom"])
def cmd_wisdom(m):
    # Manual trigger: generate dynamic AI wisdom immediately
    quote_seed = random.choice(PEPE_QUOTE_SEEDS)
    style = random.choice(["short_funny", "deep_philosophical", "mix"])
    if style == "short_funny":
        prompt = f"Create a short, witty frog-philosopher comment for this quote: '{quote_seed}'"
    elif style == "deep_philosophical":
        prompt = f"Create a short, deep, philosophical frog-style comment for this quote: '{quote_seed}'"
    else:
        prompt = f"Create a short comment mixing humor and depth for this quote: '{quote_seed}'"
    ai_comment = call_free_ai(prompt) or "Pepe is pondering... 🐸"
    caption = f"📜 *Pepe Wisdom*\n\n{quote_seed}\n\n💬 {ai_comment}"
    send_npepe_image(m.chat.id, caption=caption)

@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_members(message):
    try:
        for user in message.new_chat_members:
            name = getattr(user, "first_name", None) or getattr(user, "username", None) or "frog fren"
            text = f"🐸 Welcome {name}! Grab your meme and join the chaos 💚"
            send_npepe_image(message.chat.id, caption=text)
    except Exception as e:
        print(f"[welcome_new_members] error: {e}")

@bot.message_handler(func=lambda msg: True, content_types=['text', 'sticker', 'photo', 'animation', 'document'])
def handle_message(message):
    try:
        if not should_reply(message):
            return

        chat_id = message.chat.id
        active_chats.add(chat_id)

        text = (getattr(message, "text", "") or "").lower().strip()

        # If no text (sticker/photo), small chance to send gif or image reaction
        if not text:
            if random.random() < 0.15:
                if random.random() < 0.6:
                    send_npepe_image(chat_id, caption=None)
                else:
                    send_random_gif(chat_id)
            return

        # Keyword-driven replies
        if "roadmap" in text:
            roadmap = (
                "🐸 *NPEPE ROADMAP*\n\n"
                "1️⃣ PHASE 1 — BIRTH OF THE MEME\nPepe reincarnates as NextPepe — half legend, half glitch.\n\n"
                "2️⃣ PHASE 2 — THE GREAT FROG AWAKENING\n#NPEPEARMY rises; meme raids flood timelines.\n\n"
                "3️⃣ PHASE 3 — EXPANSION OF THE NPEPEVERSE\nLore drops, fake partnerships, real hype.\n\n"
                "4️⃣ PHASE 4 — MEMETIC ASCENSION\nMerch, art, community hype; 1 Pepe = 1 Pepe."
            )
            bot.reply_to(message, roadmap, parse_mode="Markdown")
            if random.random() < 0.6:
                send_npepe_image(chat_id)
            return

        if any(k in text for k in ("buy", "where to buy", "how to buy")):
            bot.reply_to(message, f"💰 Buy $NPEPE here:\n{BUY_LINK}")
            if random.random() < 0.6:
                send_npepe_image(chat_id)
            return

        if any(k in text for k in ("website", "link", "official", "x.com", "twitter")):
            bot.reply_to(message, f"🌍 Official Links:\nX: {OFFICIAL_X}\nWebsite: {OFFICIAL_WEBSITE}\nBuy: {BUY_LINK}")
            return

        if any(k in text for k in ("gm", "good morning")):
            greet = random.choice(MORNING)
            send_npepe_image(chat_id, caption=greet)
            if random.random() < 0.7:
                send_random_gif(chat_id)
            return

        if any(k in text for k in ("gn", "good night")):
            greet = random.choice(NIGHT)
            send_npepe_image(chat_id, caption=greet)
            return

        # Fallback: ask free AI for reply
        prompt = f"Answer briefly as NPEPE Folk AI — chaotic, funny, degen-style frog. User said: {text}"
        ai_resp = call_free_ai(prompt)
        if not ai_resp:
            ai_resp = random.choice([
                "Heh, that’s a deep swamp thought 🐸",
                "Meme or be memed.",
                "Pepe approves that message.",
                "WAGMI fren 💚",
                "That’s spicy 🧂"
            ])
        bot.reply_to(message, ai_resp)
        # Sometimes attach image or gif after reply
        if random.random() < 0.35:
            if random.random() < 0.6:
                send_npepe_image(chat_id, caption=None)
            else:
                send_random_gif(chat_id)

    except Exception as e:
        print(f"[handle_message] error: {e}")

# ---------------- BACKGROUND LOOPS ----------------
def refresh_gifs_loop():
    global pepe_gifs
    while True:
        try:
            r = requests.get("https://tenor.googleapis.com/v2/search",
                             params={"q": "pepe", "key": "LIVDSRZULELA", "limit": 10}, timeout=15)
            data = r.json()
            results = data.get("results") or []
            gifs = []
            for res in results:
                media = res.get("media_formats") or {}
                gif_url = media.get("gif", {}).get("url")
                if gif_url:
                    gifs.append(gif_url)
            pepe_gifs = gifs if gifs else default_gifs
            print(f"[refresh_gifs_loop] loaded {len(pepe_gifs)} gifs")
        except Exception as e:
            print(f"[refresh_gifs_loop] error: {e}")
            pepe_gifs = default_gifs
        time.sleep(7 * 24 * 3600)  # weekly

def scheduled_messages_loop():
    """
    Scheduled:
      - Morning 06:00 UTC (image + greeting)
      - Wisdom 06:00 UTC (AI-generated quote of the day)  <--- your requested time
      - Noon 12:00 UTC
      - Night 22:00 UTC
    NOTE: Wisdom scheduled at 06:00 UTC per earlier requests (if you want 09:00 change hour check)
    This loop ensures each event triggers once per day using date flags.
    """
    flags = {"morning": None, "wisdom": None, "noon": None, "night": None}
    while True:
        now = datetime.datetime.utcnow()
        hour = now.hour
        today = now.date()

        try:
            # Morning 06:00
            if hour == 6 and flags["morning"] != today:
                for chat in list(active_chats):
                    try:
                        text = random.choice(MORNING)
                        send_npepe_image(chat, caption=text)
                        if random.random() < 0.6:
                            send_random_gif(chat)
                    except Exception as e:
                        print(f"[morning send] {e}")
                flags["morning"] = today

            # Wisdom 06:00 (AI-generated dynamic quote)
            if hour == 6 and flags["wisdom"] != today:
                base = random.choice(PEPE_QUOTE_SEEDS)
                style = random.choice(["short_funny", "deep_philosophical", "mix"])
                if style == "short_funny":
                    prompt = f"Create a short funny frog-philosopher wisdom line based on: '{base}'"
                elif style == "deep_philosophical":
                    prompt = f"Create a short deep philosophical frog wisdom line based on: '{base}'"
                else:
                    prompt = f"Create a short line that mixes humor and depth based on: '{base}'"
                ai_comment = call_free_ai(prompt) or "Pepe thinks... 🐸"
                full = f"📜 *Pepe Wisdom of the Day*\n\n{base}\n\n💬 {ai_comment}"
                for chat in list(active_chats):
                    try:
                        send_npepe_image(chat, caption=full)
                        if random.random() < 0.8:
                            send_random_gif(chat)
                    except Exception as e:
                        print(f"[wisdom send] {e}")
                flags["wisdom"] = today

            # Noon 12:00
            if hour == 12 and flags["noon"] != today:
                for chat in list(active_chats):
                    try:
                        text = random.choice(NOON)
                        send_npepe_image(chat, caption=text)
                        if random.random() < 0.6:
                            send_random_gif(chat)
                    except Exception as e:
                        print(f"[noon send] {e}")
                flags["noon"] = today

            # Night 22:00
            if hour == 22 and flags["night"] != today:
                for chat in list(active_chats):
                    try:
                        text = random.choice(NIGHT)
                        send_npepe_image(chat, caption=text)
                    except Exception as e:
                        print(f"[night send] {e}")
                flags["night"] = today

        except Exception as e:
            print(f"[scheduled_messages_loop] error: {e}")

        time.sleep(30)  # check frequently to hit the exact hour

# ---------------- FLASK WEBHOOK ROUTES ----------------
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook_receiver():
    try:
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    except Exception as e:
        print(f"[webhook_receiver] error: {e}")
    return "OK", 200

@app.route("/", methods=["GET"])
def health():
    return "NewNPEPEBot v3 — webhook alive", 200

# ---------------- STARTUP ----------------
if __name__ == "__main__":
    # Start background threads
    threading.Thread(target=refresh_gifs_loop, daemon=True).start()
    threading.Thread(target=scheduled_messages_loop, daemon=True).start()

    # Determine webhook URL
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL") or os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    if WEBHOOK_URL:
        # if just hostname provided by Render, add scheme and token path
        full = WEBHOOK_URL
        if not full.startswith("http"):
            full = f"https://{full}/{BOT_TOKEN}"
        else:
            if not full.endswith(f"/{BOT_TOKEN}"):
                full = full.rstrip("/") + f"/{BOT_TOKEN}"
        try:
            bot.remove_webhook()
            bot.set_webhook(url=full)
            print(f"[startup] webhook set to: {full}")
        except Exception as e:
            print(f"[startup] failed to set webhook: {e}")
    else:
        print("[startup] No WEBHOOK_URL or RENDER_EXTERNAL_HOSTNAME found — webhook not set automatically.")
        print("Set env WEBHOOK_URL to 'https://yourdomain.com' or deploy on Render to get automatic hostname.")

    # Run Flask
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
