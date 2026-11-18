from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import categories as categories_kb, main_menu, periods
from texts import ADD_TITLE, ANALYSIS_TITLE, WELCOME
from ui import show

router = Router(name="common")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME, reply_markup=main_menu())


@router.message(Command("menu"))
async def menu_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню 👇", reply_markup=main_menu())


@router.message(Command("add"))
async def add_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        ADD_TITLE,
        reply_markup=categories_kb("c", back="menu", back_text="‹ Меню"),
    )


@router.message(Command("stats"))
async def stats_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ANALYSIS_TITLE, reply_markup=periods())


@router.callback_query(F.data == "menu")
async def menu_callback(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.answer()
    await show(call, WELCOME, main_menu())


@router.callback_query()
async def unknown_callback(call: CallbackQuery) -> None:
    await call.answer()


@router.message()
async def fallback_message(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Воспользуйтесь меню 👇", reply_markup=main_menu())
