import os
import telebot
import requests
import json
import random
import time
import datetime
from flask import Flask
from threading import Thread

# === BOT TOKEN ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(BOT_TOKEN)

# === GLOBALS ===
pepe_gifs = []
active_chats = set()
last_quote_sent = {}  # track daily quotes per group

# === DEFAULT PEPE GIFS ===
default_gifs = [
    "https://media.tenor.com/UcCjvPq4RrYAAAAC/pepe-dance.gif",
    "https://media.tenor.com/5cMtt1lB9CkAAAAC/pepe-spin.gif",
    "https://media.tenor.com/E4zKcgJP6nkAAAAd/pepe-happy.gif",
    "https://media.tenor.com/whhPVq8hUUMAAAAC/pepe-smile.gif",
    "https://media.tenor.com/wUoPc3VyBPUAAAAC/pepe-wink.gif"
]

# === FETCH PEPE GIFS FROM TENOR ===
def refresh_gifs():
    global pepe_gifs
    while True:
        try:
            resp = requests.get(
                "https://tenor.googleapis.com/v2/search",
                params={"q": "pepe", "key": "LIVDSRZULELA", "limit": 10},
                timeout=15
            )
            data = resp.json()
            results = data.get("results") or []
            gifs = []
            for r in results:
                media = r.get("media_formats") or {}
                gif = media.get("gif", {})
                url = gif.get("url")
                if url:
                    gifs.append(url)
            pepe_gifs = gifs or default_gifs
            print(f"✅ Updated Pepe GIFs — {len(pepe_gifs)} found")
        except Exception as e:
            pepe_gifs = default_gifs
            print(f"⚠️ GIF refresh failed: {e}")
        time.sleep(604800)  # weekly update

# === RANDOM EMOJIS ===
emojis = ["🐸", "💚", "🔥", "⚡", "💥", "😂", "🚀", "✨", "👑", "🧠", "😎"]
def random_emoji(count=3):
    return " ".join(random.choices(emojis, k=count))

# === FREE AI REPLY ===
def free_ai_reply(prompt):
    try:
        url = "https://api.mdcgpt.com/api/gpt"
        payload = {"prompt": f"Reply like Pepe AI — chaotic, witty, degen humor. Question: {prompt}"}
        res = requests.post(url, json=payload, timeout=10)
        return res.json().get("response", "Even Pepe has no clue 🐸💭")
    except Exception as e:
        print(f"AI error: {e}")
        return "Pepe is meditating in the pond right now 💤"

# === WISDOM OF THE DAY ===
def generate_daily_wisdom():
    try:
        resp = requests.post("https://api.mdcgpt.com/api/gpt", json={
            "prompt": "Give a funny, short, meme-style 'Pepe wisdom of the day'. Format it with humor and frog energy."
        }, timeout=10)
        return resp.json().get("response", "Ribbit... Stay hydrated and hodl 💧🐸")
    except:
        return random.choice([
            "Even frogs need patience — don’t FOMO every pump 🧘‍♂️🐸",
            "The swamp rewards the brave, not the greedy 💚",
            "1 Pepe = 1 Pepe — eternal truth 🧬",
            "Meme now, think later 🐸🔥"
        ])

# === HELPER: ignore admins & bots ===
def should_reply(message):
    try:
        if getattr(message.from_user, "is_bot", False):
            return False
        if message.chat.type in ["group", "supergroup"]:
            member = bot.get_chat_member(message.chat.id, message.from_user.id)
            if member.status in ['creator', 'administrator']:
                return False
        return True
    except:
        return False

