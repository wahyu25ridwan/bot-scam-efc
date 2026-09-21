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
# Mengambil data dari Environment Render/Server atau isi langsung
TOKEN = os.getenv("TOKEN", "8780305562:AAHB3vQ_z0OPLbTHJ_dI58RSKchz84co2z4")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", -6537343724))   # Sesuaikan ID Grup Admin kamu
PUBLIC_GROUP_ID = int(os.getenv("PUBLIC_GROUP_ID", -5326430759)) # Sesuaikan ID Grup Publik kamu
SAWERIA_URL = os.getenv("SAWERIA_URL", "https://saweria.co/Aryouridwan")
DB_FILE = "database.json"
# ==================================================

# Fungsi untuk Memuat Database dari File JSON
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

# Fungsi untuk Menyimpan Database ke File JSON
def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Perintah /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("☕ Dukung Hosting Bot (Saweria)", url=SAWERIA_URL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 **Bot Pelaporan & Pengecekan Scammer (eFootball & CoC)**\n\n"
        "📌 **Perintah yang tersedia:**\n"
        "1️⃣ Lapor Scammer:\n"
        "<code>/report [Game] | [Nama/Tag] | [Kronologi]</code>\n\n"
        "2️⃣ Cek Keamanan Akun/Tag:\n"
        "<code>/check [Username / Tag CoC]</code>\n\n"
        "💡 *Bot ini gratis digunakan. Jika ingin membantu biaya operasional/hosting bot, kamu bisa berdonasi melalui tombol di bawah ini ya! Terima kasih!* 🙏",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

# Perintah /report (Melaporkan Scammer)
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text_args = " ".join(context.args)
    
    if not text_args:
        await update.message.reply_text(
            "⚠️ Format salah!\nGunakan format: <code>/report [Game] | [Nama/Tag] | [Kronologi]</code>",
            parse_mode="HTML"
        )
        return

    db = load_db()
    report_id = str(len(db) + 1001)  # ID Unik Laporan (1001, 1002, dst)

    # Simpan ke JSON dengan status pending
    db[report_id] = {
        "report_id": report_id,
        "user_id": user.id,
        "username": user.username or user.first_name,
        "content": text_args,
        "status": "pending"
    }
    save_db(db)

    # Format pesan untuk dikirim ke Grup Admin
    admin_message = (
        f"🚨 **LAPORAN BARU MASUK (PENDING)** 🚨\n\n"
        f"ID Laporan: #{report_id}\n"
        f"Pelapor: @{user.username or user.first_name} (ID: {user.id})\n\n"
        f"Detail:\n{text_args}"
    )

    # Tombol Approval Admin
    keyboard = [
        [
            InlineKeyboardButton("✅ Setujui & Publish", callback_data=f"approve_{report_id}"),
            InlineKeyboardButton("❌ Tolak", callback_data=f"reject_{report_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

# Kirim ke Grup Admin
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID, 
        text=admin_message, 
        reply_markup=reply_markup,
        parse_mode="Markdown"  # Diperbaiki dari parse_mongo
    )

    await update.message.reply_text("✅ Laporanmu berhasil dikirim dan sedang menunggu **approval admin**.")

# Perintah /check (Mengecek apakah akun/tag aman)
async def check_scammer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_text = " ".join(context.args).strip()
    
    if not query_text:
        await update.message.reply_text(
            "⚠️ Format salah!\nGunakan format: <code>/check [Username Telegram / Tag CoC / Nama]</code>",
            parse_mode="HTML"
        )
        return

    db = load_db()
    found_reports = []

    # Cari hanya pada laporan yang statusnya 'approved'
    for rid, data in db.items():
        if data["status"] == "approved":
            if query_text.lower() in data["content"].lower():
                found_reports.append(data)

    if found_reports:
        result_msg = f"⚠️ **PERINGATAN! Akun / Tag `{query_text}` DITEMUKAN dalam database Scam!** ⚠️\n\n"
        for rep in found_reports:
            result_msg += f"• Laporan #{rep['report_id']}:\n{rep['content']}\n\n"
        result_msg += "❌ *Sangat disarankan untuk TIDAK BERTRANSAKSI dengan akun/tag ini!*"
        await update.message.reply_text(result_msg, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"✅ **AMAN!**\nTidak ada catatan scam terkait `{query_text}` yang terverifikasi dalam database kami.\n\n"
            "_Tetaplah waspada dan gunakan Rekber terpercaya saat bertransaksi!_",
            parse_mode="Markdown"  # Diperbaiki dari parse_Mode (M besar)
        )

# Handler untuk Tombol Klik Admin (Approve / Reject)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    action, report_id = data.split("_")
    
    db = load_db()
    if report_id not in db:
        await query.edit_message_text(text="⚠️ Data laporan tidak ditemukan di database.")
        return

    report_data = db[report_id]

    if action == "approve":
        report_data["status"] = "approved"
        save_db(db)

        # Publish ke Grup Publik
        await context.bot.send_message(
            chat_id=PUBLIC_GROUP_ID,
            text=f"⚠️ **DAFTAR SCAMMER TERVERIFIKASI** ⚠️\n\n"
                 f"Pelapor: @{report_data['username']}\n"
                 f"Detail:\n{report_data['content']}",
            parse_mode="Markdown"
        )
        
        # Edit pesan di grup admin
        await query.edit_message_text(text=f"{query.message.text}\n\n✅ **STATUS: DISETUJUI & DIPUBLISH KE GRUP**")
        
        try:
            await context.bot.send_message(
                chat_id=report_data["user_id"], 
                text=f"🎉 Laporan kamu (#{report_id}) telah **disetujui** dan dipublikasikan oleh admin."
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
    # Inisialisasi Bot menggunakan ApplicationBuilder (Standar v20+)
    app = ApplicationBuilder().token(TOKEN).build()

    # Daftarkan Command & Callback Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("check", check_scammer))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot Telegram berhasil dijalankan...")
    app.run_polling()

if __name__ == "__main__":
    main()
