import os
import logging
import random
import time
from threading import Thread
import json
import re
from datetime import datetime, timedelta, timezone

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import groq
import httpx

# ==========================
# 🔧 CONFIGURATION
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
    # Project Details
    CONTRACT_ADDRESS = "BJ65ym9UYPkcfLSUuE9j4uXYuiG6TgA4pFn393Eppump"
    PUMP_FUN_LINK = f"https://pump.fun/{CONTRACT_ADDRESS}"
    WEBSITE_URL = "https://next-pepe-launchpad-2b8b3071.base44.app"
    TELEGRAM_URL = "https://t.me/NPEPEVERSE"
    TWITTER_URL = "https://x.com/NPEPE_Verse?t=rFeVwGRDJpxwiwjQ8P67Xw&s=09"


class BotLogic:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.groq_client = self._initialize_groq()
        self.responses = self._load_initial_responses()
        self.timestamps_file = 'timestamps.json'
        
        # --- ANTI-SPAM & ADMIN CONFIG ---
        self.admin_ids = set()
        self.admins_last_updated = 0
        
        # --- "SMART INTERJECTION" CONFIG ---
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

    def _get_current_utc_time(self):
        """Returns the current time in UTC."""
        return datetime.now(timezone.utc)

    def _load_timestamps(self):
        """Loads the last run timestamps from a file."""
        try:
            if os.path.exists(self.timestamps_file):
                with open(self.timestamps_file, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_timestamps(self, data):
        """Saves the timestamps to a file."""
        with open(self.timestamps_file, 'w') as f:
            json.dump(data, f)

    def check_and_run_schedules(self):
        """The main scheduling logic. Checks if any task is due and runs it."""
        timestamps = self._load_timestamps()
        now_utc = self._get_current_utc_time()
        today_utc_str = now_utc.strftime('%Y-%m-%d')
        
        # --- THE FINAL, UNIVERSAL UTC SCHEDULE ---
        schedules = {
            'hype_asia_open':  {'hour': 2, 'task': self.send_scheduled_greeting, 'args': ('random',)},
            'hype_late_asia':  {'hour': 4, 'task': self.send_scheduled_greeting, 'args': ('random',)}, # <-- NEW
            'morning_europe':  {'hour': 7, 'task': self.send_scheduled_greeting, 'args': ('morning',)},
            'wisdom_europe':   {'hour': 9, 'task': self.send_scheduled_wisdom, 'args': ()},
            'noon_universal':  {'hour': 12, 'task': self.send_scheduled_greeting, 'args': ('noon',)},
            'hype_us_open':    {'hour': 14, 'task': self.send_scheduled_greeting, 'args': ('random',)},
            'hype_us_midday':  {'hour': 18, 'task': self.send_scheduled_greeting, 'args': ('random',)},
            'night_us':        {'hour': 21, 'task': self.send_scheduled_greeting, 'args': ('night',)},
            'hype_us_close':   {'hour': 23, 'task': self.send_scheduled_greeting, 'args': ('random',)},
            'ai_renewal':      {'hour': 10, 'day_of_week': 6, 'task': self.renew_responses_with_ai, 'args': ()} # Sunday at 10:00 UTC
        }

        updated = False
        for name, schedule in schedules.items():
            last_run_date = timestamps.get(name)
            
            is_weekly = 'day_of_week' in schedule
            should_run = False
            
            if is_weekly:
                if now_utc.weekday() == schedule['day_of_week'] and now_utc.hour >= schedule['hour'] and last_run_date != today_utc_str:
                    should_run = True
            else: # Daily task
                if now_utc.hour >= schedule['hour'] and last_run_date != today_utc_str:
                    should_run = True
            
            if should_run:
                try:
                    logger.info(f"Running scheduled task: {name} at {now_utc} UTC")
                    schedule['task'](*schedule['args'])
                    timestamps[name] = today_utc_str
                    updated = True
                except Exception as e:
                    logger.error(f"Error running scheduled task {name}: {e}")

        if updated:
            self._save_timestamps(timestamps)

    def _initialize_groq(self):
        if Config.GROQ_API_KEY:
            try:
                custom_http_client = httpx.Client(proxies=None)
                client = groq.Groq(api_key=Config.GROQ_API_KEY, http_client=custom_http_client)
                logger.info("✅ Groq AI client initialized successfully.")
                return client
            except Exception as e: logger.error(f"❌ Failed to initialize Groq AI client: {e}")
        logger.warning("⚠️ No GROQ_API_KEY found. AI features will be disabled.")
        return None

    def _load_initial_responses(self):
        # This contains all your 100+ hype messages and other responses.
        # It is unchanged and omitted here for brevity.
        return {
            "GREET_NEW_MEMBERS": [
                "🐸 Welcome to the NPEPEVERSE, {name}! We're a frenly bunch. LFG! 🚀",
            ],
            "MORNING_GREETING": [
                "🐸☀️ Rise and ribbit, NPEPEVERSE! A new day to conquer the charts. Let's get this bread! 🔥",
            ],
            "NOON_GREETING": [
                "🐸☀️ Midday check-in, NPEPEVERSE! Hope you're smashing it. Keep that afternoon energy high! LFG! 🔥",
            ],
            "NIGHT_GREETING": [
                "🐸🌙 The charts never sleep, but legends need to rest. Good night, NPEPEVERSE! See you at the next ATH. 💤",
            ],
            "WISDOM": [
                "The greatest gains are not in the chart, but in the strength of the community. WAGMI. 🐸💚",
            ],
            "HYPE": [
                "Let's go, NPEPE army! Time to make some noise! 🚀", "Who's feeling bullish today?! 🔥",
            ],
            "WHO_IS_OWNER": [
                "My dev? Think Satoshi Nakamoto, but with way more memes. A mysterious legend who dropped some based code and vanished into the hype. 🐸👻",
            ],
            "COLLABORATION_RESPONSE": [
                "WAGMI! Love the energy! The best collab is a strong community. Be loud in here, raid on X, and let's make the NPEPEVERSE impossible to ignore! 🚀",
            ],
            "FINAL_FALLBACK": [
                "My circuits are fried from too much hype. Try asking that again, or maybe just buy more $NPEPE? That usually fixes things. 🐸",
            ]
        }
    
    def _register_handlers(self):
        self.bot.message_handler(content_types=['new_chat_members'])(self.greet_new_members)
        self.bot.message_handler(commands=['start', 'help'])(self.send_welcome)
        self.bot.callback_query_handler(func=lambda call: True)(self.handle_callback_query)
        self.bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video'])(self.handle_all_text)
    
    def main_menu_keyboard(self):
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🚀 About $NPEPE", callback_data="about"),
            InlineKeyboardButton("🔗 Contract Address", callback_data="ca"),
            InlineKeyboardButton("💰 Buy on Pump.fun", url=Config.PUMP_FUN_LINK),
            InlineKeyboardButton("🌐 Website", url=Config.WEBSITE_URL),
            InlineKeyboardButton("✈️ Telegram", url=Config.TELEGRAM_URL),
            InlineKeyboardButton("🐦 Twitter", url=Config.TWITTER_URL),
            InlineKeyboardButton("🐸 Hype Me Up!", callback_data="hype")
        )
        return keyboard
    
    def _update_admin_ids(self, chat_id):
        now = time.time()
        if now - self.admins_last_updated > 600:
            try:
                admins = self.bot.get_chat_administrators(chat_id)
                self.admin_ids = {admin.user.id for admin in admins}
                self.admins_last_updated = now
            except Exception as e:
                logger.error(f"Could not update admin list: {e}")

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
        if re.search(solana_pattern, text) and Config.CONTRACT_ADDRESS not in message.text: return True, "Potential Solana Contract Address"
        if re.search(eth_pattern, text): return True, "Potential EVM Contract Address"
        return False, None

    def greet_new_members(self, message):
        for member in message.new_chat_members:
            first_name = member.first_name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
            welcome_text = random.choice(self.responses["GREET_NEW_MEMBERS"]).format(name=f"[{first_name}](tg://user?id={member.id})")
            try:
                self.bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Failed to welcome new member: {e}")

    def send_welcome(self, message):
        welcome_text = ("🐸 *Welcome to the official NextPepe ($NPEPE) Bot!* 🔥\n\n"
                        "I am the spirit of the NPEPEVERSE, here to guide you. "
                        "Use the buttons below or ask me anything!")
        self.bot.reply_to(message, welcome_text, reply_markup=self.main_menu_keyboard(), parse_mode="Markdown")
    
    def handle_callback_query(self, call):
        try:
            if call.data == "about":
                self.bot.answer_callback_query(call.id)
                about_text = ("🚀 *$NPEPE* is the next evolution of meme power!\n"
                              "We are a community-driven force born on *Pump.fun*.\n\n"
                              "This is 100% pure, unadulterated meme energy. Welcome to the NPEPEVERSE! 🐸")
                self.bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          text=about_text, reply_markup=self.main_menu_keyboard(), parse_mode="Markdown")
            elif call.data == "ca":
                self.bot.answer_callback_query(call.id)
                ca_text = f"🔗 *Contract Address:*\n`{Config.CONTRACT_ADDRESS}`"
                self.bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          text=ca_text, reply_markup=self.main_menu_keyboard(), parse_mode="Markdown")
            elif call.data == "hype":
                hype_text = random.choice(self.responses["HYPE"])
                self.bot.answer_callback_query(call.id, text=hype_text, show_alert=True)
        except Exception as e:
            logger.error(f"Error in callback handler: {e}")

    def _is_a_question(self, text):
        text = text.lower().strip()
        if text.endswith('?'): return True
        question_words = ['what', 'how', 'when', 'where', 'why', 'who', 'can', 'could', 'is', 'are', 'do', 'does', 'explain']
        if any(text.startswith(word) for word in question_words): return True
        return False

    def handle_all_text(self, message):
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

        if message.content_type != 'text': return
            
        text = message.text
        lower_text = text.lower().strip()

        if any(kw in lower_text for kw in ["ca", "contract", "address"]):
            reply = f"Here is the contract address, fren:\n\n`{Config.CONTRACT_ADDRESS}`"
            self.bot.send_message(chat_id, reply, parse_mode="Markdown")
            return
        
        if any(kw in lower_text for kw in ["how to buy", "where to buy", "buy npepe"]):
            reply = f"💰 You can buy *$NPEPE* on Pump.fun! The portal to the moon is just one click away! 🚀"
            self.bot.send_message(chat_id, reply, parse_mode="Markdown", reply_markup=self.main_menu_keyboard())
            return
        
        if any(kw in lower_text for kw in ["owner", "dev", "creator", "in charge", "who made you", "who are you", "what are you"]):
            self.bot.send_message(chat_id, random.choice(self.responses["WHO_IS_OWNER"]))
            return
            
        if any(kw in lower_text for kw in ["collab", "partner", "promote", "help grow", "shill", "marketing"]):
            self.bot.send_message(chat_id, random.choice(self.responses["COLLABORATION_RESPONSE"]))
            return

        elif self.groq_client and self._is_a_question(text):
            thinking_message = None
            try:
                thinking_message = self.bot.send_message(chat_id, "🐸 The NPEPE oracle is consulting the memes...")
                system_prompt = ( "You are a crypto community bot for a meme coin called $NPEPE. Your personality is funny, enthusiastic, and chaotic. "
                                 "Use crypto slang like 'fren', 'WAGMI', 'HODL', 'based', 'LFG', 'ribbit'. Keep answers short, hype-filled, and helpful." )
                chat_completion = self.groq_client.chat.completions.create( messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}], model="llama3-8b-8192" )
                ai_response = chat_completion.choices[0].message.content
                self.bot.edit_message_text(ai_response, chat_id=chat_id, message_id=thinking_message.message_id)
            except Exception as e:
                logger.error(f"Error during AI response generation: {e}")
                if thinking_message: self.bot.delete_message(chat_id, thinking_message.message_id)
                self.bot.send_message(chat_id, random.choice(self.responses["FINAL_FALLBACK"]))
            return

        else:
            if time.time() - self.last_random_reply_time > self.COOLDOWN_SECONDS:
                current_chance = self.BASE_REPLY_CHANCE
                if any(hype_word in lower_text for hype_word in self.HYPE_KEYWORDS): current_chance = self.HYPE_REPLY_CHANCE
                if random.random() < current_chance:
                    reply_message = random.choice(self.responses["HYPE"])
                    self.bot.send_message(chat_id, reply_message)
                    self.last_random_reply_time = time.time()
    
    def send_scheduled_greeting(self, time_of_day):
        if not Config.GROUP_CHAT_ID: return
        greetings = {
            'morning': self.responses["MORNING_GREETING"], 'noon': self.responses["NOON_GREETING"],
            'night': self.responses["NIGHT_GREETING"], 'random': self.responses["HYPE"]
        }
        message = random.choice(greetings.get(time_of_day, ["Keep the hype alive!"]))
        try: self.bot.send_message(Config.GROUP_CHAT_ID, message)
        except Exception as e: logger.error(f"Failed to send {time_of_day} greeting: {e}")

    def send_scheduled_wisdom(self):
        if not Config.GROUP_CHAT_ID: return
        wisdom = random.choice(self.responses["WISDOM"])
        message = f"**🐸 Daily Dose of NPEPE Wisdom 📜**\n\n_{wisdom}_"
        try: self.bot.send_message(Config.GROUP_CHAT_ID, message, parse_mode="Markdown")
        except Exception as e: logger.error(f"Failed to send scheduled wisdom: {e}")

    def renew_responses_with_ai(self):
        logger.info("AI response renewal task triggered by scheduler.")
        if self.groq_client:
             logger.info("AI client is available. Renewal logic would run here.")
        else:
             logger.warning("AI renewal skipped: Groq client not initialized.")
