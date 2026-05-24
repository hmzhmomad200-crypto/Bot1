from flask import Flask, request
import telebot
import threading
import os

from config import BOT_TOKEN, ADMIN_IDS, CALLBACK_SECRET
from database import (
    get_payment_by_address,
    mark_paid,
    get_available_item,
    mark_item_sold
)

from handlers.user import register_user_handlers
from handlers.admin import register_admin_handlers

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

register_user_handlers(bot)
register_admin_handlers(bot)


@app.route('/callback')
def callback():

    # التحقق من الـ secret
    secret = request.args.get('secret')
    if secret != CALLBACK_SECRET:
        print("Callback: secret غير صحيح")
        return "forbidden", 403

    txid = request.args.get('transaction_hash')
    address = request.args.get('input_address')
    value = request.args.get('value', 0)

    print(f"Callback received: address={address}, txid={txid}, value={value}")

    if not txid or not address:
        return "error", 400

    payment = get_payment_by_address(address)

    if not payment:
        print("Callback: عنوان غير موجود في DB")
        return "ok"

    pay_id, user_id, product_id, amount_usd, amount_ltc, addr, old_txid, paid, created_at = payment

    # تحويل من litoshi إلى LTC
    received_ltc = float(value) / 1e8

    # تحقق من المبلغ (هامش 1%)
    required_ltc = float(amount_ltc) * 0.99

    if received_ltc < required_ltc:
        bot.send_message(
            user_id,
            f"⚠️ *دفعة غير مكتملة*\n\n"
            f"💰 المطلوب: `{amount_ltc} LTC`\n"
            f"📥 المستلم: `{received_ltc:.8f} LTC`\n"
            f"❗ الفرق: `{round(float(amount_ltc) - received_ltc, 8)} LTC`\n\n"
            f"أرسل المبلغ الكامل لنفس العنوان لإكمال الطلب.",
            parse_mode="Markdown"
        )
        return "ok"

    # منع التكرار
    updated = mark_paid(txid, address)

    if updated == 0:
        print("Callback: طلب مدفوع مسبقاً")
        return "ok"

    # تسليم المنتج
    item = get_available_item(product_id)

    if item:
        item_id, content = item
        mark_item_sold(item_id, product_id)

        bot.send_message(
            user_id,
            f"✅ *تم استلام الدفع بنجاح!*\n\n"
            f"💵 المبلغ: `${amount_usd}`\n"
            f"🔄 دفعت: `{received_ltc:.8f} LTC`\n\n"
            f"🎁 *منتجك:*\n`{content}`\n\n"
            f"🔗 TXID:\n`{txid}`",
            parse_mode="Markdown"
        )

    else:
        bot.send_message(
            user_id,
            f"✅ تم استلام دفعتك `${amount_usd}`\n"
            f"⚠️ نفذ المخزون مؤقتاً، سيتم التواصل معك قريباً.\n"
            f"TXID: `{txid}`",
            parse_mode="Markdown"
        )

        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(
                    admin_id,
                    f"🚨 *تحذير: نفذ المخزون!*\n\n"
                    f"المستخدم `{user_id}` دفع `${amount_usd}` لكن المخزون فاضي.\n"
                    f"المنتج ID: `{product_id}`\n"
                    f"TXID: `{txid}`",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

    return "ok"


@app.route('/')
def index():
    return "🟢 Store bot is running"


if __name__ == '__main__':

    threading.Thread(
        target=bot.infinity_polling,
        daemon=True
    ).start()

    app.run(
        host='0.0.0.0',
        port=int(os.environ.get("PORT", 8080))
        )
