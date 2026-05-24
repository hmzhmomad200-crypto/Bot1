import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import LTC_WALLET, BASE_URL, API_URL
from database import (
    get_all_products,
    get_product,
    get_stock_count,
    add_payment,
    get_user_orders
)

from utils.price import usd_to_ltc


def register_user_handlers(bot: telebot.TeleBot):

    @bot.message_handler(commands=['start'])
    def start(message):

        markup = InlineKeyboardMarkup()

        markup.add(
            InlineKeyboardButton(
                "🛍 المتجر",
                callback_data="shop"
            )
        )

        markup.add(
            InlineKeyboardButton(
                "📦 طلباتي",
                callback_data="my_orders"
            )
        )

        bot.send_message(
            message.chat.id,
            "👋 *أهلاً بك في المتجر*\n\nاختر من القائمة أدناه:",
            parse_mode="Markdown",
            reply_markup=markup
        )

    @bot.message_handler(commands=['shop'])
    def shop_cmd(message):
        show_shop(message.chat.id)

    @bot.callback_query_handler(func=lambda c: c.data == "shop")
    def shop_cb(call):

        bot.answer_callback_query(call.id)

        show_shop(call.message.chat.id)

    def show_shop(chat_id):

        products = get_all_products()

        if not products:
            bot.send_message(
                chat_id,
                "❌ لا توجد منتجات متاحة حالياً."
            )
            return

        markup = InlineKeyboardMarkup()

        for p in products:

            pid, name, desc, price_usd, stock, active = p

            cnt = get_stock_count(pid)

            if cnt > 0:
                label = f"🛒 {name} — ${price_usd}"
            else:
                label = f"❌ {name} (نفذ)"

            markup.add(
                InlineKeyboardButton(
                    label,
                    callback_data=f"product_{pid}"
                )
            )

        bot.send_message(
            chat_id,
            "🛍 *المتجر*\n\nاختر المنتج:",
            parse_mode="Markdown",
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("product_"))
    def product_detail(call):

        bot.answer_callback_query(call.id)

        product_id = int(call.data.split("_")[1])

        p = get_product(product_id)

        if not p:
            bot.send_message(
                call.message.chat.id,
                "❌ المنتج غير موجود."
            )
            return

        pid, name, desc, price_usd, stock, active = p

        cnt = get_stock_count(pid)

        ltc_price = usd_to_ltc(price_usd)

        text = (
            f"📦 *{name}*\n\n"
            f"📝 {desc or 'لا يوجد وصف'}\n\n"
            f"💵 السعر: `${price_usd}`\n"
            f"🔄 يعادل: `{ltc_price} LTC`\n"
            f"📊 المخزون: `{cnt}` متاح"
        )

        markup = InlineKeyboardMarkup()

        if cnt > 0:
            markup.add(
                InlineKeyboardButton(
                    "💳 اشتري الآن",
                    callback_data=f"buy_{pid}"
                )
            )

        markup.add(
            InlineKeyboardButton(
                "🔙 رجوع",
                callback_data="shop"
            )
        )

        bot.send_message(
            call.message.chat.id,
            text,
            parse_mode="Markdown",
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
    def buy_product(call):

        bot.answer_callback_query(
            call.id,
            "⏳ جاري إنشاء الفاتورة..."
        )

        product_id = int(call.data.split("_")[1])

        p = get_product(product_id)

        if not p:
            bot.send_message(
                call.message.chat.id,
                "❌ المنتج غير موجود."
            )
            return

        pid, name, desc, price_usd, stock, active = p

        if get_stock_count(pid) == 0:
            bot.send_message(
                call.message.chat.id,
                "❌ هذا المنتج نفد من المخزون."
            )
            return

        # حساب سعر LTC
        ltc_amount = usd_to_ltc(price_usd)

        try:

            # إنشاء عنوان دفع من LitePay
            r = requests.get(
                API_URL,
                params={
                    "method": "litecoin",
                    "address": LTC_WALLET,
                    "callback": f"https://{BASE_URL}/callback"
                },
                timeout=15
            )

            print("LitePay Response:", r.status_code, r.text)

            data = r.json()

            print("LitePay Keys:", list(data.keys()))

            # عنوان الدفع المؤقت
            pay_address = data.get("payment_address") or data.get("address")

            if not pay_address:
                raise Exception(f"لم يتم استلام عنوان الدفع: {data}")

        except requests.exceptions.Timeout:

            bot.send_message(
                call.message.chat.id,
                "❌ انتهت مهلة الاتصال، حاول مجدداً."
            )
            return

        except Exception as e:

            print("LitePay Error:", e)

            bot.send_message(
                call.message.chat.id,
                "❌ خطأ في إنشاء الفاتورة، حاول لاحقاً."
            )
            return

        # حفظ الطلب
        add_payment(
            call.message.chat.id,
            pid,
            price_usd,
            ltc_amount,
            pay_address
        )

        text = (
            f"💰 *فاتورة Litecoin*\n\n"
            f"🛒 المنتج: *{name}*\n"
            f"💵 السعر: `${price_usd}`\n"
            f"🔄 المبلغ المطلوب: `{ltc_amount} LTC`\n\n"
            f"📬 عنوان الدفع:\n`{pay_address}`\n\n"
            f"⚠️ أرسل المبلغ بالكامل لنفس العنوان.\n"
            f"✅ بعد تأكيد الدفع سيتم التسليم تلقائياً."
        )

        bot.send_message(
            call.message.chat.id,
            text,
            parse_mode="Markdown"
        )

    @bot.message_handler(commands=['orders'])
    def orders_cmd(message):
        show_orders(message.chat.id)

    @bot.callback_query_handler(func=lambda c: c.data == "my_orders")
    def orders_cb(call):

        bot.answer_callback_query(call.id)

        show_orders(call.message.chat.id)

    def show_orders(chat_id):

        orders = get_user_orders(chat_id)

        if not orders:
            bot.send_message(
                chat_id,
                "📭 لا توجد طلبات سابقة."
            )
            return

        text = "📦 *آخر طلباتك:*\n\n"

        for o in orders:

            oid, uid, pid, amt_usd, amt_ltc, address, txid, paid, created_at, pname = o

            status = "✅ مدفوع" if paid else "⏳ انتظار"

            text += f"• {pname} — ${amt_usd} — {status}\n"

        bot.send_message(
            chat_id,
            text,
            parse_mode="Markdown"
        )
