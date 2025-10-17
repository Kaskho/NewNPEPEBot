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


class BotLogic:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.groq_client = self._initialize_groq()
        self.responses = self._load_initial_responses()
        self.timestamps_file = 'timestamps.json'
        
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

    def _get_current_utc_time(self):
        return datetime.now(timezone.utc)

    def _load_timestamps(self):
        try:
            if os.path.exists(self.timestamps_file):
                with open(self.timestamps_file, 'r') as f:
                    content = f.read()
                    if content: return json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning("timestamps.json is corrupt or not found. A new one will be created.")
            return {}
        return {}

    def _save_timestamps(self, data):
        with open(self.timestamps_file, 'w') as f:
            json.dump(data, f)

    def check_and_run_schedules(self):
        timestamps = self._load_timestamps()
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

        updated = False
        for name, schedule in schedules.items():
            last_run_date = timestamps.get(name)
            is_weekly = 'day_of_week' in schedule
            should_run = False
            if is_weekly:
                if now_utc.weekday() == schedule['day_of_week'] and now_utc.hour >= schedule['hour'] and last_run_date != today_utc_str: should_run = True
            else:
                if now_utc.hour >= schedule['hour'] and last_run_date != today_utc_str: should_run = True
            if should_run:
                try:
                    logger.info(f"Running scheduled task: {name} at {now_utc} UTC")
                    schedule['task'](*schedule['args'])
                    timestamps[name] = today_utc_str
                    updated = True
                except Exception as e:
                    logger.error(f"Error running scheduled task {name}: {e}")
        if updated: self._save_timestamps(timestamps)

    def _initialize_groq(self):
        if Config.GROQ_API_KEY:
            try:
                custom_http_client = httpx.Client(proxies=None, timeout=15.0)
                client = groq.Groq(api_key=Config.GROQ_API_KEY, http_client=custom_http_client)
                logger.info("✅ Groq AI client initialized successfully with a 15-second timeout.")
                return client
            except Exception as e: logger.error(f"❌ Failed to initialize Groq AI client: {e}")
        logger.warning("⚠️ No GROQ_API_KEY found. AI features will be disabled.")
        return None

    def _load_initial_responses(self):
        return {
            "BOT_IDENTITY": [
                "Bot? No, fren. I am NPEPE. 🐸",
                "I'm not just a bot. I am the spirit of the NPEPEVERSE, in digital form. ✨",
            ],
            "WHO_IS_OWNER": [
                "My dev? Think Satoshi Nakamoto, but with way more memes. A mysterious legend who dropped some based code and vanished into the hype. 🐸👻",
            ],
            "FINAL_FALLBACK": [
                "My circuits are fried from too much hype. Try asking that again, or maybe just buy more $NPEPE? That usually fixes things. 🐸",
                "Ribbit... what was that? I was busy staring at the chart. Could you rephrase for this simple frog bot? 📈",
                "That question is too powerful, even for me. For now, let's focus on the mission: HODL, meme, and get to the moon! 🚀🌕",
                "Error 404: Brain not found. Currently running on pure vibes and diamond hands. Ask me about the contract address instead! 💎",
                "Maaf, koneksi saya ke bulan sepertinya sedang terganggu. Coba tanyakan lagi nanti. 🛰️",
                "Otak kodok saya baru saja mengalami 404. Bisa ulangi pertanyaannya, fren?",
                "Sirkuit hype saya sepertinya kepanasan. Beri saya waktu sejenak untuk mendinginkan diri. 🔥❄️"
            ],
            # ... All other response lists (HYPE, WISDOM, etc.) are unchanged and omitted for brevity ...
        }
    
    def _register_handlers(self):
        self.bot.message_handler(content_types=['new_chat_members'])(self.greet_new_members)
        self.bot.message_handler(commands=['start', 'help'])(self.send_welcome)
        self.bot.callback_query_handler(func=lambda call: True)(self.handle_callback_query)
        self.bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'sticker', 'document'])(self.handle_all_text)
    
    def main_menu_keyboard(self):
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🚀 About $NPEPE", callback_data="about"), InlineKeyboardButton("🔗 Contract Address", callback_data="ca"),
            InlineKeyboardButton("💰 Buy on Pump.fun", url=Config.PUMP_FUN_LINK), InlineKeyboardButton("🌐 Website", url=Config.WEBSITE_URL),
            InlineKeyboardButton("✈️ Telegram", url=Config.TELEGRAM_URL), InlineKeyboardButton("🐦 Twitter", url=Config.TWITTER_URL),
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
        if re.search(solana_pattern, text) and Config.CONTRACT_ADDRESS not in (message.text or ""): return True, "Potential Solana Contract Address"
        if re.search(eth_pattern, text): return True, "Potential EVM Contract Address"
        return False, None

    def greet_new_members(self, message):
        # ... (Unchanged)
        pass

    def send_welcome(self, message):
        # ... (Unchanged)
        pass
    
    def handle_callback_query(self, call):
        # ... (Unchanged)
        pass

    def _is_a_question(self, text):
        # ... (Unchanged)
        pass

    def handle_all_text(self, message):
        try:
            if not message: return
            
            # --- THE CRITICAL FIX IS HERE ---
            # Only run spam checks and hype messages in a group chat.
            if message.chat.type in ['group', 'supergroup']:
                chat_id = message.chat.id
                user_id = message.from_user.id
                
                # --- Anti-Spam Check ---
                self._update_admin_ids(chat_id)
                is_exempt = user_id in self.admin_ids
                if Config.GROUP_OWNER_ID and str(user_id) == Config.GROUP_OWNER_ID: is_exempt = True

                if not is_exempt:
                    is_spam, reason = self._is_spam_or_ad(message)
                    if is_spam:
                        try: self.bot.delete_message(chat_id, message.message_id)
                        except Exception as e: logger.error(f"Failed to delete spam message: {e}")
                        return
            
            # Continue processing for text messages in ANY chat (group or private)
            if not message.text: return
            
            text = message.text
            lower_text = text.lower().strip()
            chat_id = message.chat.id # Redefine for clarity

            # --- LOGIC FLOW (Commands work in private chat too) ---
            if any(kw in lower_text for kw in ["ca", "contract", "address"]):
                self.bot.send_message(chat_id, f"Here is the contract address, fren:\n\n`{Config.CONTRACT_ADDRESS}`", parse_mode="Markdown")
                return
            
            if any(kw in lower_text for kw in ["how to buy", "where to buy", "buy npepe"]):
                self.bot.send_message(chat_id, "💰 You can buy *$NPEPE* on Pump.fun! The portal to the moon is just one click away! 🚀", parse_mode="Markdown", reply_markup=self.main_menu_keyboard())
                return
            
            if any(kw in lower_text for kw in ["what are you", "what is this bot", "are you a bot", "what kind of bot"]):
                self.bot.send_message(chat_id, random.choice(self.responses["BOT_IDENTITY"]))
                return

            if any(kw in lower_text for kw in ["owner", "dev", "creator", "in charge", "who made you"]):
                self.bot.send_message(chat_id, random.choice(self.responses["WHO_IS_OWNER"]))
                return
                
            if any(kw in lower_text for kw in ["collab", "partner", "promote", "help grow", "shill", "marketing"]):
                self.bot.send_message(chat_id, random.choice(self.responses["COLLABORATION_RESPONSE"]))
                return

            elif self.groq_client and self._is_a_question(text):
                thinking_message = None
                try:
                    thinking_message = self.bot.send_message(chat_id, "🐸 The NPEPE oracle is consulting the memes...")
                    system_prompt = ( "You are a crypto community bot for $NPEPE. Your personality is funny, enthusiastic, and chaotic. " "Use crypto slang like 'fren', 'WAGMI', 'HODL', 'based', 'LFG', 'ribbit'. Keep answers short and hype-filled." )
                    chat_completion = self.groq_client.chat.completions.create( messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}], model="llama3-8b-8192" )
                    ai_response = chat_completion.choices[0].message.content
                    self.bot.edit_message_text(ai_response, chat_id=chat_id, message_id=thinking_message.message_id)
                except Exception as e:
                    logger.error(f"Error during AI response generation: {e}", exc_info=True)
                    if thinking_message: self.bot.edit_message_text(random.choice(self.responses["FINAL_FALLBACK"]), chat_id=chat_id, message_id=thinking_message.message_id)
                return

            # --- Smart Interjection ONLY runs in a group chat ---
            elif message.chat.type in ['group', 'supergroup']:
                if time.time() - self.last_random_reply_time > self.COOLDOWN_SECONDS:
                    current_chance = self.BASE_REPLY_CHANCE
                    if any(hype_word in lower_text for hype_word in self.HYPE_KEYWORDS): current_chance = self.HYPE_REPLY_CHANCE
                    if random.random() < current_chance:
                        self.bot.send_message(chat_id, random.choice(self.responses["HYPE"]))
                        self.last_random_reply_time = time.time()
        except Exception as e:
            logger.error(f"FATAL ERROR processing message: {e}", exc_info=True)
    
    # ... (send_scheduled_greeting, send_scheduled_wisdom, renew_responses_with_ai are unchanged)
