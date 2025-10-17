import os
import logging
import random
import time
from threading import Thread
import json
import re
from datetime import datetime, timedelta, timezone
import sqlite3

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import groq
import httpx

# ==========================
# 🔧 KONFIGURASI
# ==========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Config:
    """Configuration class for the bot."""
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    GROUP_CHAT_ID = os.environ.get("GROUP_CHAT_ID")
    GROUP_OWNER_ID = os.environ.get("GROUP_OWNER_ID")
    WEBHOOK_URL = f"{WEBHOOK_BASE_URL}/{BOT_TOKEN}" if WEBHOOK_BASE_URL and BOT_TOKEN else ""
    # Detail Proyek
    CONTRACT_ADDRESS = "BJ65ym9UYPkcfLSUuE9j4uXYuiG6TgA4pFn393Eppump"
    PUMP_FUN_LINK = f"https://pump.fun/{CONTRACT_ADDRESS}"
    WEBSITE_URL = "https://next-npepe-launchpad-2b8b3071.base44.app"
    TELEGRAM_URL = "https://t.me/NPEPEVERSE"
    TWITTER_URL = "https://x.com/NPEPE_Verse?t=rFeVwGRDJpxwiwjQ8P67Xw&s=09"
    # --- BARU: Path untuk Database ---
    # Render menyediakan disk persisten di /var/data/
    DATABASE_PATH = '/var/data/schedule.db'


