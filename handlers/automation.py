from __future__ import annotations

from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from categories import CATEGORIES
from db import Database
from filters import not_command
from keyboards import automations, cancel, categories as categories_kb, confirm_delete
from texts import AUTOMATION_EMPTY, AUTOMATION_LIST
from ui import edit, fmt_money, parse_amount, show

router = Router(name="automation")

MAX_PRESETS = 20
MAX_NAME_LENGTH = 24


class AddAutomation(StatesGroup):
    category = State()
    name = State()
    amount = State()


def _screen(presets: list[dict]) -> tuple[str, InlineKeyboardMarkup]:
    text = AUTOMATION_LIST if presets else AUTOMATION_EMPTY
    return text, automations(presets)


async def _delete_message(message: Message) -> None:
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


async def _render(call: CallbackQuery, state: FSMContext, db: Database, user_id: int) -> None:
    presets = await db.presets(user_id)
    text, keyboard = _screen(presets)
    await show(call, text, keyboard)
    await state.clear()


@router.callback_query(F.data == "auto")
async def list_automations(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    db_user_id: int,
) -> None:
    await call.answer()
    await _render(call, state, db, db_user_id)


@router.callback_query(F.data == "auto:add")
async def add_automation(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    db_user_id: int,
) -> None:
    existing = await db.presets(db_user_id)
    if len(existing) >= MAX_PRESETS:
        await call.answer(
            f"Максимум {MAX_PRESETS} автоматизаций. Удалите лишнюю.",
            show_alert=True,
        )
        return

    await state.set_state(AddAutomation.category)
    await state.update_data(
        prompt_id=call.message.message_id if call.message else None,
    )
    await call.answer()
    await show(
        call,
        "⚙️ <b>Новая автоматизация</b>\n\nДля какой категории?",
        categories_kb("ac", back="auto"),
    )


@router.callback_query(AddAutomation.category, F.data.startswith("ac:"))
async def pick_automation_category(
    call: CallbackQuery,
    state: FSMContext,
) -> None:
    code = call.data.split(":", 1)[1]
    if code not in CATEGORIES:
        await call.answer()
        return

    await state.update_data(category=code)
    await state.set_state(AddAutomation.name)
    emoji, label = CATEGORIES[code]
    await call.answer()
    await show(
        call,
        "⚙️ <b>Новая автоматизация</b>\n\n"
        f"{emoji} {label}\n\n"
        "Как назвать? Например, «Метро».",
        cancel("auto"),
    )


@router.message(AddAutomation.name, not_command)
async def automation_name(
    message: Message,
    state: FSMContext,
    bot: Bot,
) -> None:
    data = await state.get_data()
    prompt_id = int(data.get("prompt_id") or message.message_id)
    code = str(data.get("category") or "")
    emoji, label = CATEGORIES.get(code, ("✨", code))
    name = (message.text or "").strip()

    await _delete_message(message)

    if not name or len(name) > MAX_NAME_LENGTH:
        await edit(
            bot,
            message.chat.id,
            prompt_id,
            "⚙️ <b>Новая автоматизация</b>\n\n"
            f"{emoji} {label}\n\n"
            f"Название — от 1 до {MAX_NAME_LENGTH} символов. Попробуйте ещё раз.",
            cancel("auto"),
        )
        return

    await state.update_data(name=name)
    await state.set_state(AddAutomation.amount)
    await edit(
        bot,
        message.chat.id,
        prompt_id,
        "⚙️ <b>Новая автоматизация</b>\n\n"
        f"{emoji} {label} · {escape(name)}\n\n"
        "Введите сумму. Например: 35 или 1,05.",
        cancel("auto"),
    )


@router.message(AddAutomation.amount, not_command)
async def automation_amount(
    message: Message,
    state: FSMContext,
    db: Database,
    db_user_id: int,
    bot: Bot,
) -> None:
    data = await state.get_data()
    prompt_id = int(data.get("prompt_id") or message.message_id)
    code = str(data.get("category") or "")
    name = str(data.get("name") or "")
    emoji, label = CATEGORIES.get(code, ("✨", code))
    amount = parse_amount(message.text or "")

    await _delete_message(message)

    if amount is None:
        await edit(
            bot,
            message.chat.id,
            prompt_id,
            "⚙️ <b>Новая автоматизация</b>\n\n"
            f"{emoji} {label} · {escape(name)}\n\n"
            "Не похоже на сумму. Введите число, например 35 или 1,05.",
            cancel("auto"),
        )
        return

    await db.add_preset(db_user_id, code, name, amount)
    await state.clear()

    presets = await db.presets(db_user_id)
    text, keyboard = _screen(presets)
    await edit(bot, message.chat.id, prompt_id, text, keyboard)


@router.callback_query(F.data.startswith("auto:del:"))
async def confirm_remove(
    call: CallbackQuery,
    db: Database,
    db_user_id: int,
) -> None:
    try:
        preset_id = int(call.data.split(":", 2)[2])
    except (IndexError, ValueError):
        await call.answer()
        return

    preset = await db.get_preset(db_user_id, preset_id)
    if preset is None:
        await call.answer("Уже удалено")
        return

    await call.answer()
    await show(
        call,
        "Удалить автоматизацию?\n\n"
        f"⚡ <b>{escape(str(preset['name']))}</b> · "
        f"{fmt_money(int(preset['amount']))}",
        confirm_delete(preset_id),
    )


@router.callback_query(F.data.startswith("auto:delok:"))
async def remove_automation(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    db_user_id: int,
) -> None:
    try:
        preset_id = int(call.data.split(":", 2)[2])
    except (IndexError, ValueError):
        await call.answer()
        return

    deleted = await db.delete_preset(db_user_id, preset_id)
    await call.answer("Удалено" if deleted else "Уже удалено")
    await _render(call, state, db, db_user_id)
