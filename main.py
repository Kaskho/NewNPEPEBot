import os
import telebot
import requests
import json
import random
import time
import datetime
from flask import Flask
from threading import Thread

# Read BOT_TOKEN from environment variable (recommended)
BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(BOT_TOKEN)

# === GLOBALS ===
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

# === FETCH TRENDING PEPE GIFS FROM TENOR (in background) ===
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
            # Some Tenor responses may vary; be defensive
            results = data.get("results") or []
            gifs = []
            for r in results:
                media = r.get("media_formats") or {}
                gif = media.get("gif", {})
                url = gif.get("url")
                if url:
                    gifs.append(url)
            if gifs:
                pepe_gifs = gifs
                print(f"✅ Updated Pepe GIFs — found {len(pepe_gifs)} new ones!")
            else:
                pepe_gifs = default_gifs
                print("⚠️ No gifs found in Tenor response — using defaults.")
        except Exception as e:
            pepe_gifs = default_gifs
            print(f"⚠️ Failed to refresh GIFs, using defaults. Error: {e}")
        # Sleep 7 days (604800 seconds)
        time.sleep(604800)

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

# === FREE AI REPLY (fallback) ===
def get_ai_reply(text):
    try:
        url = "https://api.mdcgpt.com/api/gpt"
        payload = {"prompt": f"Answer like NPEPE Folk AI — witty, short, on-brand. Question: {text}"}
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        return data.get("response", "Even Pepe has no clue about that 😅")
    except Exception as e:
        print(f"AI error: {e}")
        return "Oops... NPEPE AI is chilling in the pond 💤 Try again later!"

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
    except Exception as e:
        print(f"should_reply check error: {e}")
        # if check fails, default to not replying to avoid spam
        return False

# === MESSAGE HANDLER ===
@bot.message_handler(func=lambda msg: True, content_types=['text', 'photo', 'sticker', 'animation', 'document'])
def handle_message(message):
    if not should_reply(message):
        return

    text = (message.text or "").strip().lower()
    # add chat to active list for scheduled messages
    if message.chat.id not in active_chats and message.chat.type in ["group", "supergroup"]:
        active_chats.add(message.chat.id)

    if text in rules:
        reply = rules[text]
        if isinstance(reply, list):
            reply = random.choice(reply)
    else:
        # small chance to post engagement line instead of direct AI
        if random.random() < 0.05:
            reply = random.choice(random_engagement_lines)
        else:
            reply = get_ai_reply(text or "Hello")
    # attach emojis
    reply = reply + " " + random_emoji_set(random.randint(2,4))
    try:
        bot.reply_to(message, reply)
    except Exception as e:
        print(f"reply error: {e}")
    # optionally send a gif (50% chance)
    try:
        if pepe_gifs and random.random() < 0.5:
            bot.send_animation(message.chat.id, random.choice(pepe_gifs))
    except Exception as e:
        print(f"gif send error: {e}")

# === WELCOME NEW MEMBERS ===
@bot.message_handler(content_types=['new_chat_members'])
def on_new_member(message):
    chat_id = message.chat.id
    for user in message.new_chat_members:
        name = getattr(user, "first_name", None) or getattr(user, "username", None) or "frog fren"
        welcome = random.choice(welcome_messages).format(name=name)
        welcome = welcome + " " + random_emoji_set(3)
        try:
            bot.send_message(chat_id, welcome)
            if pepe_gifs and random.random() < 0.7:
                bot.send_animation(chat_id, random.choice(pepe_gifs))
        except Exception as e:
            print(f"welcome send error: {e}")
    # track chat for scheduled messages
    active_chats.add(chat_id)

