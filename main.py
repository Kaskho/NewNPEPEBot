import telebot
import requests
import json
import random
import time
import datetime
from flask import Flask
from threading import Thread

BOT_TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"
bot = telebot.TeleBot(BOT_TOKEN)

# === GLOBAL VARIABLE FOR GIFS ===
pepe_gifs = []
active_chats = set()

# === DEFAULT BACKUP GIFS ===
default_gifs = [
    "https://media.tenor.com/UcCjvPq4RrYAAAAC/pepe-dance.gif",
    "https://media.tenor.com/5cMtt1lB9CkAAAAC/pepe-spin.gif",
    "https://media.tenor.com/E4zKcgJP6nkAAAAd/pepe-happy.gif",
    "https://media.tenor.com/whhPVq8hUUMAAAAC/pepe-smile.gif",
    "https://media.tenor.com/wUoPc3VyBPUAAAAC/pepe-wink.gif",
    "https://media.tenor.com/1v7mM6o0X7MAAAAC/pepe-dance-frog.gif"
]

# === FETCH TRENDING PEPE GIFS FROM TENOR ===
def refresh_gifs():
    global pepe_gifs
    while True:
        try:
            response = requests.get(
                "https://tenor.googleapis.com/v2/search?q=pepe&key=LIVDSRZULELA&limit=10"
            )
            data = response.json()
            pepe_gifs = [r["media_formats"]["gif"]["url"] for r in data["results"]]
            print(f"✅ Updated Pepe GIFs — found {len(pepe_gifs)} new ones!")
        except:
            pepe_gifs = default_gifs
            print("⚠️ Failed to refresh GIFs, using defaults.")
        time.sleep(604800)  # refresh every 7 days

# === RANDOM EMOJI GENERATOR ===
emojis = ["🐸", "💚", "🔥", "⚡", "💥", "😂", "🚀", "✨", "👑", "🧠", "😎", "💦", "🤝"]

def random_emoji_set(count=2):
    return " ".join(random.choices(emojis, k=count))

# === GREETINGS & ENGAGEMENT ===
greetings = [
    "Yo fren 🐸🔥 Welcome to the swamp — home of NPEPE Folk!",
    "GM GM ☀️ Rise and meme, $NPEPE never sleeps!",
    "Sup frog bro? 🐸 Let’s pump some vibes!",
    "Ribbit! You’ve entered the NPEPE dimension!",
    "Hey degen 🧠💥 Ready to go full meme today?"
]

random_engagement_lines = [
    "🐸 Stay hydrated and memed, soldiers of $NPEPE!",
    "💚 Pepe bless this chat — no paper hands allowed!",
    "🔥 Someone say ‘Pump’? Because $NPEPE always delivers!",
    "⚔️ The swamp never sleeps — keep the meme war alive!",
    "🧠 Degens unite! $NPEPE is destiny, not a choice!"
]

welcome_messages = [
    "🐸 Welcome to the swamp, {name}! Grab your meme and join the chaos 💚",
    "Ribbit ribbit! 🐸 {name}, you just entered the NPEPE zone!",
    "🔥 Yo {name}! Pepe saw your soul and said — 'this one’s a degen' 😎",
    "💥 New frog detected: {name}! Time to meme or drown 🐸",
    "👑 Welcome {name}! One of us. One of us. 🐸"
]

# === RULES ===
rules = {
    "hello": random.choice(greetings),
    "gm": random.choice(greetings),
    "nextpepe": "NextPepe ($NPEPE) — half legend, half glitch. Born on pump.fun. No promises, just chaos 🐸💥",
    "npepe": "$NPEPE 💚 — the purest meme energy on-chain!",
    "where to buy npepe": "🐸 Buy here bro: https://pump.fun/coin/BJ65ym9UYPkcfLSUuE9j4uXYuiG6TgA4pFn393Eppump?s=09",
    "npepeverse": "🌍 Welcome to **NPEPEVERSE** — where memes become law and frogs reign supreme!",
    "wagmi": "WAGMI! The swamp is eternal 🐸🚀",
    "roadmap": """
🐸 **NPEPE ROADMAP**

1️⃣ PHASE 1 — BIRTH OF THE MEME  
Pepe reincarnates as NextPepe — half legend, half glitch.  
💥 Launched on Pump.fun, no presale, no roadmap, just destiny.  
📈 Early degenerates smell profit.  
😎 “If it’s stupid but works — it’s $NPEPE.”

---

2️⃣ PHASE 2 — THE GREAT FROG AWAKENING  
⚔️ The #NPEPEARMY rises.  
💬 Meme raids flood timelines.  
📸 Pepe GIFs everywhere.  
🧠 “Buy. Meme. Repeat.” becomes religion.

---

3️⃣ PHASE 3 — EXPANSION OF THE NPEPEVERSE  
🌍 Welcome to the NPEPEVERSE, where memes are law.  
🤝 Fake partnerships. Real hype.  
👾 “AI Pepe”, “Dark Pepe”, “MiniPepe.”  
💫 Pepe is inevitable.

---

4️⃣ PHASE 4 — MEMETIC ASCENSION  
🌙 Whales dream about frogs.  
🛍️ Merch so dumb it’s genius.  
🎨 Community art goes viral.  
📢 Prophecy: “1 Pepe = 1 Pepe.”

💬 *Tagline:* “From the swamp to the chain — NextPepe runs the game.” 🧬
"""
}

