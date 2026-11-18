from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, LinkPreviewOptions

from config import TIMEZONE

TZ = ZoneInfo(TIMEZONE)
LINK_PREVIEW_OFF = LinkPreviewOptions(is_disabled=True)

MONTHS: tuple[str, ...] = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def now_local() -> datetime:
    return datetime.now(TZ)


def utc_iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(TZ)


def fmt_money(kopecks: int) -> str:
    """105 -> «1,05 ₽», 200 -> «2 ₽», 1234567 -> «12 345,67 ₽»."""
    kopecks = int(kopecks)
    sign = "−" if kopecks < 0 else ""
    rubles, cents = divmod(abs(kopecks), 100)
    body = f"{rubles:,}".replace(",", " ")
    if cents:
        return f"{sign}{body},{cents:02d} ₽"
    return f"{sign}{body} ₽"


def fmt_time(value: str) -> str:
    return from_iso(value).strftime("%H:%M")


def plural(number: int, one: str, few: str, many: str) -> str:
    number = abs(int(number)) % 100
    if 11 <= number <= 19:
        return many
    number %= 10
    if number == 1:
        return one
    if 2 <= number <= 4:
        return few
    return many


def bar(share: float, width: int = 10) -> str:
    filled = round(share * width)
    filled = max(0, min(width, filled))
    if share > 0:
        filled = max(1, filled)
    return "▰" * filled + "▱" * (width - filled)


def percent(part: int, total: int) -> str:
    if total <= 0:
        return "0%"
    value = part * 100 / total
    if value < 1:
        return "<1%"
    return f"{round(value)}%"


def date_range(start: datetime, end_exclusive: datetime) -> str:
    last = end_exclusive - timedelta(days=1)
    if start.date() == last.date():
        return f"{start.day} {MONTHS[start.month - 1]}"
    if start.year != last.year:
        return (
            f"{start.day} {MONTHS[start.month - 1]} {start.year} — "
            f"{last.day} {MONTHS[last.month - 1]} {last.year}"
        )
    if start.month == last.month:
        return f"{start.day} — {last.day} {MONTHS[last.month - 1]}"
    return f"{start.day} {MONTHS[start.month - 1]} — {last.day} {MONTHS[last.month - 1]}"


def parse_amount(text: str) -> int | None:
    """Разбирает «250», «12,50», «1.05 ₽», «2 руб» в копейки."""
    value = (
        (text or "")
        .strip()
        .lower()
        .replace("\u00a0", "")
        .replace("\u202f", "")
        .replace(" ", "")
    )
    value = re.sub(r"(₽|рублей|рубля|рубль|руб\.?|р\.?|rub\.?)$", "", value)
    value = value.replace(",", ".")
    if not re.fullmatch(r"\d{1,8}(?:\.\d{1,2})?", value):
        return None
    whole, _, fraction = value.partition(".")
    amount = int(whole) * 100 + int((fraction or "0").ljust(2, "0"))
    if amount <= 0 or amount > 100_000_000:
        return None
    return amount


async def show(
    call: CallbackQuery,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
) -> None:
    """Аккуратно заменяет текущий экран, не оставляя мусора в чате."""
    if call.message is None:
        return
    try:
        await call.message.edit_text(
            text,
            reply_markup=keyboard,
            link_preview_options=LINK_PREVIEW_OFF,
        )
    except TelegramBadRequest as error:
        if "message is not modified" in str(error).lower():
            return
        await call.message.answer(
            text,
            reply_markup=keyboard,
            link_preview_options=LINK_PREVIEW_OFF,
        )


async def edit(
    bot: Bot,
    chat_id: int,
    message_id: int,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
) -> None:
    """Редактирует экран по id — используется после ввода текста."""
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=keyboard,
            link_preview_options=LINK_PREVIEW_OFF,
        )
    except TelegramBadRequest as error:
        if "message is not modified" in str(error).lower():
            return
        await bot.send_message(
            chat_id,
            text,
            reply_markup=keyboard,
            link_preview_options=LINK_PREVIEW_OFF,
        )
