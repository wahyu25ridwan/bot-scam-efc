import json
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# ================= CONFIGURATION =================
TOKEN = os.getenv("TOKEN", "8780305562:AAHB3vQ_z0OPLbTHJ_dI58RSKchz84co2z4")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", 6537343724))   # ID Grup Admin
PUBLIC_GROUP_ID = int(os.getenv("PUBLIC_GROUP_ID", -5326430759)) # ID Grup Publik
SAWERIA_URL = os.getenv("SAWERIA_URL", "https://saweria.co/Aryouridwan")
DB_FILE = "database.json"

REPORT_TEMP = {}
# ==================================================

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Perintah /start (Hanya di Grup)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        await update.message.reply_text("❌ Bot ini hanya dapat digunakan di dalam grup!")
        return

    keyboard = [
        [InlineKeyboardButton("☕ Dukung Hosting Bot (Saweria)", url=SAWERIA_URL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 **Bot Pelaporan & Pengecekan Scammer (eFootball & CoC)**\n\n"
        "📌 **Cara Lapor Scammer:**\n"
        "Ketik: <code>/report [Nama/Tag] | [Bukti & Kronologi]</code>\n"
        "*(Contoh: `/report @badguy | Bukti chat: https://ibb.co/xxx Minta DP lalu kabur`)*\n\n"
        "📌 **Cara Cek Akun:**\n"
        "Ketik: <code>/check [Username / Tag CoC]</code>",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

# Perintah /report
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        await update.message.reply_text("❌ Perintah /report hanya bisa dilakukan di dalam grup!")
        return

    user = update.message.from_user
    text_args = " ".join(context.args)
    
    if not text_args:
        await update.message.reply_text(
            "⚠️ Format salah!\nGunakan format: <code>/report [Nama/Tag] | [Bukti & Kronologi]</code>",
            parse_mode="HTML"
        )
        return

    REPORT_TEMP[user.id] = text_args

    keyboard = [
        [
            InlineKeyboardButton("⚽ eFootball", callback_data="game_efootball"),
            InlineKeyboardButton("🏰 Clash of Clans (CoC)", callback_data="game_coc")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🎮 **Pilih Kategori Game untuk Laporan ini:**\n\n"
        f"📝 <b>Bukti & Detail:</b> {text_args}\n\n"
        f"<i>Silakan klik salah satu tombol game di bawah ini:</i>",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

# Perintah /check (Memanggil bukti dari database.json)
async def check_scammer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        await update.message.reply_text("❌ Perintah /check hanya bisa dilakukan di dalam grup!")
        return

    query_text = " ".join(context.args).strip()
    
    if not query_text:
        await update.message.reply_text(
            "⚠️ Format salah!\nGunakan format: <code>/check [Username Telegram / Tag CoC / Nama]</code>",
            parse_mode="HTML"
        )
        return

    db = load_db()
    found_reports = []

    # Mencari data yang statusnya sudah 'approved'
    for rid, data in db.items():
        if data["status"] == "approved":
            if query_text.lower() in data["content"].lower():
                found_reports.append(data)

    if found_reports:
        result_msg = f"⚠️ **PERINGATAN! Akun / Tag `{query_text}` DITEMUKAN dalam database Scam!** ⚠️\n\n"
        for rep in found_reports:
            result_msg += f"• **Game:** {rep['game']}\n"
            result_msg += f"• **ID Laporan:** #{rep['report_id']}\n"
            result_msg += f"• **Bukti & Kronologi:**\n{rep['content']}\n\n"
        result_msg += "❌ *Sangat disarankan untuk TIDAK BERTRANSAKSI dengan akun/tag ini!*"
        await update.message.reply_text(result_msg, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"✅ **AMAN!**\nTidak ada catatan scam terkait `{query_text}` yang terverifikasi dalam database kami.\n\n"
            "_Tetaplah waspada dan gunakan Rekber terpercaya saat bertransaksi!_",
            parse_mode="Markdown"
        )

# Handler Tombol Klik
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = query.from_user

    if data.startswith("game_"):
        game_name = "eFootball" if data == "game_efootball" else "Clash of Clans (CoC)"
        
        if user.id not in REPORT_TEMP:
            await query.edit_message_text(text="⚠️ Sesi laporan kedaluwarsa. Silakan ketik ulang /report.")
            return

        text_args = REPORT_TEMP.pop(user.id)
        db = load_db()
        report_id = str(len(db) + 1001)

        # Bukti disimpan ke dalam database.json
        db[report_id] = {
            "report_id": report_id,
            "game": game_name,
            "user_id": user.id,
            "username": user.username or user.first_name,
            "content": text_args,
            "status": "pending"
        }
        save_db(db)

        admin_message = (
            f"🚨 **LAPORAN BARU MASUK (PENDING)** 🚨\n\n"
            f"🎮 Game: {game_name}\n"
            f"🆔 ID Laporan: #{report_id}\n"
            f"👤 Pelapor: @{user.username or user.first_name}\n\n"
            f"📄 **Bukti & Detail:**\n{text_args}"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Setujui & Publish", callback_data=f"approve_{report_id}"),
                InlineKeyboardButton("❌ Tolak", callback_data=f"reject_{report_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID, 
            text=admin_message, 
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        await query.edit_message_text(
            text=f"✅ Laporan **{game_name}** kamu (#{report_id}) berhasil dikirim dan menunggu **approval admin**."
        )
        return

    action, report_id = data.split("_", 1)
    db = load_db()
    if report_id not in db:
        await query.edit_message_text(text="⚠️ Data laporan tidak ditemukan di database.")
        return

    report_data = db[report_id]

    if action == "approve":
        report_data["status"] = "approved"
        save_db(db)

        # Publish ke Grup Publik beserta bukti penipuannya
        await context.bot.send_message(
            chat_id=PUBLIC_GROUP_ID,
            text=f"⚠️ **DAFTAR SCAMMER TERVERIFIKASI** ⚠️\n\n"
                 f"🎮 **Game:** {report_data['game']}\n"
                 f"👤 **Pelapor:** @{report_data['username']}\n\n"
                 f"📄 **Bukti & Detail:**\n{report_data['content']}",
            parse_mode="Markdown"
        )
        
        await query.edit_message_text(text=f"{query.message.text}\n\n✅ **STATUS: DISETUJUI & DIPUBLISH**")
        
        try:
            await context.bot.send_message(
                chat_id=report_data["user_id"], 
                text=f"🎉 Laporan kamu (#{report_id}) telah **disetujui** dan dipublikasikan."
            )
        except Exception:
            pass

    elif action == "reject":
        report_data["status"] = "rejected"
        save_db(db)

        await query.edit_message_text(text=f"{query.message.text}\n\n❌ **STATUS: DITOLAK**")
        
        try:
            await context.bot.send_message(
                chat_id=report_data["user_id"], 
                text=f"❌ Maaf, laporan kamu (#{report_id}) **ditolak** oleh admin."
            )
        except Exception:
            pass

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("check", check_scammer))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot Telegram berhasil dijalankan...")
    app.run_polling()

if __name__ == "__main__":
    main()
