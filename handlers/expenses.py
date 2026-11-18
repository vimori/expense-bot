from __future__ import annotations

from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from categories import CATEGORIES
from db import Database
from filters import not_command
from keyboards import amount as amount_kb
from keyboards import cancel, categories as categories_kb, main_menu, saved
from texts import ADD_TITLE, WELCOME
from ui import edit, fmt_money, fmt_time, parse_amount, show

router = Router(name="expenses")


class AddExpense(StatesGroup):
    amount = State()


def _category_title(code: str) -> str:
    emoji, label = CATEGORIES.get(code, ("✨", code))
    return f"{emoji} <b>{label}</b>"


def _amount_screen(code: str, has_presets: bool) -> str:
    hint = (
        "Выберите автоматизацию или введите свою сумму."
        if has_presets
        else "Введите сумму траты."
    )
    return f"{_category_title(code)}\n\n{hint}"


def _saved_screen(expense: dict) -> str:
    code = str(expense["category"])
    emoji, label = CATEGORIES.get(code, ("✨", code))
    title = f"{emoji} {label}"
    if expense.get("note"):
        title += f" · {escape(str(expense['note']))}"
    return (
        "✅ <b>Записано</b>\n\n"
        f"{title}\n"
        f"<b>{fmt_money(int(expense['amount']))}</b> · "
        f"{fmt_time(str(expense['created_at']))}"
    )


async def _delete_message(message: Message) -> None:
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "add")
async def add_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.answer()
    await show(call, ADD_TITLE, categories_kb("c", back="menu", back_text="‹ Меню"))


@router.callback_query(F.data.startswith("c:"))
async def pick_category(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    db_user_id: int,
) -> None:
    code = call.data.split(":", 1)[1]
    if code not in CATEGORIES:
        await call.answer("Неизвестная категория", show_alert=True)
        return

    presets = await db.presets(db_user_id, code)
    await state.clear()
    await call.answer()

    if not presets:
        await state.set_state(AddExpense.amount)
        await state.update_data(
            category=code,
            prompt_id=call.message.message_id if call.message else None,
        )
        await show(
            call,
            f"{_category_title(code)}\n\n"
            "Отправьте сумму сообщением.\n"
            "<i>Например: 250 или 12,50</i>",
            cancel("menu"),
        )
        return

    await show(call, _amount_screen(code, True), amount_kb(code, presets))


@router.callback_query(F.data == "back:cats")
async def back_to_categories(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.answer()
    await show(call, ADD_TITLE, categories_kb("c", back="menu", back_text="‹ Меню"))


@router.callback_query(F.data.startswith("amt:"))
async def custom_amount(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    db_user_id: int,
) -> None:
    code = call.data.split(":", 1)[1]
    if code not in CATEGORIES:
        await call.answer()
        return

    presets = await db.presets(db_user_id, code)
    await state.set_state(AddExpense.amount)
    await state.update_data(
        category=code,
        prompt_id=call.message.message_id if call.message else None,
    )
    await call.answer()
    await show(
        call,
        f"{_category_title(code)}\n\n"
        "Отправьте сумму сообщением.\n"
        "<i>Например: 250 или 12,50</i>",
        cancel("menu"),
    )


@router.message(AddExpense.amount, not_command)
async def amount_entered(
    message: Message,
    state: FSMContext,
    db: Database,
    db_user_id: int,
    bot: Bot,
) -> None:
    data = await state.get_data()
    code = str(data.get("category") or "")
    prompt_id = data.get("prompt_id") or message.message_id

    if code not in CATEGORIES:
        await state.clear()
        await message.answer(WELCOME, reply_markup=main_menu())
        return

    amount = parse_amount(message.text or "")
    if amount is None:
        await edit(
            bot,
            message.chat.id,
            int(prompt_id),
            f"{_category_title(code)}\n\n"
            "Не похоже на сумму. Отправьте число, например 250 или 12,50.",
            cancel("menu"),
        )
        return

    expense_id = await db.add_expense(db_user_id, code, amount)
    expense = await db.get_expense(db_user_id, expense_id)
    await state.clear()
    await _delete_message(message)

    if expense is None:
        return
    await edit(
        bot,
        message.chat.id,
        int(prompt_id),
        _saved_screen(expense),
        saved(expense_id),
    )


@router.callback_query(F.data.startswith("p:"))
async def preset_clicked(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    db_user_id: int,
) -> None:
    try:
        preset_id = int(call.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await call.answer()
        return

    preset = await db.get_preset(db_user_id, preset_id)
    if preset is None:
        await call.answer("Автоматизация не найдена", show_alert=True)
        return

    expense_id = await db.add_expense(
        db_user_id,
        str(preset["category"]),
        int(preset["amount"]),
        str(preset["name"]),
    )
    expense = await db.get_expense(db_user_id, expense_id)
    await state.clear()
    await call.answer()

    if expense is None:
        return
    await show(call, _saved_screen(expense), saved(expense_id))


@router.callback_query(F.data.startswith("more:"))
async def repeat_expense(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    db_user_id: int,
) -> None:
    try:
        expense_id = int(call.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await call.answer()
        return

    original = await db.get_expense(db_user_id, expense_id)
    if original is None:
        await call.answer("Трата не найдена", show_alert=True)
        return

    new_id = await db.add_expense(
        db_user_id,
        str(original["category"]),
        int(original["amount"]),
        original.get("note"),
    )
    expense = await db.get_expense(db_user_id, new_id)
    await state.clear()
    await call.answer()

    if expense is None:
        return
    await show(call, _saved_screen(expense), saved(new_id))


@router.callback_query(F.data.startswith("undo:"))
async def undo_expense(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    db_user_id: int,
) -> None:
    try:
        expense_id = int(call.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await call.answer()
        return

    deleted = await db.delete_expense(db_user_id, expense_id)
    await state.clear()
    await call.answer("Удалено" if deleted else "Уже удалено")
    await show(call, WELCOME, main_menu())
