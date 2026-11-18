from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from db import Database
from keyboards import periods
from stats import PERIODS, collect, render
from texts import ANALYSIS_TITLE
from ui import show

router = Router(name="analysis")


@router.callback_query(F.data == "an")
async def analysis_menu(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.answer()
    await show(call, ANALYSIS_TITLE, periods())


@router.callback_query(F.data.startswith("an:"))
async def show_report(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    db_user_id: int,
) -> None:
    key = call.data.split(":", 1)[1]
    if key not in PERIODS:
        await call.answer()
        return

    await state.clear()
    await call.answer()
    report = await collect(db, db_user_id, key)
    await show(call, render(report), periods())