# === AI REPLY FUNCTION ===
def get_ai_reply(text):
    try:
        url = "https://api.mdcgpt.com/api/gpt"
        payload = {
            "prompt": f"Answer like NPEPE Folk AI — a funny, chaotic, meme-loving assistant that talks like a crypto degen. Be witty, short, and on-brand. Question: {text}"
        }
        response = requests.post(url, json=payload)
        data = response.json()
        return data.get("response", "Even Pepe has no clue about that 😅")
    except:
        return "Oops... NPEPE AI is chilling in the pond 💤 Try again later!"

# === FILTER ADMINS, OWNERS & BOTS ===
def should_reply(message):
    if message.from_user.is_bot:
        return False
    try:
        member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status in ['creator', 'administrator']:
            return False
    except:
        pass
    return True

# === MESSAGE HANDLER ===
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if not should_reply(message):
        return
    text = message.text.lower()
    reply = rules[text] if text in rules else get_ai_reply(text)
    reply += " " + random_emoji_set(random.randint(2, 4))
    bot.reply_to(message, reply)
    if pepe_gifs and random.random() < 0.5:
        bot.send_animation(message.chat.id, random.choice(pepe_gifs))

# === WELCOME NEW MEMBERS ===
@bot.message_handler(content_types=['new_chat_members'])
def on_new_member(message):
    chat_id = message.chat.id
    for user in message.new_chat_members:
        name = user.first_name or user.username or "frog fren"
        welcome = random.choice(welcome_messages).format(name=name)
        welcome += " " + random_emoji_set(3)
        bot.send_message(chat_id, welcome)
        if pepe_gifs:
            bot.send_animation(chat_id, random.choice(pepe_gifs))
    active_chats.add(chat_id)

# === RANDOM ENGAGEMENT + TIME-BASED GREETINGS ===
def daily_greetings_and_engagement():
    greeted = {"morning": False, "noon": False, "night": False}
    while True:
        try:
            now = datetime.datetime.utcnow()
            hour = now.hour
            # Reset greeting flags daily
            if hour == 0:
                greeted = {"morning": False, "noon": False, "night": False}

            # Morning greetings (UTC 05–10)
            if 5 <= hour <= 10 and not greeted["morning"]:
                for chat in active_chats:
                    msg = random.choice([
                        "☀️ GM frogs! New day, new memes — $NPEPE never sleeps 🐸",
                        "🐸 Morning swampers! Time to rise, meme, and conquer 💚",
                        "💥 Wake up degens! Pepe awaits your devotion this morning.",
                        "GM GM ☕ $NPEPE fuel = memes and chaos only!"
                    ]) + " " + random_emoji_set(3)
                    bot.send_message(chat, msg)
                    if pepe_gifs:
                        bot.send_animation(chat, random.choice(pepe_gifs))
                greeted["morning"] = True

            # Noon greetings (UTC 11–14)
            if 11 <= hour <= 14 and not greeted["noon"]:
                for chat in active_chats:
                    msg = random.choice([
                        "🍽️ Noon vibes only — meme while you eat, $NPEPE never rests!",
                        "🔥 Midday frogs — meme raids incoming!",
                        "🐸 It’s meme o’clock somewhere — lunch & pump session!",
                        "💚 Keep those memes flowing even during lunch break!"
                    ]) + " " + random_emoji_set(3)
                    bot.send_message(chat, msg)
                    if pepe_gifs:
                        bot.send_animation(chat, random.choice(pepe_gifs))
                greeted["noon"] = True

            # Night greetings (UTC 18–22)
            if 18 <= hour <= 22 and not greeted["night"]:
                for chat in active_chats:
                    msg = random.choice([
                        "🌙 GN frogs — dream of memes and moonshots 🐸💤",
                        "💫 Night degen session starts — may Pepe bless your bags.",
                        "😴 Sleep tight swampers, tomorrow’s meme war awaits!",
                        "🐸 The night is dark but the memes are strong 💚"
                    ]) + " " + random_emoji_set(3)
                    bot.send_message(chat, msg)
                    if pepe_gifs:
                        bot.send_animation(chat, random.choice(pepe_gifs))
                greeted["night"] = True

            # Random engagement in between
            for chat in active_chats:
                if random.random() < 0.05:
                    msg = random.choice(random_engagement_lines) + " " + random_emoji_set(3)
                    bot.send_message(chat, msg)
                    if pepe_gifs and random.random() < 0.4:
                        bot.send_animation(chat, random.choice(pepe_gifs))
            time.sleep(900)  # check every 15 minutes
        except Exception as e:
            print(f"⚠️ Engagement loop error: {e}")
            time.sleep(60)

# === KEEP-ALIVE SERVER ===
app = Flask('')

@app.route('/')
def home():
    return "🐸 NPEPE Folk AI Bot is alive"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()
    Thread(target=daily_greetings_and_engagement).start()
    Thread(target=refresh_gifs).start()

keep_alive()
print("🐸 NPEPE Folk AI Bot (time-aware + engagement mode) running nonstop...")
bot.polling(none_stop=True, timeout=90)
