from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, filters, ContextTypes
)
import datetime
import asyncio
import json
import os

TOKEN = "8020222241:AAGSO3ya3BckHIx1KXvHcTm_AGO4-B7aGec"
OWNER_ID = 8567061059

DATA_FILE = "data.json"

# -----------------------
# โหลด/บันทึกข้อมูล
# -----------------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "data": {},
        "settings": {
            "summary_time": "23:00",
            "auto_reset": True,
            "deposit_text": "✅ ฝาก {amount:,} บาท",
            "withdraw_text": "🔻 ถอน {amount:,} บาท"
        }
    }

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)

store = load_data()

# -----------------------
# เช็คสิทธิ์
# -----------------------
def is_owner(user_id):
    return user_id == OWNER_ID

# -----------------------
# ฝาก/ถอน
# -----------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_owner(user_id):
        return

    text = update.message.text
    today = str(datetime.date.today())

    if today not in store["data"]:
        store["data"][today] = {"deposit": 0, "withdraw": 0}

    if text.startswith("+"):
        amount = int(text[1:])
        store["data"][today]["deposit"] += amount
        save_data()
        await update.message.reply_text(
            store["settings"]["deposit_text"].format(amount=amount)
        )

    elif text.startswith("-"):
        amount = int(text[1:])
        store["data"][today]["withdraw"] += amount
        save_data()
        await update.message.reply_text(
            store["settings"]["withdraw_text"].format(amount=amount)
        )

# -----------------------
# สรุปยอด
# -----------------------
async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_owner(user_id):
        return

    today = str(datetime.date.today())

    if today in store["data"]:
        deposit = store["data"][today]["deposit"]
        withdraw = store["data"][today]["withdraw"]
        profit = deposit - withdraw

        await update.message.reply_text(
            f"📊 สรุปวันนี้\n"
            f"ฝาก: {deposit:,}\n"
            f"ถอน: {withdraw:,}\n"
            f"คงเหลือ: {profit:,}"
        )
    else:
        await update.message.reply_text("ยังไม่มียอดวันนี้")

# -----------------------
# ตั้งเวลาแจ้งเตือน
# -----------------------
async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.message.from_user.id):
        return

    if len(context.args) != 1:
        await update.message.reply_text("ใช้แบบนี้ /settime 22:30")
        return

    store["settings"]["summary_time"] = context.args[0]
    save_data()
    await update.message.reply_text("ตั้งเวลาเรียบร้อย")

# -----------------------
# เปิด/ปิด รีเซ็ต
# -----------------------
async def toggle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.message.from_user.id):
        return

    store["settings"]["auto_reset"] = not store["settings"]["auto_reset"]
    save_data()
    status = "เปิด" if store["settings"]["auto_reset"] else "ปิด"
    await update.message.reply_text(f"รีเซ็ตอัตโนมัติ: {status}")

# -----------------------
# แก้ข้อความ
# -----------------------
async def set_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.message.from_user.id):
        return

    if len(context.args) < 2:
        await update.message.reply_text("ใช้แบบนี้ /settext deposit ข้อความใหม่")
        return

    key = context.args[0]
    new_text = " ".join(context.args[1:])

    if key == "deposit":
        store["settings"]["deposit_text"] = new_text
    elif key == "withdraw":
        store["settings"]["withdraw_text"] = new_text
    else:
        await update.message.reply_text("ใช้ได้แค่ deposit หรือ withdraw")
        return

    save_data()
    await update.message.reply_text("แก้ข้อความเรียบร้อย")

# -----------------------
# ระบบแจ้งเตือนอัตโนมัติ
# -----------------------
async def scheduler(app):
    while True:
        now = datetime.datetime.now().strftime("%H:%M")
        if now == store["settings"]["summary_time"]:
            today = str(datetime.date.today())

            if today in store["data"]:
                deposit = store["data"][today]["deposit"]
                withdraw = store["data"][today]["withdraw"]
                profit = deposit - withdraw

                await app.bot.send_message(
                    chat_id=OWNER_ID,
                    text=f"📊 สรุปอัตโนมัติ\nฝาก: {deposit:,}\nถอน: {withdraw:,}\nคงเหลือ: {profit:,}"
                )

                if store["settings"]["auto_reset"]:
                    store["data"][today] = {"deposit": 0, "withdraw": 0}
                    save_data()

        await asyncio.sleep(60)

# -----------------------
# เริ่มระบบ
# -----------------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("summary", summary))
app.add_handler(CommandHandler("settime", set_time))
app.add_handler(CommandHandler("reset", toggle_reset))
app.add_handler(CommandHandler("settext", set_text))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.job_queue.run_once(lambda ctx: asyncio.create_task(scheduler(app)), 0)

print("บอทกำลังทำงาน...")
app.run_polling()
