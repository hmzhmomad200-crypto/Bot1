import telebot
from config import BOT_TOKEN
from handlers.user import register_user_handlers
from handlers.admin import register_admin_handlers

bot = telebot.TeleBot(BOT_TOKEN)

register_user_handlers(bot)
register_admin_handlers(bot)

print("🤖 Bot started...")
bot.infinity_polling()
