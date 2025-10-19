import os
import logging
import random
import time
import json
import re
from datetime import datetime, timezone
import threading

from config import Config

try:
    import psycopg2
    logging.info("DIAGNOSTIK (bot_logic.py): Pustaka 'psycopg2' BERHASIL diimpor.")
except ImportError as e:
    psycopg2 = None
    logging.critical(f"DIAGNOSTIK (bot_logic.py): KRITIS - GAGAL mengimpor 'psycopg2'. Persistensi akan dinonaktifkan. Error: {e}")

try:
    import groq
    import httpx
except ImportError:
    groq = None
    httpx = None

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BotLogic:
    def __init__(self, bot_instance: telebot.TeleBot):
        self.bot = bot_instance
        
        if not Config.DATABASE_URL():
            logger.critical("FATAL (BotLogic init): DATABASE_URL tidak ditemukan. Persistensi tidak akan berfungsi.")
        if not psycopg2:
            logger.critical("FATAL (BotLogic init): Pustaka psycopg2 tidak tersedia. Persistensi tidak akan berfungsi.")
            
        self.groq_client = self._initialize_groq()
        self.responses = self._load_initial_responses()
        self.admin_ids = set()
        self.admins_last_updated = 0
        self.last_random_reply_time = 0
        
        self.COOLDOWN_SECONDS = 90
        self.BASE_REPLY_CHANCE = 0.20
        self.HYPE_REPLY_CHANCE = 0.75
        self.HYPE_KEYWORDS = ['buy', 'bought', 'pump', 'moon', 'lfg', 'send it', 'green', 'bullish', 'rocket', 'diamond', 'hodl', 'ape', 'lets go', 'ath']
        self.FORBIDDEN_KEYWORDS = ['airdrop', 'giveaway', 'presale', 'private sale', 'whitelist', 'signal', 'pump group', 'trading signal', 'investment advice', 'other project']
        self.ALLOWED_DOMAINS = ['pump.fun', 't.me/NPEPEVERSE', 'x.com/NPEPE_Verse', 'base44.app']
        
        self._ensure_db_table_exists()
        self._register_handlers()
        logger.info("BotLogic berhasil diinisialisasi.")

    def _get_db_connection(self):
        db_url = Config.DATABASE_URL()
        if not db_url or not psycopg2:
            logger.warning("DATABASE_URL tidak diatur atau psycopg2 tidak terinstal. Persistensi dinonaktifkan.")
            return None
        try:
            return psycopg2.connect(db_url)
        except Exception as e:
            logger.error(f"Koneksi DB gagal: {e}")
            return None

    def _ensure_db_table_exists(self):
        conn = self._get_db_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("CREATE TABLE IF NOT EXISTS schedule_log (task_name TEXT PRIMARY KEY, last_run_date TEXT)")
                conn.commit()
                logger.info("Tabel database 'schedule_log' siap.")
            except Exception as e:
                logger.error(f"Gagal membuat tabel jadwal: {e}")
            finally:
                conn.close()

    def _get_last_run_date(self, task_name):
        conn = self._get_db_connection()
        if not conn: return None
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT last_run_date FROM schedule_log WHERE task_name = %s", (task_name,))
                result = cursor.fetchone()
            return result[0] if result else None
        finally:
            if conn: conn.close()

    def _update_last_run_date(self, task_name, run_date):
        conn = self._get_db_connection()
        if not conn: return
        try:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO schedule_log (task_name, last_run_date) VALUES (%s, %s) ON CONFLICT (task_name) DO UPDATE SET last_run_date = EXCLUDED.last_run_date", (task_name, run_date))
            conn.commit()
        except Exception as e:
            logger.error(f"Gagal memperbarui DB untuk {task_name}: {e}")
            try: conn.rollback()
            except: pass
        finally:
            if conn: conn.close()

    def _get_current_utc_time(self):
        return datetime.now(timezone.utc)

    def check_and_run_schedules(self):
        now_utc = self._get_current_utc_time()
        today_utc_str = now_utc.strftime('%Y-%m-%d')
        
        schedules = {
            'hype_asia_open':  {'hour': 2, 'task': self.send_scheduled_greeting, 'args': ('random',)},
            'morning_europe':  {'hour': 7, 'task': self.send_scheduled_greeting, 'args': ('morning',)},
            'wisdom_europe':   {'hour': 9, 'task': self.send_scheduled_wisdom, 'args': ()},
            'noon_universal':  {'hour': 12, 'task': self.send_scheduled_greeting, 'args': ('noon',)},
            'night_us':        {'hour': 21, 'task': self.send_scheduled_greeting, 'args': ('night',)},
            'ai_renewal':      {'hour': 10, 'day_of_week': 5, 'task': self.renew_responses_with_ai, 'args': ()}
        }

        for name, schedule in schedules.items():
            last_run_date = self._get_last_run_date(name)
            should_run = False
            is_weekly = 'day_of_week' in schedule
            
            if is_weekly:
                iso_key = now_utc.strftime('%Y-W%U')
                if (now_utc.weekday() == schedule['day_of_week'] and now_utc.hour >= schedule['hour'] and last_run_date != iso_key):
                    should_run = True
            else:
                if (now_utc.hour >= schedule['hour'] and last_run_date != today_utc_str):
                    should_run = True
            
            if should_run:
                try:
                    logger.info(f"Menjalankan tugas terjadwal: {name} pada {now_utc.isoformat()}")
                    schedule['task'](*schedule.get('args', ()))
                    run_marker = iso_key if is_weekly else today_utc_str
                    self._update_last_run_date(name, run_marker)
                except Exception as e:
                    logger.error(f"Error menjalankan tugas terjadwal {name}: {e}", exc_info=True)

    def _initialize_groq(self):
        api_key = Config.GROQ_API_KEY()
        if not api_key or not groq or not httpx:
            logger.warning("Groq tidak tersedia atau GROQ_API_KEY hilang. Fitur AI dinonaktifkan.")
            return None
        try:
            client = groq.Groq(api_key=api_key, http_client=httpx.Client(timeout=15.0))
            logger.info("Klien Groq berhasil diinisialisasi.")
            return client
        except Exception as e:
            logger.error(f"Gagal menginisialisasi klien Groq: {e}")
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
        keyboard.add(
            InlineKeyboardButton("🚀 About $NPEPE", callback_data="about"),
            InlineKeyboardButton("🔗 Contract Address", callback_data="ca"),
            InlineKeyboardButton("💰 Buy on Pump.fun", url=Config.PUMP_FUN_LINK()),
            InlineKeyboardButton("🌐 Website", url=Config.WEBSITE_URL()),
            InlineKeyboardButton("✈️ Telegram", url=Config.TELEGRAM_URL()),
            InlineKeyboardButton("🐦 Twitter", url=Config.TWITTER_URL()),
            InlineKeyboardButton("🐸 Hype Me Up!", callback_data="hype")
        )
        return keyboard
    
    def _update_admin_ids(self, chat_id):
        now = time.time()
        if now - self.admins_last_updated > 600:
            try:
                admins = self.bot.get_chat_administrators(chat_id)
                self.admin_ids = {admin.user.id for admin in admins if admin and admin.user}
                self.admins_last_updated = now
            except Exception as e:
                logger.error(f"Could not update admin list: {e}")

    def _is_spam_or_ad(self, message):
        text = (message.text or message.caption or "") if message else ""
        text_lower = text.lower()
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in text_lower: return True, f"Forbidden Keyword: {keyword}"
        if "http" in text_lower or "t.me" in text_lower:
            urls = re.findall(r'(https?://[^\s]+)|([\w\.-]+(?:\.[\w\.-]+)+)', text)
            urls_flat = [u[0] or u[1] for u in urls if u[0] or u[1]]
            for url in urls_flat:
                if not any(domain in url for domain in self.ALLOWED_DOMAINS): return True, f"Unauthorized Link: {url}"
        solana_pattern = r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b'
        eth_pattern = r'\b0x[a-fA-F0-9]{40}\b'
        if re.search(solana_pattern, text) and Config.CONTRACT_ADDRESS() not in text: return True, "Potential Solana Contract Address"
        if re.search(eth_pattern, text): return True, "Potential EVM Contract Address"
        return False, None

    def greet_new_members(self, message):
        try:
            for member in message.new_chat_members:
                first_name = (member.first_name or "fren").replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
                welcome_text = random.choice(self.responses.get("GREET_NEW_MEMBERS", [])).format(name=f"[{first_name}](tg://user?id={member.id})")
                self.bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error in greet_new_members: {e}", exc_info=True)

    def send_welcome(self, message):
        welcome_text = (" 🐸  *Welcome to the official NextPepe ($NPEPE) Bot!* 🔥 \n\n" "I am the spirit of the NPEPEVERSE, here to guide you. Use the buttons below or ask me anything!")
        self.bot.reply_to(message, welcome_text, reply_markup=self.main_menu_keyboard(), parse_mode="Markdown")

    def handle_callback_query(self, call):
        try:
            if call.data == "hype":
                hype_text = random.choice(self.responses.get("HYPE", ["LFG!"]))
                self.bot.answer_callback_query(call.id, text=hype_text, show_alert=True)
            elif call.data == "about":
                self.bot.answer_callback_query(call.id)
                about_text = (" 🚀  *$NPEPE* is the next evolution of meme power!\n" "We are a community-driven force born on *Pump.fun*.\n\n" "This is 100% pure, unadulterated meme energy. Welcome to the NPEPEVERSE!  🐸 ")
                self.bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=about_text, reply_markup=self.main_menu_keyboard(), parse_mode="Markdown")
            elif call.data == "ca":
                self.bot.answer_callback_query(call.id)
                ca_text = f" 🔗  *Contract Address:*\n`{Config.CONTRACT_ADDRESS()}`"
                self.bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=ca_text, reply_markup=self.main_menu_keyboard(), parse_mode="Markdown")
            else:
                self.bot.answer_callback_query(call.id, text="Action not recognized.")
        except Exception as e:
            logger.error(f"Error in callback handler: {e}", exc_info=True)
            try: self.bot.answer_callback_query(call.id, text="Sorry, something went wrong!", show_alert=True)
            except: pass

    def _is_a_question(self, text):
        if not text or not isinstance(text, str): return False
        txt = text.strip().lower()
        if txt.endswith('?'): return True
        question_words = ['what', 'how', 'when', 'where', 'why', 'who', 'can', 'could', 'is', 'are', 'do', 'does', 'explain']
        return any(txt.startswith(w) for w in question_words)

    def handle_all_text(self, message):
        try:
            if not message: return
            if message.chat.type in ['group', 'supergroup']:
                chat_id = message.chat.id
                user_id = message.from_user.id
                self._update_admin_ids(chat_id)
                is_exempt = user_id in self.admin_ids
                if Config.GROUP_OWNER_ID() and str(user_id) == str(Config.GROUP_OWNER_ID()): is_exempt = True
                if not is_exempt:
                    is_spam, reason = self._is_spam_or_ad(message)
                    if is_spam:
                        self.bot.delete_message(chat_id, message.message_id)
                        logger.info(f"Deleted message {message.message_id} from {user_id} reason: {reason}")
                        return
            
            text = (message.text or message.caption or "")
            if not text: return
            lower_text = text.lower().strip()
            chat_id = message.chat.id
            
            if any(kw in lower_text for kw in ["ca", "contract", "address"]):
                self.bot.send_message(chat_id, f"Here is the contract address, fren:\n\n`{Config.CONTRACT_ADDRESS()}`", parse_mode="Markdown")
                return
            if any(kw in lower_text for kw in ["how to buy", "where to buy", "buy npepe"]):
                self.bot.send_message(chat_id, " 💰  You can buy *$NPEPE* on Pump.fun! The portal to the moon is one click away!  🚀 ", parse_mode="Markdown", reply_markup=self.main_menu_keyboard())
                return
            if any(kw in lower_text for kw in ["what are you", "what is this bot", "are you a bot"]):
                self.bot.send_message(chat_id, random.choice(self.responses.get("BOT_IDENTITY", [])))
                return
            if any(kw in lower_text for kw in ["owner", "dev", "creator", "who made you"]):
                self.bot.send_message(chat_id, random.choice(self.responses.get("WHO_IS_OWNER", [])))
                return
            if any(kw in lower_text for kw in ["collab", "partner", "promote", "marketing"]):
                self.bot.send_message(chat_id, random.choice(self.responses.get("COLLABORATION_RESPONSE", [])))
                return

            if self.groq_client and self._is_a_question(text):
                thinking_message = self.bot.send_message(chat_id, " 🐸  The NPEPE oracle is consulting the memes...")
                try:
                    system_prompt = ( "You are a crypto community bot for $NPEPE. Funny, enthusiastic, chaotic. " "Use slang: ‘fren’, ‘WAGMI’, ‘HODL’, ‘based’, ‘LFG’, ‘ribbit’. Keep answers short." )
                    chat_completion = self.groq_client.chat.completions.create( messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}], model="llama3-8b-8192", temperature=0.7, max_tokens=150 )
                    ai_response = chat_completion.choices[0].message.content
                    self.bot.edit_message_text(ai_response, chat_id=chat_id, message_id=thinking_message.message_id)
                except Exception as e:
                    logger.error(f"AI response error: {e}", exc_info=True)
                    fallback = random.choice(self.responses.get("FINAL_FALLBACK", ["Sorry fren, can’t answer now."]))
                    self.bot.edit_message_text(fallback, chat_id=chat_id, message_id=thinking_message.message_id)
                return

            if message.chat.type in ['group', 'supergroup']:
                now_ts = time.time()
                if now_ts - self.last_random_reply_time < self.COOLDOWN_SECONDS: return
                current_chance = self.BASE_REPLY_CHANCE
                if any(hype_word in lower_text for hype_word in self.HYPE_KEYWORDS): current_chance = self.HYPE_REPLY_CHANCE
                if random.random() < current_chance:
                    self.bot.send_message(chat_id, random.choice(self.responses.get("HYPE", ["LFG!"])))
                    self.last_random_reply_time = now_ts
        except Exception as e:
            logger.error(f"FATAL ERROR processing message: {e}", exc_info=True)

    def send_scheduled_greeting(self, time_of_day):
        group_id = Config.GROUP_CHAT_ID()
        if not group_id: return
        greetings = { 'morning': self.responses.get("MORNING_GREETING", []), 'noon': self.responses.get("NOON_GREETING", []), 'night': self.responses.get("NIGHT_GREETING", []), 'random': self.responses.get("HYPE", []) }
        message_list = greetings.get(time_of_day, ["Keep the hype alive!"])
        if message_list:
            message = random.choice(message_list)
            self.bot.send_message(group_id, message)
            logger.info(f"Sent scheduled greeting ({time_of_day}) to {group_id}")

    def send_scheduled_wisdom(self):
        group_id = Config.GROUP_CHAT_ID()
        if not group_id: return
        wisdom_list = self.responses.get("WISDOM", [])
        if wisdom_list:
            wisdom = random.choice(wisdom_list)
            message = f"** 🐸  Daily Dose of NPEPE Wisdom  📜 **\n\n_{wisdom}_"
            self.bot.send_message(group_id, message, parse_mode="Markdown")
            logger.info("Sent scheduled wisdom.")

    def renew_responses_with_ai(self):
        logger.info("AI response renewal scheduled.")
        if not self.groq_client:
            logger.warning("Skipping AI renewal: Groq not initialized.")
            return
        try:
            # PERUBAHAN: Menambahkan kategori sapaan ke dalam daftar pembaruan AI
            categories_to_renew = {
                "HYPE": ("Produce 100 short hype messages for a meme coin bot. Funny, enthusiastic, use slang like LFG, WAGMI, ribbit, fren. Each 5-30 words.", 50),
                "WISDOM": ("Produce 20 wise, motivational quotes for a crypto community. Meme-themed, short, inspiring about HODL, community, moon.", 10),
                "MORNING_GREETING": ("Produce 20 enthusiastic 'Good Morning' greetings for a crypto community. Use slang like GM, LFG, bullish. Each 10-30 words.", 10),
                "NOON_GREETING": ("Produce 20 motivational midday greetings for a crypto community. Encourage them to keep the energy high. Each 10-30 words.", 10),
                "NIGHT_GREETING": ("Produce 20 calm 'Good Night' greetings for a crypto community. Wish them sweet dreams of green candles. Use slang like GN, HODL. Each 10-30 words.", 10),
                "GREET_NEW_MEMBERS": ("Produce 20 welcoming messages for new members of a crypto community. IMPORTANT: Each message MUST include the placeholder '{name}' to mention the user.", 10)
            }
            for category, (prompt, min_count) in categories_to_renew.items():
                logger.info(f"Attempting to renew AI responses for category: {category}")
                completion = self.groq_client.chat.completions.create(
                    messages=[{"role": "system", "content": prompt}],
                    model="llama3-8b-8192",
                    temperature=1.0,
                    max_tokens=2000
                )
                text = completion.choices[0].message.content
                # Memastikan placeholder {name} tidak 'rusak' saat pemisahan
                if category == "GREET_NEW_MEMBERS":
                    new_lines = [line.strip() for line in text.split('\n') if '{name}' in line and line.strip()]
                else:
                    new_lines = [line.strip() for line in re.split(r'\n|\d+\.', text) if line.strip() and len(line) > 5]
                
                if len(new_lines) >= min_count:
                    self.responses[category] = new_lines
                    logger.info(f"✅ {category} responses successfully renewed by AI with {len(new_lines)} entries.")
                else:
                    logger.warning(f"⚠️ AI renewal for {category} returned too few lines ({len(new_lines)}); skipping update for this category.")
        except Exception as e:
            logger.error(f"❌ AI renewal failed: {e}", exc_info=True)
