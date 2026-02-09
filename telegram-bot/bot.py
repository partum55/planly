import os
from collections import deque
from telegram import (
    Update,
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    constants,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
WEBSERVER_URL = os.getenv("WEBSERVER_URL", "http://localhost:8000").strip()
SERVICE_TOKEN = os.getenv("SERVICE_TOKEN", "").strip()

BUFFER_MAX = 50
BUTTON_LABEL_MAX = 60

# ─── In-Memory State ────────────────────────────────────────

message_buffers: dict[int, deque] = {}  # chat_id -> last N messages
conversations: dict[int, str] = {}  # chat_id -> conversation_id
action_states: dict[int, dict] = {}  # chat_id -> {message_id, actions, selected, conversation_id}


# ─── Helpers ────────────────────────────────────────────────


def _headers() -> dict[str, str]:
    """Build auth headers for backend calls."""
    if SERVICE_TOKEN:
        return {"Authorization": f"Bearer {SERVICE_TOKEN}"}
    return {}


def _truncate(text: str, limit: int = BUTTON_LABEL_MAX) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "\u2026"


def _is_mention(message, bot_username: str) -> bool:
    """Check if the bot is @mentioned in the message."""
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                mentioned = message.text[entity.offset : entity.offset + entity.length]
                if mentioned.lower() == f"@{bot_username.lower()}":
                    return True
    # Fallback: plain text check
    if f"@{bot_username}" in (message.text or ""):
        return True
    return False


def _build_action_keyboard(actions: list[dict], selected: set) -> InlineKeyboardMarkup:
    """Build inline keyboard for action cards."""
    rows = []
    for action in actions:
        aid = action["action_id"]
        check = "\u2705" if aid in selected else "\u2b1c"
        label = _truncate(action["description"])
        rows.append([InlineKeyboardButton(f"{check} {label}", callback_data=f"toggle:{aid}")])
    rows.append([
        InlineKeyboardButton("Confirm", callback_data="confirm"),
        InlineKeyboardButton("Cancel", callback_data="cancel"),
    ])
    return InlineKeyboardMarkup(rows)


# ─── Command Handlers ───────────────────────────────────────


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! I'm Planly \u2014 I help your group plan activities.\n\n"
        "Just chat normally. When you need me, mention me:\n"
        '  @planly_bot book dinner tomorrow\n\n'
        "I'll read recent messages, understand the context, and propose actions.\n\n"
        "Commands:\n"
        "/help  \u2014 How to use Planly\n"
        "/link <CODE>  \u2014 Link Telegram to your Planly account\n"
        "/reset  \u2014 Clear conversation state"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "How to use Planly:\n\n"
        "1. Add me to a group chat\n"
        "2. Chat about plans normally \u2014 I remember recent messages\n"
        "3. Mention me when you want action:\n"
        '   @planly_bot organize dinner\n'
        "4. I'll propose actions \u2014 tap to select, then Confirm\n\n"
        "I can create calendar events, search restaurants, find showtimes, and more.\n\n"
        "/link <CODE> \u2014 Connect Telegram to your Planly account\n"
        "  (get a code from the Planly desktop app or web settings)\n"
        "/reset \u2014 Clear conversation state for this group"
    )