# === MESSAGE HANDLER ===
@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_message(message):
    if not should_reply(message):
        return
    text = (message.text or "").lower()

    # Track active chat
    if message.chat.id not in active_chats:
        active_chats.add(message.chat.id)

    # === Contract Address (CA) ===
    if any(k in text for k in ["contract", "ca", "token address", "smart contract", "address"]):
        bot.reply_to(message,
            "🧾 *Contract Address (CA)*\n"
            "`BJ65ym9UYPkcfLSUuE9j4uXYuiG6TgA4pFn393Eppump`\n\n"
            "🔗 [Buy Here](https://pump.fun/coin/BJ65ym9UYPkcfLSUuE9j4uXYuiG6TgA4pFn393Eppump?s=09)\n"
            "🐸 Stay degen, stay $NPEPE!",
            parse_mode="Markdown")
        return

    # === Website / X account ===
    if "website" in text or "x account" in text or "twitter" in text:
        bot.reply_to(message,
            "🌐 Official Links:\n"
            "🐸 Website: https://t.co/4UziPz99j8\n"
            "🐦 X (Twitter): https://x.com/NPEPE_Verse?t=tBiSnw3W5a_lm0AN-jdE6w&s=09")
        return

    # === Roadmap ===
    if "roadmap" in text:
        bot.reply_to(message, "🐸 Roadmap:\nPhase 1 to 4 — Birth of Meme to Memetic Ascension.\nFull detail pinned in swamp 📜")
        return

    # === General reply or AI fallback ===
    reply = free_ai_reply(text)
    reply += " " + random_emoji(3)
    try:
        bot.reply_to(message, reply)
        if random.random() < 0.4:
            bot.send_animation(message.chat.id, random.choice(pepe_gifs))
    except Exception as e:
        print(f"Reply error: {e}")

# === DAILY ROUTINES ===
def scheduled_tasks():
    global last_quote_sent
    while True:
        now = datetime.datetime.utcnow()
        hour = now.hour

        # Morning greetings 6 UTC
        if hour == 6:
            for chat in list(active_chats):
                try:
                    msg = random.choice([
                        "☀️ GM frogs! Rise and meme — $NPEPE never sleeps 🐸",
                        "🐸 Morning swampers! New day, new pump 💚",
                        "🔥 It’s meme o’clock — grab your coffee and hop in!"
                    ]) + " " + random_emoji(3)
                    bot.send_message(chat, msg)
                except:
                    pass

        # Noon greetings 12 UTC
        if hour == 12:
            for chat in list(active_chats):
                try:
                    msg = random.choice([
                        "🍽️ Lunchtime degens — meme while you eat!",
                        "💚 Midday swamp check: frogs still strong 🐸",
                        "🔥 Keep the vibes pumping, it’s meme hour!"
                    ]) + " " + random_emoji(3)
                    bot.send_message(chat, msg)
                except:
                    pass

        # Night greetings 20 UTC
        if hour == 20:
            for chat in list(active_chats):
                try:
                    msg = random.choice([
                        "🌙 GN frogs — dream of memes & moonshots 💤",
                        "🐸 Rest well, tomorrow we raid again ⚔️",
                        "💫 The night is dark, but the memes are bright 💚"
                    ]) + " " + random_emoji(3)
                    bot.send_message(chat, msg)
                except:
                    pass

        # Quote of the day (once per 24h per group)
        for chat in list(active_chats):
            last_sent = last_quote_sent.get(chat)
            if not last_sent or (now - last_sent).days >= 1:
                wisdom = generate_daily_wisdom()
                try:
                    bot.send_message(chat, f"📜 *Pepe Wisdom of the Day*\n\n_{wisdom}_", parse_mode="Markdown")
                    last_quote_sent[chat] = now
                except:
                    pass

        time.sleep(3600)  # check hourly

# === KEEP ALIVE ===
app = Flask('')

@app.route('/')
def home():
    return "🐸 NewNPEPEBot is alive"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run_flask, daemon=True).start()
    Thread(target=refresh_gifs, daemon=True).start()
    Thread(target=scheduled_tasks, daemon=True).start()

keep_alive()
print("✅ NewNPEPEBot running nonstop 🐸💚")
bot.polling(none_stop=True, timeout=90)
