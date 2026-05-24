import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_IDS
from database import (
    add_product, get_all_products, get_product,
    delete_product, update_product_price,
    add_stock, get_stock_count, get_stats
)
from utils.price import usd_to_ltc

admin_state = {}

def is_admin(user_id):
    return user_id in ADMIN_IDS

def register_admin_handlers(bot: telebot.TeleBot):

    @bot.message_handler(commands=['admin'])
    def admin_panel(message):
        if not is_admin(message.from_user.id):
            return
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("➕ إضافة منتج",  callback_data="adm_add_product"),
            InlineKeyboardButton("📦 المنتجات",     callback_data="adm_list_products"),
            InlineKeyboardButton("📥 إضافة مخزون", callback_data="adm_add_stock_menu"),
            InlineKeyboardButton("📊 الإحصائيات",  callback_data="adm_stats"),
        )
        bot.send_message(message.chat.id, "🔧 *لوحة الأدمن*", parse_mode="Markdown", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data == "adm_stats")
    def show_stats(call):
        if not is_admin(call.from_user.id):
            return
        bot.answer_callback_query(call.id)
        s = get_stats()
        text = (
            f"📊 *إحصائيات المتجر*\n\n"
            f"🛒 إجمالي الطلبات: `{s['total_orders']}`\n"
            f"💵 إجمالي الإيرادات: `${s['total_usd']}`\n"
            f"🔄 يعادل: `{s['total_ltc']} LTC`\n"
            f"👥 المستخدمين: `{s['total_users']}`\n"
            f"⏳ فواتير معلقة: `{s['pending']}`"
        )
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda c: c.data == "adm_add_product")
    def adm_add_product(call):
        if not is_admin(call.from_user.id):
            return
        bot.answer_callback_query(call.id)
        admin_state[call.from_user.id] = {"step": "add_product_name"}
        bot.send_message(call.message.chat.id, "📝 أرسل *اسم المنتج:*", parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda c: c.data == "adm_list_products")
    def adm_list_products(call):
        if not is_admin(call.from_user.id):
            return
        bot.answer_callback_query(call.id)
        products = get_all_products()
        if not products:
            bot.send_message(call.message.chat.id, "❌ لا توجد منتجات.")
            return
        markup = InlineKeyboardMarkup()
        for p in products:
            pid, name, desc, price_usd, stock, active = p
            cnt = get_stock_count(pid)
            markup.add(InlineKeyboardButton(
                f"📦 {name} | ${price_usd} | مخزون: {cnt}",
                callback_data=f"adm_product_{pid}"
            ))
        bot.send_message(call.message.chat.id, "📦 *قائمة المنتجات:*", parse_mode="Markdown", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("adm_product_"))
    def adm_product_detail(call):
        if not is_admin(call.from_user.id):
            return
        bot.answer_callback_query(call.id)
        pid = int(call.data.split("_")[2])
        p = get_product(pid)
        if not p:
            bot.send_message(call.message.chat.id, "❌ المنتج غير موجود.")
            return
        _, name, desc, price_usd, stock, active = p
        cnt = get_stock_count(pid)
        ltc = usd_to_ltc(price_usd)
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("➕ إضافة مخزون", callback_data=f"adm_stock_{pid}"),
            InlineKeyboardButton("✏️ تعديل السعر",  callback_data=f"adm_price_{pid}"),
            InlineKeyboardButton("🗑 حذف المنتج",   callback_data=f"adm_del_{pid}"),
            InlineKeyboardButton("🔙 رجوع",         callback_data="adm_list_products"),
        )
        text = (
            f"📦 *{name}*\n"
            f"📝 {desc or '-'}\n"
            f"💵 السعر: `${price_usd}`\n"
            f"🔄 يعادل: `{ltc} LTC`\n"
            f"📊 المخزون: `{cnt}`"
        )
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("adm_del_"))
    def adm_delete(call):
        if not is_admin(call.from_user.id):
            return
        bot.answer_callback_query(call.id)
        pid = int(call.data.split("_")[2])
        delete_product(pid)
        bot.send_message(call.message.chat.id, "✅ تم حذف المنتج.")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("adm_price_"))
    def adm_change_price(call):
        if not is_admin(call.from_user.id):
            return
        bot.answer_callback_query(call.id)
        pid = int(call.data.split("_")[2])
        admin_state[call.from_user.id] = {"step": "change_price", "pid": pid}
        bot.send_message(call.message.chat.id, "💵 أرسل السعر الجديد بالدولار ($):")

    @bot.callback_query_handler(func=lambda c: c.data == "adm_add_stock_menu")
    def adm_stock_menu(call):
        if not is_admin(call.from_user.id):
            return
        bot.answer_callback_query(call.id)
        products = get_all_products()
        if not products:
            bot.send_message(call.message.chat.id, "❌ لا توجد منتجات.")
            return
        markup = InlineKeyboardMarkup()
        for p in products:
            pid, name, _, _, _, _ = p
            markup.add(InlineKeyboardButton(f"📦 {name}", callback_data=f"adm_stock_{pid}"))
        bot.send_message(call.message.chat.id, "اختر المنتج لإضافة مخزون:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("adm_stock_"))
    def adm_add_stock(call):
        if not is_admin(call.from_user.id):
            return
        bot.answer_callback_query(call.id)
        pid = int(call.data.split("_")[2])
        admin_state[call.from_user.id] = {"step": "add_stock", "pid": pid}
        bot.send_message(
            call.message.chat.id,
            "📥 أرسل المحتوى (حساب/باسورد)\nكل عنصر في سطر مستقل:"
        )

    @bot.message_handler(func=lambda m: m.from_user.id in admin_state)
    def handle_admin_input(message):
        if not is_admin(message.from_user.id):
            return
        uid   = message.from_user.id
        state = admin_state.get(uid, {})
        step  = state.get("step")

        if step == "add_product_name":
            admin_state[uid]["name"] = message.text.strip()
            admin_state[uid]["step"] = "add_product_desc"
            bot.send_message(message.chat.id, "📝 أرسل *وصف المنتج* (أو /skip للتخطي):", parse_mode="Markdown")

        elif step == "add_product_desc":
            desc = "" if message.text.strip() == "/skip" else message.text.strip()
            admin_state[uid]["desc"] = desc
            admin_state[uid]["step"] = "add_product_price"
            bot.send_message(message.chat.id, "💵 أرسل *السعر بالدولار* مثال: `1` أو `0.75`:", parse_mode="Markdown")

        elif step == "add_product_price":
            try:
                price = float(message.text.strip().replace("$", ""))
                if price <= 0:
                    raise ValueError
            except ValueError:
                bot.send_message(message.chat.id, "❌ سعر غير صحيح، أرسل رقماً موجباً مثال: 1.5")
                return
            name = admin_state[uid]["name"]
            desc = admin_state[uid]["desc"]
            pid  = add_product(name, desc, price)
            ltc  = usd_to_ltc(price)
            del admin_state[uid]
            bot.send_message(
                message.chat.id,
                f"✅ تم إضافة المنتج *{name}*\n"
                f"💵 السعر: `${price}` = `{ltc} LTC`\n"
                f"ID: `{pid}`",
                parse_mode="Markdown"
            )

        elif step == "change_price":
            try:
                price = float(message.text.strip().replace("$", ""))
                if price <= 0:
                    raise ValueError
            except ValueError:
                bot.send_message(message.chat.id, "❌ سعر غير صحيح.")
                return
            pid = state["pid"]
            update_product_price(pid, price)
            ltc = usd_to_ltc(price)
            del admin_state[uid]
            bot.send_message(
                message.chat.id,
                f"✅ تم تحديث السعر إلى `${price}` = `{ltc} LTC`",
                parse_mode="Markdown"
            )

        elif step == "add_stock":
            pid   = state["pid"]
            items = [line.strip() for line in message.text.strip().splitlines() if line.strip()]
            if not items:
                bot.send_message(message.chat.id, "❌ لا يوجد محتوى.")
                return
            for item in items:
                add_stock(pid, item)
            del admin_state[uid]
            p     = get_product(pid)
            pname = p[1] if p else "؟"
            total = get_stock_count(pid)
            bot.send_message(
                message.chat.id,
                f"✅ تم إضافة *{len(items)}* عنصر إلى *{pname}*\n"
                f"📊 إجمالي المخزون الآن: `{total}`",
                parse_mode="Markdown"
            )