async def cmd_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Usage: /link <CODE>\n\n"
            "To get a code:\n"
            "1. Log in to the Planly desktop app or web\n"
            "2. Go to Settings \u2192 Link Telegram\n"
            "3. Copy the 6-character code\n"
            "4. Come back here and type /link YOUR_CODE"
        )
        return

    code = context.args[0].upper().strip()
    user_id = update.effective_user.id
    username = update.effective_user.username or ""

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                f"{WEBSERVER_URL}/auth/link-telegram",
                headers=_headers(),
                json={
                    "code": code,
                    "telegram_id": user_id,
                    "telegram_username": username,
                },
            )
            if response.status_code == 200:
                await update.message.reply_text(
                    "\u2705 Linked! Your Telegram is now connected to your Planly account."
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


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    message_buffers.pop(chat_id, None)
    conversations.pop(chat_id, None)
    action_states.pop(chat_id, None)
    await update.message.reply_text("Conversation state cleared for this group.")


# ─── Message Handler ────────────────────────────────────────


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.text:
        return

    chat_id = message.chat_id
    bot_username = context.bot.username or ""

    # Always buffer the message
    if chat_id not in message_buffers:
        message_buffers[chat_id] = deque(maxlen=BUFFER_MAX)

    message_buffers[chat_id].append({
        "username": message.from_user.first_name or message.from_user.username or "Unknown"
        if message.from_user
        else "Unknown",
        "text": message.text,
        "timestamp": message.date.strftime("%-I:%M %p") if message.date else "",
    })

    # Only respond on @mention
    if not _is_mention(message, bot_username):
        return

    # Strip the @mention from the prompt
    user_prompt = message.text.replace(f"@{bot_username}", "").strip()
    if not user_prompt:
        user_prompt = "What should we plan?"

    # Send typing indicator
    await context.bot.send_chat_action(chat_id, constants.ChatAction.TYPING)

    # Build buffered messages list
    buffered = list(message_buffers.get(chat_id, []))

    # Call /agent/process
    payload = {
        "source": "telegram",
        "conversation_id": conversations.get(chat_id),
        "user_prompt": user_prompt,
        "context": {
            "messages": buffered,
            "screenshot_metadata": {
                "ocr_confidence": 100.0,
                "raw_text": "\n".join(f"{m['username']}: {m['text']}" for m in buffered),
            },
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{WEBSERVER_URL}/agent/process",
                headers=_headers(),
                json=payload,
            )

            if response.status_code != 200:
                detail = "Unknown error"
                try:
                    detail = response.json().get("detail", detail)
                except Exception:
                    pass
                await message.reply_text(f"Backend error: {detail}")
                return

            data = response.json()
        except httpx.RequestError as e:
            await message.reply_text(
                f"Could not reach the Planly server.\n"
                f"URL: {WEBSERVER_URL}/agent/process\n"
                f"Error: {type(e).__name__}: {e}"
            )
            print(f"Agent process error: {e}")
            return

    # Track conversation
    conv_id = data.get("conversation_id")
    if conv_id:
        conversations[chat_id] = conv_id

    # Render response blocks
    blocks = data.get("blocks", [])
    await _render_blocks(message, chat_id, blocks, conv_id)


# ─── Block Rendering ────────────────────────────────────────


async def _render_blocks(message, chat_id: int, blocks: list, conversation_id: str | None) -> None:
    for block in blocks:
        block_type = block.get("type")

        if block_type == "text":
            content = block.get("content", "")
            if content:
                await message.reply_text(content)

        elif block_type == "action_cards":
            actions = block.get("actions", [])
            if actions:
                await _render_action_cards(message, chat_id, actions, conversation_id)

        elif block_type == "calendar_picker":
            prompt = block.get("prompt", "Please provide a date.")
            await message.reply_text(f"\U0001f4c5 {prompt}\n\nMention me again with a date, e.g. @planly_bot February 10")

        elif block_type == "time_picker":
            prompt = block.get("prompt", "Please provide a time.")
            await message.reply_text(f"\u23f0 {prompt}\n\nMention me again with a time, e.g. @planly_bot 7pm")

        elif block_type == "error":
            err = block.get("message", "Something went wrong.")
            await message.reply_text(f"\u26a0\ufe0f {err}")


async def _render_action_cards(
    message, chat_id: int, actions: list[dict], conversation_id: str | None
) -> None:
    selected: set = set()
    keyboard = _build_action_keyboard(actions, selected)

    sent = await message.reply_text("Select the actions to confirm:", reply_markup=keyboard)

    action_states[chat_id] = {
        "message_id": sent.message_id,
        "actions": actions,
        "selected": selected,
        "conversation_id": conversation_id,
    }


# ─── Callback Query Handler ─────────────────────────────────


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    chat_id = query.message.chat_id
    data = query.data

    state = action_states.get(chat_id)
    if not state or state["message_id"] != query.message.message_id:
        await query.answer("This action card has expired.", show_alert=True)
        return

    if data.startswith("toggle:"):
        action_id = data[7:]
        selected: set = state["selected"]
        if action_id in selected:
            selected.discard(action_id)
        else:
            selected.add(action_id)

        keyboard = _build_action_keyboard(state["actions"], selected)
        await query.message.edit_reply_markup(reply_markup=keyboard)
        await query.answer()

    elif data == "confirm":
        selected = state["selected"]
        if not selected:
            await query.answer("Select at least one action first.", show_alert=True)
            return

        await query.answer()

        # Remove keyboard while processing
        await query.message.edit_text("Processing\u2026")

        conv_id = state.get("conversation_id")
        action_ids = list(selected)

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{WEBSERVER_URL}/agent/confirm-actions",
                    headers=_headers(),
                    json={
                        "conversation_id": conv_id,
                        "action_ids": action_ids,
                    },
                )

                if response.status_code == 200:
                    result = response.json()
                    formatted = result.get("formatted_response", "")

                    if formatted:
                        await query.message.edit_text(f"\u2705 {formatted}")
                    else:
                        # Build summary from individual results
                        results = result.get("results", [])
                        lines = []
                        for r in results:
                            status = "\u2705" if r.get("success") else "\u274c"
                            tool = r.get("tool", "action")
                            lines.append(f"{status} {tool}")
                        summary = "\n".join(lines) if lines else "Done."
                        await query.message.edit_text(summary)
                else:
                    detail = "Unknown error"
                    try:
                        detail = response.json().get("detail", detail)
                    except Exception:
                        pass
                    await query.message.edit_text(f"\u274c Error: {detail}")

            except httpx.RequestError as e:
                await query.message.edit_text("\u274c Could not reach the Planly server.")
                print(f"Confirm error: {e}")

        # Clean up state
        action_states.pop(chat_id, None)

    elif data == "cancel":
        await query.answer("Cancelled.")
        await query.message.edit_text("Cancelled.")
        action_states.pop(chat_id, None)


# ─── Bot Setup ──────────────────────────────────────────────


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([
        BotCommand("start", "Welcome message"),
        BotCommand("help", "How to use Planly"),
        BotCommand("link", "Link Telegram to Planly account"),
        BotCommand("reset", "Clear conversation state"),
    ])


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
    app.add_handler(CommandHandler("reset", cmd_reset))

    # Callback query handler (inline keyboard buttons)
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Message handler — all text messages in groups (must be last)
    app.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_group_message)
    )

    print("Planly Telegram bot started")
    print(f"Backend: {WEBSERVER_URL}")
    print(f"Auth: {'SERVICE_TOKEN set' if SERVICE_TOKEN else 'no auth'}")

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
