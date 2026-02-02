from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import subprocess
import os
from dotenv import load_dotenv

load_dotenv()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Ejecutando análisis...")
    script_path = os.path.join(os.path.dirname(__file__), "main.py")
    chat_id = str(update.effective_chat.id)
    subprocess.run(["python", script_path, chat_id])
    await update.message.reply_text("✅ Análisis completado.")

async def instruction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # information about the bot functionality
    await update.message.reply_text("Este bot ejecuta un análisis de quiniela y envía los resultados.")
    await update.message.reply_text("Para comenzar, usa el comando /start.")
    
TOKEN = os.getenv("TELEGRAM_TOKEN")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("init", instruction))
app.run_polling()
