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

    def _get_current_wib_time(self):
        """Returns the current time in WIB (UTC+7)."""
        return datetime.now(timezone.utc) + timedelta(hours=7)

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
        now_wib = self._get_current_wib_time()
        today_str = now_wib.strftime('%Y-%m-%d')
        
        # --- THE COMPLETE, UPGRADED SCHEDULE ---
        schedules = {
            'morning': {'hour': 9, 'task': self.send_scheduled_greeting, 'args': ('morning',)},
            'hype_11am': {'hour': 11, 'task': self.send_scheduled_greeting, 'args': ('random',)},
            'wisdom': {'hour': 12, 'task': self.send_scheduled_wisdom, 'args': ()},
            'noon': {'hour': 14, 'task': self.send_scheduled_greeting, 'args': ('noon',)},
            'hype_4pm': {'hour': 16, 'task': self.send_scheduled_greeting, 'args': ('random',)},
            'hype_6pm': {'hour': 18, 'task': self.send_scheduled_greeting, 'args': ('random',)},
            'night': {'hour': 21, 'task': self.send_scheduled_greeting, 'args': ('night',)},
            'ai_renewal': {'hour': 10, 'day_of_week': 6, 'task': self.renew_responses_with_ai, 'args': ()} # Sunday is 6
        }

        updated = False
        for name, schedule in schedules.items():
            last_run_date = timestamps.get(name)
            
            is_weekly = 'day_of_week' in schedule
            should_run = False
            
            if is_weekly:
                if now_wib.weekday() == schedule['day_of_week'] and now_wib.hour >= schedule['hour'] and last_run_date != today_str:
                    should_run = True
            else: # Daily task
                if now_wib.hour >= schedule['hour'] and last_run_date != today_str:
                    should_run = True
            
            if should_run:
                try:
                    logger.info(f"Running scheduled task: {name}")
                    schedule['task'](*schedule['args'])
                    timestamps[name] = today_str
                    updated = True
                except Exception as e:
                    logger.error(f"Error running scheduled task {name}: {e}")

        if updated:
            self._save_timestamps(timestamps)

    def _initialize_groq(self):
        """Initializes the Groq AI client, ignoring environment proxies."""
        if Config.GROQ_API_KEY:
            try:
                custom_http_client = httpx.Client(proxies=None)
                client = groq.Groq(api_key=Config.GROQ_API_KEY, http_client=custom_http_client)
                logger.info("✅ Groq AI client initialized successfully.")
                return client
            except Exception as e:
                logger.error(f"❌ Failed to initialize Groq AI client: {e}")
        else:
            logger.warning("⚠️ No GROQ_API_KEY found. AI features will be disabled.")
        return None

    def _load_initial_responses(self):
        """Loads the default set of bot responses."""
        return {
            "GREET_NEW_MEMBERS": [
                "🐸 Welcome to the NPEPEVERSE, {name}! We're a frenly bunch. LFG! 🚀",
                "Ribbit! A new fren has appeared! Welcome, {name}! Glad to have you hopping with us. 🐸💚",
                "A wild {name} appears! Welcome to the $NPEPE community. Ask questions, share memes, and let's ride to the moon together! 🌕",
                "GM, {name}! You've just landed in the best corner of the crypto world. Welcome to the NPEPEVERSE! 🔥"
            ],
            "MORNING_GREETING": [
                "🐸☀️ Rise and ribbit, NPEPEVERSE! A new day to conquer the charts. Let's get this bread! 🔥",
                "GM legends! Coffee in one hand, diamond hands in the other. Let's make today legendary! 💎🙌",
                "Wakey wakey, frens! The sun is up and so is the hype. Let's send it! 🚀",
                "Good morning, NPEPE army! Hope you dreamt of green candles. Now let's make it a reality! 💚",
                "The early frog gets the gains! GM to all the hustlers in the NPEPEVERSE! 🐸💰",
                "A beautiful morning to be bullish! Let's show the world the power of NPEPE today! LFG! 🔥",
                "GM! Let's start the day with positive vibes and a shared mission: the moon! 🌕"
            ],
            "NOON_GREETING": [
                "🐸☀️ Midday check-in, NPEPEVERSE! Hope you're smashing it. Keep that afternoon energy high! LFG! 🔥",
                "Lunch time fuel-up! 🍔 Grab a bite, check the charts, and get ready for the afternoon pump. We're just getting warmed up! 🚀",
                "Just dropping by to say: stay based, stay hydrated, and stay diamond-handed. The best is yet to come! 💎🙌",
                "Hope you're having a legendary day, frens! The world is watching the NPEPEVERSE. Let's give them a show this afternoon! ✨",
                "The sun is high and so are our spirits! How's the NPEPE army feeling? Sound off! 🐸💚",
                "Quick break from conquering the crypto world. Remember to stretch those diamond hands. The second half of the day is ours! 💪",
                "Afternoon vibe check! ✅ Bullish. ✅ Based. ✅ Ready to send it. Let's finish the day strong, frens! 🚀"
            ],
            "NIGHT_GREETING": [
                "🐸🌙 The charts never sleep, but legends need to rest. Good night, NPEPEVERSE! See you at the next ATH. 💤",
                "GN, frens! Dream big, HODL strong. Tomorrow we continue our journey. 🚀",
                "Rest up, diamond hands. You've earned it. The hype will be here when you wake up! 💎",
                "Hope you had a based and bullish day. Good night, NPEPE army! 💚",
                "The moon is watching over us, frens. Sleep well. Our mission resumes at dawn! 🌕",
                "Signing off for the night! Keep those bags packed, the rocket is always ready. GN! 🚀",
                "Another great day in the books. Good night, NPEPEVERSE! Let's do it all again tomorrow, but bigger! 🔥"
            ],
            "WISDOM": [
                "The greatest gains are not in the chart, but in the strength of the community. WAGMI. 🐸💚",
                "Fear is temporary, HODLing is forever. Stay strong, fren.",
                "In a world of paper hands, be the diamond-handed rock. Your patience will be rewarded. 💎",
                "A red day is just a discount for the true believer. The NPEPEVERSE is built on conviction.",
                "They told you it was just a meme. They were right. And memes are the most powerful force on the internet. 🔥",
                "Look not at the price of today, but at the vision of tomorrow. We are building more than a token. 🚀",
                "The journey to the moon is a marathon, not a sprint. Conserve your energy, keep the faith. 🌕"
            ],
            "HYPE": [
                # Massively Expanded List
                "Let's go, NPEPE army! Time to make some noise! 🚀", "Who's feeling bullish today?! 🔥", "NPEPEVERSE is unstoppable! 🐸💚",
                "Keep that energy high! We're just getting started! ✨", "Diamond hands, where you at?! 💎🙌", "This is more than a coin, it's a movement!",
                "To the moon and beyond! LFG! 🌕", "Hype train is leaving the station! All aboard! 🚂", "Feel the power of the meme! 💪",
                "We're writing history, one block at a time! 📜", "Don't just HODL, be proud! We are NPEPE! 🐸", "The vibes are immaculate today, frens!",
                "Let's paint that chart green! 💚", "Remember why you're here. For the glory! 🔥", "This community is the best in crypto, period.",
                "Let them doubt. We know what we hold. 💎", "Ready for the next leg up? I know I am! 🚀", "Stay hyped, stay based!",
                "Every buy, every meme, every post matters! Keep it up! 💪", "NPEPE is the future of memes! 🐸", "Can you feel it? That's the feeling of inevitability.",
                "Let's show them what a real community looks like! 💚", "The pump is programmed. Stay tuned. 📈", "Who's ready to shock the world? ✨",
                "HODL the line, frens! Victory is near! ⚔️", "This is the one. You know it, I know it. 🐸", "Keep spreading the word. NPEPE is taking over!",
                "The bigger the base, the higher in space! 🚀", "Let's get it! No sleep 'til the moon! 🌕", "This is legendary. You are legendary. We are legendary.",
                "Don't let anyone shake you out. Diamond hands win. 💎", "The energy in here is electric! 🔥", "We are the new standard. The NPEPE standard.",
                "History has its eyes on us. Let's give them a show! 🐸🎬", "Let's make our ancestors proud. Buy more NPEPE. 😂🚀", "We're not just riding the wave, we ARE the wave! 🌊",
                "UNSTOPPABLE FORCE!", "This army is legendary.", "Generational wealth is minted here.", "My ribbits are tingling... something is coming.",
                "Keep shilling, keep winning.", "Inject it into my veins! 💉", "The market can try, but it can't stop this. 💪", "This is financial advice. (not financial advice)",
                "Every dip is a gift. 🎁", "WAGMI is not a meme, it's a promise.", "Building the future, one green candle at a time.", "They ain't seen nothing yet.",
                "Chart looking tastier than a midnight snack. 😋", "Load up your bags, frens. The rocket is boarding.", "This is pure, uncut hopium. And I love it.",
                "Feel that? The ground is shaking. 🐸", "We're not just going to the moon, we're building a colony there. 🌕🏡", "The sleeper has awakened.",
                "In a world of dogs and cats, be a frog. 🐸", "Let the FOMO begin. They'll wish they bought here.", "This is what peak performance looks like.",
                "Stay calm and HODL on. Panicking is for paper hands.", "The meme economy is strong with this one.", "This is the way.",
                "NPEPEVERSE > Multiverse.", "They called us a meme. We're becoming a religion. 🙏", "Screaming, crying, throwing up. (in a good way)",
                "This is the people's coin.", "The community is our utility. And it's priceless.", "Just up.", "I smell a new all-time high coming soon. 👃",
                "Let your diamond hands shine bright today. ✨", "Some people chase pumps. We ARE the pump.", "This is the beginning of our villain arc. 😈",
                "Don't tell your girlfriend, tell the world! 🗣️", "Absolutely based.", "We are so back.", "Never been so bullish in my life.",
                "This is the alpha. You are the alpha.", "The strength in here is unreal. 💚", "Keep the faith. The plan is working.", "It's NPEPE season, frens.",
                "The prophecy is being fulfilled.", "I've seen the future, and it's very, very green.", "Ribbiting news coming soon!", "Patience is for the rich. Let's get rich faster!",
                "Someone call an ambulance... but not for us! 🔥", "Are you not entertained?!", "This chart is a piece of art. 🎨", "I'm feeling froggy today! 🐸",
                "Resistance is futile.", "We are the signal in the noise.", "This is the sound of inevitability.", "If you're seeing this, you're still early.",
                "They will write songs about these days.", "The memes must flow.", "This is not a drill! I repeat, this is not a drill!", "Buckle up, buttercup.",
                "We're on a mission from the meme gods.", "Today is a good day to buy $NPEPE.", "It's beautiful. I've looked at this for five hours now.",
                "Maximum hopium levels engaged.", "The only way is up!", "This is just the appetizer. The main course is coming.", "We're all gonna make it, fren.",
                "Don't just stand there, buy something!", "This is a certified hood classic.", "I'm telling my kids this was the moon landing."
            ],
            "WHO_IS_OWNER": [
                "My dev? Think Satoshi Nakamoto, but with way more memes. A mysterious legend who dropped some based code and vanished into the hype. 🐸👻",
                "The dev? They're in the meme labs cooking up the next pump. They left me, a humble frog bot, in charge of the hype. So, what's up, fren? 🐸🔥",
                "You're speaking to the official mouthpiece! The main dev is a shadowy super-coder, too based for the spotlight. I handle the important work, like spamming rocket emojis. 🚀",
                "In the NPEPEVERSE, the community is the real boss. The dev just lit the fuse. My job as caretaker is to guard the flame and keep the vibes immaculate. ✨",
                "The creator is a legend whispered on the blockchain. I'm the spokesperson they built to make sure the memes stay dank and the FUD stays away. Now, let's talk about our trip to the moon. 🌕"
            ],
            "COLLABORATION_RESPONSE": [
                "WAGMI! Love the energy! The best collab is a strong community. Be loud in here, raid on X, and let's make the NPEPEVERSE impossible to ignore! 🚀",
                "Thanks, fren! We don't do paid promos, we ARE the promo! Your hype is the best marketing. Light up X with $NPEPE memes and be a legend in this chat! 🔥",
                "You want to help? Based! The NPEPE army runs on passion. Be active, welcome new frens, and spread the gospel of NPEPE across the internet like a religion! 🐸🙏"
            ],
            "FINAL_FALLBACK": [
                "My circuits are fried from too much hype. Try asking that again, or maybe just buy more $NPEPE? That usually fixes things. 🐸",
                "Ribbit... what was that? I was busy staring at the chart. Could you rephrase for this simple frog bot? 📈",
                "That question is too powerful, even for me. For now, let's focus on the mission: HODL, meme, and get to the moon! 🚀🌕"
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
                logger.info(f"Refreshed admin list for chat {chat_id}. Found {len(self.admin_ids)} admins.")
            except Exception as e:
                logger.error(f"Could not update admin list: {e}")

    def _is_spam_or_ad(self, message):
        text = message.text or message.caption or ""
        text = text.lower()
        if any(keyword in text for keyword in self.FORBIDDEN_KEYWORDS):
            return True, "Forbidden Keyword"
        if "http" in text or "t.me" in text:
            urls = re.findall(r'[\w\.-]+(?:\.[\w\.-]+)+', text)
            for url in urls:
                if not any(allowed in url for allowed in self.ALLOWED_DOMAINS):
                    return True, f"Unauthorized Link: {url}"
        solana_pattern = r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b'
        eth_pattern = r'\b0x[a-fA-F0-9]{40}\b'
        if re.search(solana_pattern, text) and Config.CONTRACT_ADDRESS not in message.text:
             return True, "Potential Solana Contract Address"
        if re.search(eth_pattern, text):
             return True, "Potential EVM Contract Address"
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
                about_text = ("🚀 *$NPEPE* is the next evolution of meme power!\n"
                              "We are a community-driven force born on *Pump.fun*.\n\n"
                              "This is 100% pure, unadulterated meme energy. Welcome to the NPEPEVERSE! 🐸")
                self.bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          text=about_text, reply_markup=self.main_menu_keyboard(), parse_mode="Markdown")
            elif call.data == "ca":
                ca_text = f"🔗 *Contract Address:*\n`{Config.CONTRACT_ADDRESS}`"
                self.bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          text=ca_text, reply_markup=self.main_menu_keyboard(), parse_mode="Markdown")
            elif call.data == "hype":
                hype_text = random.choice(self.responses["HYPE"])
                self.bot.answer_callback_query(call.id, text=hype_text, show_alert=True)
        except Exception as e:
            logger.error(f"Error in callback handler: {e}")

    def _is_a_question(self, text):
        """A simple heuristic to check if a message is a question."""
        text = text.lower().strip()
        if text.endswith('?'):
            return True
        question_words = ['what', 'how', 'when', 'where', 'why', 'who', 'can', 'could', 'is', 'are', 'do', 'does', 'explain']
        if any(text.startswith(word) for word in question_words):
            return True
        return False

    def handle_all_text(self, message):
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        self._update_admin_ids(chat_id)
        is_exempt = user_id in self.admin_ids
        if Config.GROUP_OWNER_ID and str(user_id) == Config.GROUP_OWNER_ID:
            is_exempt = True

        if not is_exempt:
            is_spam, reason = self._is_spam_or_ad(message)
            if is_spam:
                try:
                    self.bot.delete_message(chat_id, message.message_id)
                    logger.info(f"Deleted message from user {user_id} for reason: {reason}")
                except Exception as e:
                    logger.error(f"Failed to delete spam message: {e}")
                return

        if message.content_type != 'text':
            return
            
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

        if any(kw in lower_text for kw in ["who are you", "what are you", "what is this bot"]):
            self.bot.send_message(chat_id, random.choice(self.responses["WHO_IS_OWNER"])) # Note: Changed to WHO_IS_OWNER for fun
            return

        if any(kw in lower_text for kw in ["owner", "dev", "creator", "in charge", "who made you"]):
            self.bot.send_message(chat_id, random.choice(self.responses["WHO_IS_OWNER"]))
            return
            
        if any(kw in lower_text for kw in ["collab", "partner", "promote", "help grow", "shill", "marketing"]):
            self.bot.send_message(chat_id, random.choice(self.responses["COLLABORATION_RESPONSE"]))
            return

        elif self.groq_client and self._is_a_question(text):
            logger.info("Question detected. Passing to AI for an intelligent response.")
            thinking_message = None
            try:
                thinking_message = self.bot.send_message(chat_id, "🐸 The NPEPE oracle is consulting the memes...")
                system_prompt = (
                    "You are a crypto community bot for a meme coin called $NPEPE. "
                    "Your personality is funny, enthusiastic, and a bit chaotic, like a frog who drank too much coffee. "
                    "Use crypto slang like 'fren', 'WAGMI', 'HODL', 'based', 'LFG', 'ribbit'. "
                    "Keep your answers short, hype-filled, and as helpful as possible. You represent the NPEPEVERSE."
                )
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
                    model="llama3-8b-8192",
                )
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
                if any(hype_word in lower_text for hype_word in self.HYPE_KEYWORDS):
                    current_chance = self.HYPE_REPLY_CHANCE
                
                if random.random() < current_chance:
                    logger.info("Smart Interjection triggered. Sending a hype message.")
                    reply_message = random.choice(self.responses["HYPE"])
                    self.bot.send_message(chat_id, reply_message)
                    self.last_random_reply_time = time.time()
    
    def send_scheduled_greeting(self, time_of_day):
        if not Config.GROUP_CHAT_ID: return
        greetings = {
            'morning': self.responses["MORNING_GREETING"],
            'noon': self.responses["NOON_GREETING"],
            'night': self.responses["NIGHT_GREETING"],
            'random': self.responses["HYPE"]
        }
        message = random.choice(greetings.get(time_of_day, ["Keep the hype alive!"]))
        try:
            self.bot.send_message(Config.GROUP_CHAT_ID, message)
        except Exception as e:
            logger.error(f"Failed to send {time_of_day} greeting: {e}")

    def send_scheduled_wisdom(self):
        if not Config.GROUP_CHAT_ID: return
        wisdom = random.choice(self.responses["WISDOM"])
        message = f"**🐸 Daily Dose of NPEPE Wisdom 📜**\n\n_{wisdom}_"
        try:
            self.bot.send_message(Config.GROUP_CHAT_ID, message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send scheduled wisdom: {e}")

    def renew_responses_with_ai(self):
        logger.info("AI response renewal task triggered by scheduler.")
        # This is where you would put the complex logic to call the Groq AI
        # to get a JSON object and update self.responses.
        # For now, we'll just log that it was called.
        if self.groq_client:
             logger.info("AI client is available. Renewal logic would run here.")
             # You could send a message to the group announcing the 'upgrade'
             # self.bot.send_message(Config.GROUP_CHAT_ID, "🐸✨ My meme circuits have been upgraded!")
        else:
             logger.warning("AI renewal skipped: Groq client not initialized.")
