from __future__ import annotations

from aiogram.types import Message


def not_command(message: Message) -> bool:
    """Пропускает любой контент, кроме команд: команды должны работать всегда."""
    return not (message.text or "").startswith("/")
