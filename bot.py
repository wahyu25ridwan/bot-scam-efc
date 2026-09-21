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
TOKEN = os.getenv("TOKEN", "8780305562:AAFEFRL_c1QFUV7aOw2lZazFc1kdSdfXI8s")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", 6537343724))   # ID Grup Admin
PUBLIC_GROUP_ID = int(os.getenv("PUBLIC_GROUP_ID", -5326430759)) # ID Grup Publik
SAWERIA_URL = os.getenv("SAWERIA_URL", "https://saweria.co/Aryouridwan")
DB_FILE = "database.json"
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
        "Kirim foto screenshot bukti dengan *caption* atau ketik:\n"
        "<code>/report [Nama/Tag] | [Kronologi singkat]</code>\n\n"
        "📌 **Cara Cek Akun:**\n"
        "Ketik: <code>/check [Username / Tag CoC]</code>",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

# Perintah /report (Mendukung Teks dan Foto/Screenshot)
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        await update.message.reply_text("❌ Perintah /report hanya bisa dilakukan di dalam grup!")
        return

    message = update.message
    user = message.from_user
    
    # Ambil caption jika mengirim foto, atau ambil argumen teks jika mengetik biasa
    caption_text = message.caption if message.photo else " ".join(context.args)

    if not caption_text:
        await message.reply_text(
            "⚠️ Format salah!\nGunakan format: <code>/report [Nama/Tag] | [Kronologi]</code>\n"
            "(Atau sertakan *caption* tersebut jika mengirim screenshot).",
            parse_mode="HTML"
        )
        return

    photo_file_id = message.photo[-1].file_id if message.photo else None

    db = load_db()
    report_id = str(len(db) + 1001)

    # Simpan ke JSON dengan status "waiting_game" agar aman dari kedaluwarsa
    db[report_id] = {
        "report_id": report_id,
        "user_id": user.id,
        "username": user.username or user.first_name,
        "content": caption_text,
        "photo_id": photo_file_id,
        "status": "waiting_game"
    }
    save_db(db)

    # Tombol Pilihan Game
    keyboard = [
        [
            InlineKeyboardButton("⚽ eFootball", callback_data=f"game_efootball_{report_id}"),
            InlineKeyboardButton("🏰 Clash of Clans (CoC)", callback_data=f"game_coc_{report_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        f"🎮 **Pilih Kategori Game untuk Laporan ini:**\n\n"
        f"📝 <b>Keterangan:</b> {caption_text}\n"
        f"📸 <b>Foto Bukti:</b> {'Terlampir ✅' if photo_file_id else 'Tidak ada'}\n\n"
        f"<i>Silakan klik tombol game di bawah ini:</i>",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

# Perintah /check (Memanggil database dan bukti foto)
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

    for rid, data in db.items():
        if data["status"] == "approved":
            if query_text.lower() in data["content"].lower():
                found_reports.append(data)

    if found_reports:
        for rep in found_reports:
            result_text = (
                f"⚠️ **PERINGATAN! Akun / Tag `{query_text}` DITEMUKAN!** ⚠️\n\n"
                f"🎮 **Game:** {rep.get('game', 'Umum')}\n"
                f"🆔 **ID Laporan:** #{rep['report_id']}\n"
                f"📄 **Kronologi:**\n{rep['content']}\n\n"
                f"❌ *Sangat disarankan untuk TIDAK BERTRANSAKSI!*"
            )
            if rep.get("photo_id"):
                await update.message.reply_photo(photo=rep["photo_id"], caption=result_text, parse_mode="Markdown")
            else:
                await update.message.reply_text(result_text, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"✅ **AMAN!**\nTidak ada catatan scam terkait `{query_text}` yang terverifikasi dalam database kami.\n\n"
            "_Tetaplah waspada dan gunakan Rekber terpercaya saat bertransaksi!_",
            parse_mode="Markdown"
        )

# Handler Tombol Klik (Pilihan Game & Admin Approval)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    db = load_db()

    # 1. Pilihan Game oleh Pelapor
    if data.startswith("game_"):
        parts = data.split("_")
        game_type = parts[1]
        report_id = parts[2]

        if report_id not in db:
            await query.edit_message_text(text="⚠️ Sesi laporan tidak ditemukan. Silakan kirim ulang laporan.")
            return

        game_name = "eFootball" if game_type == "efootball" else "Clash of Clans (CoC)"
        report_data = db[report_id]

        report_data["game"] = game_name
        report_data["status"] = "pending"
        save_db(db)

        admin_message = (
            f"🚨 **LAPORAN BARU MASUK (PENDING)** 🚨\n\n"
            f"🎮 Game: {game_name}\n"
            f"🆔 ID Laporan: #{report_id}\n"
            f"👤 Pelapor: @{report_data['username']}\n\n"
            f"📄 **Keterangan:**\n{report_data['content']}"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Setujui & Publish", callback_data=f"approve_{report_id}"),
                InlineKeyboardButton("❌ Tolak", callback_data=f"reject_{report_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if report_data.get("photo_id"):
            await context.bot.send_photo(
                chat_id=ADMIN_CHAT_ID,
                photo=report_data["photo_id"],
                caption=admin_message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
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

    # 2. Keputusan Admin (Approve / Reject)
    action, report_id = data.split("_", 1)
    if report_id not in db:
        await query.edit_message_text(text="⚠️ Data laporan tidak ditemukan di database.")
        return

    report_data = db[report_id]

    if action == "approve":
        report_data["status"] = "approved"
        save_db(db)

        pub_text = (
            f"⚠️ **DAFTAR SCAMMER TERVERIFIKASI** ⚠️\n\n"
            f"🎮 **Game:** {report_data.get('game', 'Umum')}\n"
            f"👤 **Pelapor:** @{report_data['username']}\n\n"
            f"📄 **Kronologi:**\n{report_data['content']}"
        )

        if report_data.get("photo_id"):
            await context.bot.send_photo(
                chat_id=PUBLIC_GROUP_ID,
                photo=report_data["photo_id"],
                caption=pub_text,
                parse_mode="Markdown"
            )
        else:
            await context.bot.send_message(
                chat_id=PUBLIC_GROUP_ID,
                text=pub_text,
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
