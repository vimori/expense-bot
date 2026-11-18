from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent

from config import BOT_TOKEN, DB_PATH
from db import Database
from handlers import ROUTERS
from middlewares import UserMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
)
logger = logging.getLogger("budget-bot")


async def main() -> None:
    if not BOT_TOKEN:
        logger.error(
            "Не задан BOT_TOKEN. Скопируйте .env.example в .env и вставьте токен от @BotFather."
        )
        sys.exit(1)

    db = Database(DB_PATH)
    await db.init()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher["db"] = db

    user_middleware = UserMiddleware(db)
    dispatcher.message.middleware(user_middleware)
    dispatcher.callback_query.middleware(user_middleware)

    for router in ROUTERS:
        dispatcher.include_router(router)

    @dispatcher.errors()
    async def on_error(event: ErrorEvent) -> bool:
        logger.exception("Ошибка при обработке апдейта", exc_info=event.exception)
        return True

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Главное меню"),
            BotCommand(command="add", description="Новая трата"),
            BotCommand(command="stats", description="Анализ трат"),
        ]
    )
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Бот запущен. База: %s", DB_PATH)
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