class BotLogic:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.groq_client = self._initialize_groq()
        self.responses = self._load_initial_responses()
        self._setup_database() # <-- PANGGILAN BARU
        
        self.admin_ids = set()
        self.admins_last_updated = 0
        self.last_random_reply_time = 0
        self.COOLDOWN_SECONDS = 90
        self.BASE_REPLY_CHANCE = 0.20
        self.HYPE_REPLY_CHANCE = 0.75
        self.HYPE_KEYWORDS = [
            'buy', 'bought', 'pump', 'moon', 'lfg', 'send it', 'green', 'bullish',
            'rocket', 'diamond', 'hodl', 'ape', 'lets go', 'ath'
        ]
        self.FORBIDDEN_KEYWORDS = [
            'airdrop', 'giveaway', 'presale', 'private sale', 'whitelist', 'signal', 
            'pump group', 'trading signal', 'investment advice', 'other project'
        ]
        self.ALLOWED_DOMAINS = [ 'pump.fun', 't.me/NPEPEVERSE', 'x.com/NPEPE_Verse', 'base44.app' ]
        self._register_handlers()

    # --- FUNGSI DATABASE BARU ---
    def _setup_database(self):
        """Membuat tabel database jika belum ada."""
        try:
            # Pastikan direktori ada
            os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
            conn = sqlite3.connect(Config.DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedule_log (
                    task_name TEXT PRIMARY KEY,
                    last_run_date TEXT
                )
            ''')
            conn.commit()
            conn.close()
            logger.info("Database setup successful.")
        except Exception as e:
            logger.error(f"Failed to setup database: {e}")

    def _get_last_run_date(self, task_name):
        """Mengambil tanggal terakhir tugas dijalankan dari database."""
        try:
            conn = sqlite3.connect(Config.DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT last_run_date FROM schedule_log WHERE task_name = ?", (task_name,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to get last run date for {task_name}: {e}")
            return None

    def _update_last_run_date(self, task_name, run_date):
        """Memperbarui tanggal terakhir tugas dijalankan di database."""
        try:
            conn = sqlite3.connect(Config.DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO schedule_log (task_name, last_run_date) VALUES (?, ?)", (task_name, run_date))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update last run date for {task_name}: {e}")

    # --- FUNGSI PENJADWALAN YANG DIPERBARUI ---
    def check_and_run_schedules(self):
        now_utc = self._get_current_utc_time()
        today_utc_str = now_utc.strftime('%Y-%m-%d')
        
        schedules = {
            'hype_asia_open':  {'hour': 2, 'task': self.send_scheduled_greeting, 'args': ('random',)},
            'hype_late_asia':  {'hour': 4, 'task': self.send_scheduled_greeting, 'args': ('random',)},
            'morning_europe':  {'hour': 7, 'task': self.send_scheduled_greeting, 'args': ('morning',)},
            'wisdom_europe':   {'hour': 9, 'task': self.send_scheduled_wisdom, 'args': ()},
            'noon_universal':  {'hour': 12, 'task': self.send_scheduled_greeting, 'args': ('noon',)},
            'hype_us_open':    {'hour': 14, 'task': self.send_scheduled_greeting, 'args': ('random',)},
            'hype_us_midday':  {'hour': 18, 'task': self.send_scheduled_greeting, 'args': ('random',)},
            'night_us':        {'hour': 21, 'task': self.send_scheduled_greeting, 'args': ('night',)},
            'hype_us_close':   {'hour': 23, 'task': self.send_scheduled_greeting, 'args': ('random',)},
            'ai_renewal':      {'hour': 10, 'day_of_week': 6, 'task': self.renew_responses_with_ai, 'args': ()}
        }

        for name, schedule in schedules.items():
            last_run_date = self._get_last_run_date(name)
            
            should_run = False
            is_weekly = 'day_of_week' in schedule
            
            if is_weekly:
                if (now_utc.weekday() == schedule['day_of_week'] and 
                    now_utc.hour >= schedule['hour'] and 
                    last_run_date != today_utc_str):
                    should_run = True
            else:
                if (now_utc.hour >= schedule['hour'] and 
                    last_run_date != today_utc_str):
                    should_run = True
            
            if should_run:
                try:
                    logger.info(f"Running scheduled task: {name} because its time has passed at {now_utc} UTC")
                    schedule['task'](*schedule['args'])
                    self._update_last_run_date(name, today_utc_str) # <-- MENGGUNAKAN DATABASE
                except Exception as e:
                    logger.error(f"Error running scheduled task {name}: {e}")

    # ... Sisa file (dari _get_current_utc_time hingga akhir) persis sama dengan versi sebelumnya ...
    # ... Kode lengkapnya disertakan di bawah ini untuk kepastian ...
    def _get_current_utc_time(self):
        return datetime.now(timezone.utc)
    def _initialize_groq(self):
        if Config.GROQ_API_KEY:
            try:
                custom_http_client = httpx.Client(proxies=None, timeout=15.0)
                client = groq.Groq(api_key=Config.GROQ_API_KEY, http_client=custom_http_client)
                logger.info("✅ Groq AI client initialized successfully.")
                return client
            except Exception as e: 
                logger.error(f"❌ Failed to initialize Groq AI client: {e}")
        logger.warning("⚠️ No GROQ_API_KEY found. AI features will be disabled.")
        return None
    def _load_initial_responses(self):
        return {
            "BOT_IDENTITY": [ "Bot? No, fren. I am NPEPE. 🐸", "I'm not just a bot. I am the spirit of the NPEPEVERSE, in digital form. ✨", "Call me a bot if you want, but I'm really just NPEPE's hype machine. My only job is to spread the gospel. LFG! 🚀", "Are you asking if I'm just code? Nah. I'm the based energy of NPEPE, here to send it. *ribbit*", "Part bot, part frog, all legend. But you can just call me NPEPE.", "What kind of bot? The kind that's destined for the moon. I am NPEPE. 🌕", "I'm NPEPE, manifested. My code runs on pure, uncut hype and diamond hands. 💎", "I am the signal, not the noise. I am NPEPE.", "They built a bot, but the spirit of NPEPE took over. So, yeah. I'm NPEPE.", "I'm the ghost in the machine, and the machine is fueled by NPEPE. So, that's what I am. 👻" ],
            "WHO_IS_OWNER": [ "My dev? Think Satoshi Nakamoto, but with way more memes. A mysterious legend who dropped some based code and vanished into the hype. 🐸👻", "The dev is busy. I'm the caretaker. Any complaints can be submitted to me in the form of a 100x pump. 📈", "In the NPEPEVERSE, the community is the real boss. The dev just lit the fuse. My job as caretaker is to guard the flame and keep the vibes immaculate. ✨", "The creator is a legend whispered on the blockchain. I'm the spokesperson they built to make sure the memes stay dank and the FUD stays away.", "The owner is the spirit of decentralization itself. I'm just the humble groundskeeper of this fine establishment. 🐸", "You're looking for the boss? They're busy in the meme labs. You can talk to me, I'm the official spokesperson. What's up, fren? 🔥" ],
            "FINAL_FALLBACK": [ "My circuits are fried from too much hype. Try asking that again, or maybe just buy more $NPEPE? That usually fixes things. 🐸", "Ribbit... what was that? I was busy staring at the chart. Could you rephrase for this simple frog bot? 📈", "That question is too powerful, even for me. For now, let's focus on the mission: HODL, meme, and get to the moon! 🚀🌕", "Error 404: Brain not found. Currently running on pure vibes and diamond hands. Ask me about the contract address instead! 💎", "Maaf, koneksi saya ke bulan sepertinya sedang terganggu. Coba tanyakan lagi nanti. 🛰️", "Otak kodok saya baru saja mengalami 404. Bisa ulangi pertanyaannya, fren?", "Sirkuit hype saya sepertinya kepanasan. Beri saya waktu sejenak untuk mendinginkan diri. 🔥❄️" ],
            "GREET_NEW_MEMBERS": [ "🐸 Welcome to the NPEPEVERSE, {name}! We're a frenly bunch. LFG! 🚀", "Ribbit! A new fren has appeared! Welcome, {name}! Glad to have you hopping with us. 🐸💚", "A wild {name} appears! Welcome to the $NPEPE community. Ask questions, share memes, and let's ride to the moon together! 🌕", "GM, {name}! You've just landed in the best corner of the crypto world. Welcome to the NPEPEVERSE! 🔥" ],
            "MORNING_GREETING": [ "🐸☀️ Rise and ribbit, NPEPEVERSE! A new day to conquer the charts. Let's get this bread! 🔥", "GM legends! Coffee in one hand, diamond hands in the other. Let's make today legendary! 💎🙌", "Wakey wakey, frens! The sun is up and so is the hype. Let's send it! 🚀", "Good morning, NPEPE army! Hope you dreamt of green candles. Now let's make it a reality! 💚", "The early frog gets the gains! GM to all the hustlers in the NPEPEVERSE! 🐸💰", "A beautiful morning to be bullish! Let's show the world the power of NPEPE today! LFG! 🔥", "GM! Let's start the day with positive vibes and a shared mission: the moon! 🌕" ],
            "NOON_GREETING": [ "🐸☀️ Midday check-in, NPEPEVERSE! Hope you're smashing it. Keep that afternoon energy high! LFG! 🔥", "Lunch time fuel-up! 🍔 Grab a bite, check the charts, and get ready for the afternoon pump. We're just getting warmed up! 🚀", "Just dropping by to say: stay based, stay hydrated, and stay diamond-handed. The best is yet to come! 💎🙌", "Hope you're having a legendary day, frens! The world is watching the NPEPEVERSE. Let's give them a show this afternoon! ✨", "The sun is high and so are our spirits! How's the NPEPE army feeling? Sound off! 🐸💚", "Quick break from conquering the crypto world. Remember to stretch those diamond hands. The second half of the day is ours! 💪", "Afternoon vibe check! ✅ Bullish. ✅ Based. ✅ Ready to send it. Let's finish the day strong, frens! 🚀" ],
            "NIGHT_GREETING": [ "🐸🌙 The charts never sleep, but legends need to rest. Good night, NPEPEVERSE! See you at the next ATH. 💤", "GN, frens! Dream big, HODL strong. Tomorrow we continue our journey. 🚀", "Rest up, diamond hands. You've earned it. The hype will be here when you wake up! 💎", "Hope you had a based and bullish day. Good night, NPEPE army! 💚", "The moon is watching over us, frens. Sleep well. Our mission resumes at dawn! 🌕", "Signing off for the night! Keep those bags packed, the rocket is always ready. GN! 🚀", "Another great day in the books. Good night, NPEPEVERSE! Let's do it all again tomorrow, but bigger! 🔥" ],
            "WISDOM": [ "The greatest gains are not in the chart, but in the strength of the community. WAGMI. 🐸💚", "Fear is temporary, HODLing is forever. Stay strong, fren.", "In a world of paper hands, be the diamond-handed rock. Your patience will be rewarded. 💎", "A red day is just a discount for the true believer. The NPEPEVERSE is built on conviction.", "They told you it was just a meme. They were right. And memes are the most powerful force on the internet. 🔥", "Look not at the price of today, but at the vision of tomorrow. We are building more than a token. 🚀", "The journey to the moon is a marathon, not a sprint. Conserve your energy, keep the faith. 🌕" ],
            "HYPE": [ "Let's go, NPEPE army! Time to make some noise! 🚀", "Who's feeling bullish today?! 🔥", "NPEPEVERSE is unstoppable! 🐸💚", "Keep that energy high! We're just getting started! ✨", "Diamond hands, where you at?! 💎🙌", "This is more than a coin, it's a movement!", "To the moon and beyond! LFG! 🌕", "Hype train is leaving the station! All aboard! 🚂", "Feel the power of the meme! 💪", "We're writing history, one block at a time! 📜", "Don't just HODL, be proud! We are NPEPE! 🐸", "The vibes are immaculate today, frens!", "Let's paint that chart green! 💚", "Remember why you're here. For the glory! 🔥", "This community is the best in crypto, period.", "Let them doubt. We know what we hold. 💎", "Ready for the next leg up? I know I am! 🚀", "Stay hyped, stay based!", "Every buy, every meme, every post matters! Keep it up! 💪", "NPEPE is the future of memes! 🐸", "Can you feel it? That's the feeling of inevitability.", "Let's show them what a real community looks like! 💚", "The pump is programmed. Stay tuned. 📈", "Who's ready to shock the world? ✨", "HODL the line, frens! Victory is near! ⚔️", "This is the one. You know it, I know it. 🐸", "Keep spreading the word. NPEPE is taking over!", "The bigger the base, the higher in space! 🚀", "Let's get it! No sleep 'til the moon! 🌕", "This is legendary. You are legendary. We are legendary.", "Don't let anyone shake you out. Diamond hands win. 💎", "The energy in here is electric! 🔥", "We are the new standard. The NPEPE standard.", "History has its eyes on us. Let's give them a show! 🐸🎬", "Let's make our ancestors proud. Buy more NPEPE. 😂🚀", "We're not just riding the wave, we ARE the wave! 🌊" ],
            "COLLABORATION_RESPONSE": [ "WAGMI! Love the energy! The best collab is a strong community. Be loud in here, raid on X, and let's make the NPEPEVERSE impossible to ignore! 🚀", "Thanks, fren! We don't do paid promos, we ARE the promo! Your hype is the best marketing. Light up X with $NPEPE memes and be a legend in this chat! 🔥", "You want to help? Based! The NPEPE army runs on passion. Be active, welcome new frens, and spread the gospel of NPEPE across the internet like a religion! 🐸🙏", "Glad to have you on board! The most valuable thing you can do is bring your energy here every day and make some noise on X. Let's build this together! 💚", "That's the spirit! To grow, we need soldiers. Your mission: engage with our posts on X, create memes, and keep the vibe in this Telegram electric! ⚡️", "Thanks for the offer, legend! Our marketing plan is YOU. Be the hype you want to see in the world. Let's get $NPEPE trending! 📈", "Let's do it! Your role is Chief Hype Officer. Your KPIs are memes posted and raids joined. Welcome to the team! 😎", "Awesome! We need more frens like you. Let's make this the most active, legendary community in crypto. Start by telling a fren about $NPEPE today! 🗣️" ],
        }
    def _register_handlers(self):
        self.bot.message_handler(content_types=['new_chat_members'])(self.greet_new_members)
        self.bot.message_handler(commands=['start', 'help'])(self.send_welcome)
        self.bot.callback_query_handler(func=lambda call: True)(self.handle_callback_query)
        self.bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'sticker', 'document'])(self.handle_all_text)
    def main_menu_keyboard(self):
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add( InlineKeyboardButton("🚀 About $NPEPE", callback_data="about"), InlineKeyboardButton("🔗 Contract Address", callback_data="ca"), InlineKeyboardButton("💰 Buy on Pump.fun", url=Config.PUMP_FUN_LINK), InlineKeyboardButton("🌐 Website", url=Config.WEBSITE_URL), InlineKeyboardButton("✈️ Telegram", url=Config.TELEGRAM_URL), InlineKeyboardButton("🐦 Twitter", url=Config.TWITTER_URL), InlineKeyboardButton("🐸 Hype Me Up!", callback_data="hype") )
        return keyboard
    def _update_admin_ids(self, chat_id):
        now = time.time()
        if now - self.admins_last_updated > 600:
            try:
                admins = self.bot.get_chat_administrators(chat_id)
                self.admin_ids = {admin.user.id for admin in admins}
                self.admins_last_updated = now
            except Exception as e: logger.error(f"Could not update admin list: {e}")
    def _is_spam_or_ad(self, message):
        text = message.text or message.caption or ""
        text = text.lower()
        if any(keyword in text for keyword in self.FORBIDDEN_KEYWORDS): return True, "Forbidden Keyword"
        if "http" in text or "t.me" in text:
            urls = re.findall(r'[\w\.-]+(?:\.[\w\.-]+)+', text)
            for url in urls:
                if not any(allowed in url for allowed in self.ALLOWED_DOMAINS): return True, f"Unauthorized Link: {url}"
        solana_pattern = r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b'
        eth_pattern = r'\b0x[a-fA-F0-9]{40}\b'
        if re.search(solana_pattern, text) and Config.CONTRACT_ADDRESS not in (message.text or ""): return True, "Potential Solana Contract Address"
        if re.search(eth_pattern, text): return True, "Potential EVM Contract Address"
        return False, None
    def greet_new_members(self, message):
        for member in message.new_chat_members:
            first_name = member.first_name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
            welcome_text = random.choice(self.responses.get("GREET_NEW_MEMBERS", [])).format(name=f"[{first_name}](tg://user?id={member.id})")
            try: self.bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")
            except Exception as e: logger.error(f"Failed to welcome new member: {e}")
    def send_welcome(self, message):
        welcome_text = ("🐸 *Welcome to the official NextPepe ($NPEPE) Bot!* 🔥\n\n" "I am the spirit of the NPEPEVERSE, here to guide you. " "Use the buttons below or ask me anything!")
        self.bot.reply_to(message, welcome_text, reply_markup=self.main_menu_keyboard(), parse_mode="Markdown")
    def handle_callback_query(self, call):
        try:
            if call.data == "hype":
                hype_text = random.choice(self.responses.get("HYPE", ["LFG!"]))
                self.bot.answer_callback_query(call.id, text=hype_text, show_alert=True)
            elif call.data == "about":
                self.bot.answer_callback_query(call.id)
                about_text = ("🚀 *$NPEPE* is the next evolution of meme power!\n" "We are a community-driven force born on *Pump.fun*.\n\n" "This is 100% pure, unadulterated meme energy. Welcome to the NPEPEVERSE! 🐸")
                self.bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=about_text, reply_markup=self.main_menu_keyboard(), parse_mode="Markdown")
            elif call.data == "ca":
                self.bot.answer_callback_query(call.id)
                ca_text = f"🔗 *Contract Address:*\n`{Config.CONTRACT_ADDRESS}`"
                self.bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=ca_text, reply_markup=self.main_menu_keyboard(), parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error in callback handler: {e}")
            try: self.bot.answer_callback_query(call.id, text="Sorry, something went wrong!", show_alert=True)
            except: pass
    def _is_a_question(self, text):
        text = text.lower().strip()
        if text.endswith('?'): return True
        question_words = ['what', 'how', 'when', 'where', 'why', 'who', 'can', 'could', 'is', 'are', 'do', 'does', 'explain']
        if any(text.startswith(word) for word in question_words): return True
        return False
    def handle_all_text(self, message):
        try:
            if not message: return
            if message.chat.type in ['group', 'supergroup']:
                chat_id = message.chat.id
                user_id = message.from_user.id
                self._update_admin_ids(chat_id)
                is_exempt = user_id in self.admin_ids
                if Config.GROUP_OWNER_ID and str(user_id) == Config.GROUP_OWNER_ID: is_exempt = True
                if not is_exempt:
                    is_spam, reason = self._is_spam_or_ad(message)
                    if is_spam:
                        try: self.bot.delete_message(chat_id, message.message_id)
                        except Exception as e: logger.error(f"Failed to delete spam message: {e}")
                        return
            if not message.text: return
            text = message.text
            lower_text = text.lower().strip()
            chat_id = message.chat.id
            if (Config.GROUP_OWNER_ID and message.entities and message.chat.type in ['group', 'supergroup']):
                for entity in message.entities:
                    if entity.type == 'text_mention' and str(entity.user.id) == Config.GROUP_OWNER_ID:
                        self.bot.send_message(chat_id, random.choice(self.responses.get("WHO_IS_OWNER", [])))
                        return
            if any(kw in lower_text for kw in ["ca", "contract", "address"]):
                self.bot.send_message(chat_id, f"Here is the contract address, fren:\n\n`{Config.CONTRACT_ADDRESS}`", parse_mode="Markdown")
                return
            if any(kw in lower_text for kw in ["how to buy", "where to buy", "buy npepe"]):
                self.bot.send_message(chat_id, "💰 You can buy *$NPEPE* on Pump.fun! The portal to the moon is just one click away! 🚀", parse_mode="Markdown", reply_markup=self.main_menu_keyboard())
                return
            if any(kw in lower_text for kw in ["what are you", "what is this bot", "are you a bot", "what kind of bot"]):
                self.bot.send_message(chat_id, random.choice(self.responses.get("BOT_IDENTITY", [])))
                return
            if any(kw in lower_text for kw in ["owner", "dev", "creator", "in charge", "who made you"]):
                self.bot.send_message(chat_id, random.choice(self.responses.get("WHO_IS_OWNER", [])))
                return
            if any(kw in lower_text for kw in ["collab", "partner", "promote", "help grow", "shill", "marketing"]):
                self.bot.send_message(chat_id, random.choice(self.responses.get("COLLABORATION_RESPONSE", [])))
                return
            elif self.groq_client and self._is_a_question(text):
                thinking_message = self.bot.send_message(chat_id, "🐸 The NPEPE oracle is consulting the memes...")
                try:
                    system_prompt = ( "You are a crypto community bot for $NPEPE. Your personality is funny, enthusiastic, and chaotic. " "Use crypto slang like 'fren', 'WAGMI', 'HODL', 'based', 'LFG', 'ribbit'. Keep answers short and hype-filled." )
                    chat_completion = self.groq_client.chat.completions.create( messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}], model="llama3-8b-8192" )
                    ai_response = chat_completion.choices[0].message.content
                    self.bot.edit_message_text(ai_response, chat_id=chat_id, message_id=thinking_message.message_id)
                except Exception as e:
                    logger.error(f"Error during AI response generation: {e}", exc_info=True)
                    try: self.bot.edit_message_text(random.choice(self.responses.get("FINAL_FALLBACK", [])), chat_id=chat_id, message_id=thinking_message.message_id)
                    except Exception as edit_e:
                        logger.error(f"Failed to edit message to fallback, sending new message: {edit_e}")
                        self.bot.send_message(chat_id, random.choice(self.responses.get("FINAL_FALLBACK", [])))
                return
            elif message.chat.type in ['group', 'supergroup']:
                if time.time() - self.last_random_reply_time > self.COOLDOWN_SECONDS:
                    current_chance = self.BASE_REPLY_CHANCE
                    if any(hype_word in lower_text for hype_word in self.HYPE_KEYWORDS): current_chance = self.HYPE_REPLY_CHANCE
                    if random.random() < current_chance:
                        self.bot.send_message(chat_id, random.choice(self.responses.get("HYPE", [])))
                        self.last_random_reply_time = time.time()
        except Exception as e:
            logger.error(f"FATAL ERROR processing message: {e}", exc_info=True)
    def send_scheduled_greeting(self, time_of_day):
        if not Config.GROUP_CHAT_ID: return
        greetings = { 'morning': self.responses.get("MORNING_GREETING", []), 'noon': self.responses.get("NOON_GREETING", []), 'night': self.responses.get("NIGHT_GREETING", []), 'random': self.responses.get("HYPE", []) }
        message_list = greetings.get(time_of_day, ["Keep the hype alive!"])
        if message_list:
            message = random.choice(message_list)
            try: self.bot.send_message(Config.GROUP_CHAT_ID, message)
            except Exception as e: logger.error(f"Failed to send {time_of_day} greeting: {e}")
    def send_scheduled_wisdom(self):
        if not Config.GROUP_CHAT_ID: return
        wisdom_list = self.responses.get("WISDOM", [])
        if wisdom_list:
            wisdom = random.choice(wisdom_list)
            message = f"**🐸 Daily Dose of NPEPE Wisdom 📜**\n\n_{wisdom}_"
            try: self.bot.send_message(Config.GROUP_CHAT_ID, message, parse_mode="Markdown")
            except Exception as e: logger.error(f"Failed to send scheduled wisdom: {e}")
    def renew_responses_with_ai(self):
        logger.info("AI response renewal task triggered by scheduler.")
        if self.groq_client: logger.info("AI client is available. Renewal logic would run here.")
        else: logger.warning("AI renewal skipped: Groq client not initialized.")
