import requests
import ssl
import socket
import asyncio
import certifi
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

TOKEN = "" # telegram bot token

CHECK_INTERVAL = 600
domains = {}

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

def check_ssl(domain):
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
        return True
    except Exception:
        return False

async def check_domain(domain, chat_id, context):
    while True:
        try:
            response = requests.get(domain, timeout=10, verify=certifi.where())
            status = response.status_code

            if 200 <= status < 400:
                message = f"✅ {domain} çalışıyor (Durum Kodu: {status})"
            elif status == 403:  
                ssl_valid = check_ssl(domain.replace("https://", "").replace("http://", ""))

                if ssl_valid:
                    message = f"⚠️ {domain} botları engelliyor (403) ama yasaklanmamış."
                else:
                    message = f"🚫 {domain} WAF olabilir. (403 + SSL Hatası)"
            else:
                message = f"⚠️ {domain} çalışmıyor (Durum Kodu: {status})"

        except requests.RequestException:
            ssl_valid = check_ssl(domain.replace("https://", "").replace("http://", ""))
            if not ssl_valid:
                message = f"❌ {domain} tamamen yasaklanmış olabilir! SSL sertifikasına erişilemiyor."
            else:
                message = f"❌ {domain} çökmüş olabilir ama yasaklanmamış."

        message = message.replace("https://", "<https://").replace("http://", "<http://") + ">"
        await context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True)

        await asyncio.sleep(CHECK_INTERVAL)  
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Merhaba! Domain durumunu takip etmek için bana bir URL gönder. 😊")

async def track_domain(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    domain = update.message.text.strip()

    if not domain.startswith("http"):
        await update.message.reply_text("⚠️ Lütfen geçerli bir URL gir (http veya https ile başlamalı).")
        return

    if domain in domains:
        await update.message.reply_text(f"⚠️ {domain} zaten takip ediliyor!")
        return

    await update.message.reply_text(f"🕵️‍♂️ <{domain} takip edilmeye başlandı.>")

    asyncio.create_task(check_domain(domain, chat_id, context))
    domains[domain] = True 

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_domain))

    app.run_polling()

if __name__ == "__main__":
    main()