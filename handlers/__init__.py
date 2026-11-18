from __future__ import annotations

from aiogram import Router

from . import analysis, automation, common, expenses

ROUTERS: tuple[Router, ...] = (
    expenses.router,
    automation.router,
    analysis.router,
    common.router,
)
