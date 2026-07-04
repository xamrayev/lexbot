"""HR Assistant Telegram Bot — the free entry point of the LegalOS funnel.

Bridges Telegram chats to the LegalOS backend HR agent. Each Telegram user is
lazily provisioned a personal Free-tier account, so backend plan limits
(messages/day) apply automatically.
"""

import asyncio
import logging
import os
import secrets

import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("legalos.tgbot")

BACKEND_URL = os.environ.get("LEGALOS_BACKEND_URL", "http://backend:8000")
BOT_TOKEN = os.environ["LEGALOS_TELEGRAM_BOT_TOKEN"]

# chat_id -> {"token": str, "conversation_id": str | None}
_sessions: dict[int, dict] = {}

WELCOME = (
    "Ассалому алайкум! Я — HR Assistant, бесплатный AI-помощник по трудовому "
    "законодательству Республики Узбекистан.\n\n"
    "Спросите меня, например:\n"
    "• Сколько дней ежегодного отпуска положено?\n"
    "• Как оформить прием на работу?\n"
    "• Как подготовить приказ об увольнении?\n\n"
    "Я отвечаю со ссылками на статьи Трудового кодекса (Lex.uz)."
)


async def _ensure_session(chat_id: int) -> dict:
    if chat_id in _sessions:
        return _sessions[chat_id]
    email = f"tg-{chat_id}@telegram.legalos.uz"
    password = secrets.token_urlsafe(24)
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=60.0) as client:
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": f"Telegram {chat_id}"},
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]
    _sessions[chat_id] = {"token": token, "conversation_id": None}
    return _sessions[chat_id]


async def _ask_backend(chat_id: int, text: str) -> str:
    session = await _ensure_session(chat_id)
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=120.0) as client:
        resp = await client.post(
            "/api/v1/chat",
            json={"message": text, "agent": "hr", "conversation_id": session["conversation_id"]},
            headers={"Authorization": f"Bearer {session['token']}"},
        )
        if resp.status_code == 429:
            return "Дневной лимит бесплатных сообщений исчерпан. Попробуйте завтра или перейдите на HR Pro."
        resp.raise_for_status()
        data = resp.json()
    session["conversation_id"] = data["conversation_id"]
    answer = data["content"]
    links = [s["url"] for s in data.get("sources", []) if s.get("url")]
    if links:
        answer += "\n\nИсточники:\n" + "\n".join(f"• {u}" for u in dict.fromkeys(links))
    return answer


dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    await message.answer(WELCOME)


@dp.message()
async def on_message(message: types.Message) -> None:
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовый вопрос.")
        return
    await message.bot.send_chat_action(message.chat.id, "typing")
    try:
        answer = await _ask_backend(message.chat.id, message.text)
    except Exception:
        log.exception("backend call failed")
        answer = "Сервис временно недоступен. Попробуйте позже."
    await message.answer(answer)


async def main() -> None:
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
