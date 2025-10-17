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
# ... (Config class is unchanged)
class Config:
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    GROUP_CHAT_ID = os.environ.get("GROUP_CHAT_ID")
    GROUP_OWNER_ID = os.environ.get("GROUP_OWNER_ID")
    WEBHOOK_URL = f"{WEBHOOK_BASE_URL}/{BOT_TOKEN}" if WEBHOOK_BASE_URL and BOT_TOKEN else ""
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

        self._register_handlers()

    def _load_initial_responses(self):
        return {
            "HYPE": [
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
                "The prophecy is being fulfilled.", "I've seen the future, and it's very, very green."
            ],
            # ... all other response lists like "MORNING_GREETING", "WHO_IS_OWNER" are unchanged ...
        }

    # --- NEW HELPER FUNCTION TO DETECT QUESTIONS ---
    def _is_a_question(self, text):
        """A simple heuristic to check if a message is a question."""
        text = text.lower().strip()
        # Check for question mark
        if text.endswith('?'):
            return True
        # Check for common question words at the start
        question_words = ['what', 'how', 'when', 'where', 'why', 'who', 'can', 'could', 'is', 'are', 'do', 'does', 'explain']
        if any(text.startswith(word) for word in question_words):
            return True
        return False

    def handle_all_text(self, message):
        # ... (Anti-spam, admin exemption, and scheduler checks are unchanged)

        if message.content_type != 'text':
            return
            
        text = message.text
        chat_id = message.chat.id

        # --- 1. Handle SPECIFIC keyword commands FIRST ---
        lower_text = text.lower().strip()
        if any(kw in lower_text for kw in ["ca", "contract", "address"]):
            # ... (implementation unchanged)
            return
        
        # ... (check for "how to buy", "who are you", "owner", "collab", etc.)
        # ... (all these specific checks remain the same)

        # --- 2. NEW: If it's a question, let the AI handle it ---
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
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text} # Use the original text for the AI
                    ],
                    model="llama3-8b-8192",
                )
                ai_response = chat_completion.choices[0].message.content
                self.bot.edit_message_text(ai_response, chat_id=chat_id, message_id=thinking_message.message_id)
            except Exception as e:
                logger.error(f"Error during AI response generation: {e}")
                if thinking_message: self.bot.delete_message(chat_id, thinking_message.message_id)
                self.bot.send_message(chat_id, random.choice(self.responses["FINAL_FALLBACK"]))
            return # Stop processing after AI responds

        # --- 3. If not a command or question, run the "Smart Interjection" logic ---
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
    
    # ... (All other functions like greet_new_members, send_scheduled_greeting, etc., are unchanged)
