import os
import asyncio
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBSERVER_URL = os.getenv("WEBSERVER_URL", "http://localhost:8000")


# ─── Command Handlers ────────────────────────────────────────


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome message when bot is added or /start is used."""
    await update.message.reply_text(
        "Hi! I'm Planly — I help your group plan activities.\n\n"
        "Just chat normally and mention me when you want me to help "
        "organize something (dinner, movies, meetings, etc.).\n\n"
        "Commands:\n"
        "/help  — How to use Planly\n"
        "/link <email>  — Link your Telegram to your Planly account"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage instructions."""
    await update.message.reply_text(
        "How to use Planly:\n\n"
        "1. Add me to a group chat\n"
        "2. Chat about plans normally\n"
        '3. Mention me: "@planly_bot book dinner"\n'
        "4. I'll read recent messages, understand the plan, and help organize it\n\n"
        "I can:\n"
        "  - Create calendar events\n"
        "  - Search for restaurants\n"
        "  - Find cinema showtimes\n\n"
        "Use /link <email> to connect your Telegram to your Planly account."
    )


async def cmd_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Link Telegram user to Planly account."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /link your@email.com\n"
            "This connects your Telegram to your Planly account."
        )
        return

    email = context.args[0]
    user_id = update.effective_user.id
    username = update.effective_user.username or ""

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                f"{WEBSERVER_URL}/auth/link-telegram",
                json={
                    "email": email,
                    "telegram_id": user_id,
                    "telegram_username": username,
                },
            )

            if response.status_code == 200:
                await update.message.reply_text(
                    f"Linked! Your Telegram is now connected to {email}."
                )
            else:
                data = response.json()
                detail = data.get("detail", "Unknown error")
                await update.message.reply_text(f"Failed to link: {detail}")

        except httpx.RequestError as e:
            await update.message.reply_text(
                "Could not reach the Planly server. Please try again later."
            )
            print(f"Link error: {e}")


# ─── Message Handler ─────────────────────────────────────────


async def handle_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Forward all group text messages to the webserver."""
    message = update.message
    if not message or not message.text:
        return

    bot_username = context.bot.username or ""
    is_mention = f"@{bot_username}" in message.text

    payload = {
        "group_id": message.chat_id,
        "group_title": message.chat.title or "",
        "message_id": message.message_id,
        "user_id": message.from_user.id if message.from_user else 0,
        "username": message.from_user.username or "" if message.from_user else "",
        "first_name": message.from_user.first_name or "" if message.from_user else "",
        "last_name": message.from_user.last_name or "" if message.from_user else "",
        "text": message.text,
        "timestamp": message.date.isoformat(),
        "is_bot_mention": is_mention,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{WEBSERVER_URL}/telegram/webhook",
                json=payload,
            )

            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response_text")
                if response_text:
                    await message.reply_text(response_text)

        except httpx.RequestError as e:
            print(f"Error forwarding to webserver: {e}")
            # Don't reply with error to avoid spamming the group


# ─── Bot Setup ────────────────────────────────────────────────


async def post_init(application: Application) -> None:
    """Set bot commands after startup."""
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Welcome message"),
            BotCommand("help", "How to use Planly"),
            BotCommand("link", "Link Telegram to Planly account"),
        ]
    )


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: Set TELEGRAM_BOT_TOKEN in .env")
        print("Get one from @BotFather on Telegram")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("link", cmd_link))

    # Message handler — all text messages in groups
    app.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_message)
    )

    print("Planly Telegram bot started")
    print(f"Forwarding to: {WEBSERVER_URL}")
    print("Add the bot to a group and start chatting")

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
