import os
import pandas as pd
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from services.analyzer import analyze_dataframe
from services.report_builder import build_report

DOWNLOADS_DIR = "downloads"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

BASE_URL = os.getenv("BASE_URL", "http://localhost:8501")


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    document = message.document

    if not document:
        await message.reply_text("❗ أرسل ملف CSV أو Excel.")
        return

    file_name = document.file_name or "file"
    ext = Path(file_name).suffix.lower()

    if ext not in [".csv", ".xlsx", ".xls"]:
        await message.reply_text("❗ الصيغ المدعومة: CSV, XLSX, XLS فقط.")
        return

    # ── Download file ──────────────────────────────────────────────────────────
    status_msg = await message.reply_text("⏳ جاري تحميل الملف...")

    local_path = os.path.join(DOWNLOADS_DIR, document.file_id + ext)
    tg_file = await context.bot.get_file(document.file_id)
    await tg_file.download_to_drive(local_path)

    # ── Parse ──────────────────────────────────────────────────────────────────
    try:
        if ext == ".csv":
            df = pd.read_csv(local_path, encoding="utf-8-sig")
        else:
            df = pd.read_excel(local_path)
    except Exception as e:
        await status_msg.edit_text(f"❌ تعذّر قراءة الملف: {e}")
        return

    if df.empty:
        await status_msg.edit_text("❌ الملف فارغ.")
        return

    # ── Analyze ────────────────────────────────────────────────────────────────
    await status_msg.edit_text("🤖 جاري التحليل بالذكاء الاصطناعي...")

    try:
        analysis = await analyze_dataframe(df, file_name)
    except Exception as e:
        await status_msg.edit_text(f"❌ خطأ في التحليل: {e}")
        return

    # ── Build JSON report ──────────────────────────────────────────────────────
    await status_msg.edit_text("📊 جاري بناء التقرير...")

    try:
        report_path = build_report(file_name, df, analysis)
    except Exception as e:
        await status_msg.edit_text(f"❌ خطأ في بناء التقرير: {e}")
        return

    report_filename = Path(report_path).name
    dashboard_url = f"{BASE_URL.rstrip('/')}/?report={report_filename}"

    # ── Send result ────────────────────────────────────────────────────────────
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 فتح الداشبورد", url=dashboard_url)]
    ])

    rows = len(df)
    cols = len(df.columns)
    insights = analysis.get("insights", "")
    charts_count = len(analysis.get("charts", []))

    text = (
        f"✅ *تم التحليل بنجاح!*\n\n"
        f"📁 *الملف:* `{file_name}`\n"
        f"📋 *الصفوف:* {rows:,} &nbsp;|&nbsp; *الأعمدة:* {cols}\n"
        f"📉 *الرسوم البيانية:* {charts_count}\n\n"
    )
    if insights:
        text += f"💡 *تحليل AI:*\n{insights}\n\n"

    text += f"👇 افتح الداشبورد التفاعلي:"

    await status_msg.delete()
    await message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
