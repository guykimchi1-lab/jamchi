import os
import time
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from cryptography.fernet import Fernet
from supabase import create_client

ALLOWED_USER_ID = int(os.environ["ALLOWED_USER_ID"])
BOT_TOKEN = os.environ["BOT_TOKEN"]
ENCRYPTION_KEY = os.environ["ENCRYPTION_KEY"].encode()
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

fernet = Fernet(ENCRYPTION_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_code(name: str) -> str | None:
    result = supabase.table("codes").select("code").eq("name", name).execute()
    if result.data:
        return fernet.decrypt(result.data[0]["code"].encode()).decode()
    return None


def set_code(name: str, code: str):
    encrypted = fernet.encrypt(code.encode()).decode()
    supabase.table("codes").upsert({"name": name, "code": encrypted}).execute()


def delete_code(name: str):
    supabase.table("codes").delete().eq("name", name).execute()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return

    text = update.message.text.strip()

    if text.startswith("add "):
        parts = text[4:].split(" ", 1)
        if len(parts) == 2:
            name, code = parts
            set_code(name, code)
            await update.message.reply_text(f"✅ שמרתי קוד עבור {name}")
        else:
            await update.message.reply_text("שימוש: add [שם] [קוד]")
        return

    if text.startswith("delete "):
        name = text[7:].strip()
        delete_code(name)
        await update.message.reply_text(f"🗑 מחקתי את {name}")
        return

    if text == "list":
        result = supabase.table("codes").select("name").execute()
        names = [r["name"] for r in result.data]
        await update.message.reply_text("\n".join(names) if names else "אין קודים שמורים")
        return

    code = get_code(text)
    if code:
        await update.message.reply_text(f"🔑 {code}")
    else:
        await update.message.reply_text(f"לא מצאתי קוד עבור {text}")


def main():
    time.sleep(5)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