# === TIME-BASED GREETINGS & RANDOM ENGAGEMENT ===
def daily_greetings_and_engagement():
    greeted = {"morning": False, "noon": False, "night": False}
    while True:
        try:
            now = datetime.datetime.utcnow()
            hour = now.hour
            # reset at UTC midnight
            if hour == 0:
                greeted = {"morning": False, "noon": False, "night": False}

            # Morning 05–10 UTC
            if 5 <= hour <= 10 and not greeted["morning"]:
                for chat in list(active_chats):
                    try:
                        msg = random.choice([
                            "☀️ GM frogs! New day, new memes — $NPEPE never sleeps 🐸",
                            "🐸 Morning swampers! Time to rise, meme, and conquer 💚",
                            "💥 Wake up degens! Pepe awaits your devotion this morning.",
                            "GM GM ☕ $NPEPE fuel = memes and chaos only!"
                        ]) + " " + random_emoji_set(3)
                        bot.send_message(chat, msg)
                        if pepe_gifs and random.random() < 0.7:
                            bot.send_animation(chat, random.choice(pepe_gifs))
                    except Exception as ex:
                        print(f"morning send error to {chat}: {ex}")
                        # if chat invalid, remove
                        try:
                            active_chats.discard(chat)
                        except:
                            pass
                greeted["morning"] = True

            # Noon 11–14 UTC
            if 11 <= hour <= 14 and not greeted["noon"]:
                for chat in list(active_chats):
                    try:
                        msg = random.choice([
                            "🍽️ Noon vibes only — meme while you eat, $NPEPE never rests!",
                            "🔥 Midday frogs — meme raids incoming!",
                            "🐸 It’s meme o’clock somewhere — lunch & pump session!",
                            "💚 Keep those memes flowing even during lunch break!"
                        ]) + " " + random_emoji_set(3)
                        bot.send_message(chat, msg)
                        if pepe_gifs and random.random() < 0.7:
                            bot.send_animation(chat, random.choice(pepe_gifs))
                    except Exception as ex:
                        print(f"noon send error to {chat}: {ex}")
                        try:
                            active_chats.discard(chat)
                        except:
                            pass
                greeted["noon"] = True

            # Night 18–22 UTC
            if 18 <= hour <= 22 and not greeted["night"]:
                for chat in list(active_chats):
                    try:
                        msg = random.choice([
                            "🌙 GN frogs — dream of memes and moonshots 🐸💤",
                            "💫 Night degen session starts — may Pepe bless your bags.",
                            "😴 Sleep tight swampers, tomorrow’s meme war awaits!",
                            "🐸 The night is dark but the memes are strong 💚"
                        ]) + " " + random_emoji_set(3)
                        bot.send_message(chat, msg)
                        if pepe_gifs and random.random() < 0.7:
                            bot.send_animation(chat, random.choice(pepe_gifs))
                    except Exception as ex:
                        print(f"night send error to {chat}: {ex}")
                        try:
                            active_chats.discard(chat)
                        except:
                            pass
                greeted["night"] = True

            # Random engagement small chance every loop
            for chat in list(active_chats):
                try:
                    if random.random() < 0.05:
                        msg = random.choice(random_engagement_lines) + " " + random_emoji_set(3)
                        bot.send_message(chat, msg)
                        if pepe_gifs and random.random() < 0.4:
                            bot.send_animation(chat, random.choice(pepe_gifs))
                except Exception as ex:
                    print(f"engagement send error to {chat}: {ex}")
                    try:
                        active_chats.discard(chat)
                    except:
                        pass

            time.sleep(900)  # check every 15 minutes
        except Exception as e:
            print(f"⚠️ Engagement loop error: {e}")
            time.sleep(60)

# === KEEP-ALIVE (Flask) ===
app = Flask('')

@app.route('/')
def home():
    return "🐸 NPEPE Folk AI Bot is alive"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run_web, daemon=True).start()
    Thread(target=daily_greetings_and_engagement, daemon=True).start()
    Thread(target=refresh_gifs, daemon=True).start()

keep_alive()
print("🐸 NPEPE Folk AI Bot (time-aware + engagement mode) running nonstop...")
bot.polling(none_stop=True, timeout=90)
import telebot
import os
from flask import Flask, request

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Example route for webhook
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://newnpepebot.onrender.com/' + BOT_TOKEN)
    return "Webhook set!", 200

# Example bot command
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🐸 Welcome to NPEPEFolk — The next meme legend!")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
