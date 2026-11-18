from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from db import Database


class UserMiddleware(BaseMiddleware):
    """Добавляет в каждый обработчик id пользователя из нашей базы."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is not None and not user.is_bot:
            data["db_user_id"] = await self.db.ensure_user(user.id)
        return await handler(event, data)
