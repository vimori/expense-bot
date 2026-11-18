from __future__ import annotations

from aiogram.types import InlineKeyboardButton as Button, InlineKeyboardMarkup as Keyboard

from categories import CATEGORIES, CATEGORY_ORDER
from ui import fmt_money


def main_menu() -> Keyboard:
    return Keyboard(
        inline_keyboard=[
            [Button(text="💸 Новая трата", callback_data="add")],
            [Button(text="📊 Анализ трат", callback_data="an")],
            [Button(text="⚙️ Автоматизации", callback_data="auto")],
        ]
    )


def categories(prefix: str, back: str, back_text: str = "‹ Назад") -> Keyboard:
    buttons = [
        Button(
            text=f"{CATEGORIES[code][0]} {CATEGORIES[code][1]}",
            callback_data=f"{prefix}:{code}",
        )
        for code in CATEGORY_ORDER
    ]
    rows = [buttons[index : index + 2] for index in range(0, len(buttons), 2)]
    rows.append([Button(text=back_text, callback_data=back)])
    return Keyboard(inline_keyboard=rows)


def amount(category: str, presets: list[dict]) -> Keyboard:
    rows = [
        [
            Button(
                text=f"⚡ {preset['name']} · {fmt_money(preset['amount'])}",
                callback_data=f"p:{preset['id']}",
            )
        ]
        for preset in presets
    ]
    rows.append([Button(text="✏️ Своя сумма", callback_data=f"amt:{category}")])
    rows.append(
        [
            Button(text="‹ Назад", callback_data="back:cats"),
            Button(text="‹ Меню", callback_data="menu"),
        ]
    )
    return Keyboard(inline_keyboard=rows)


def saved(expense_id: int) -> Keyboard:
    return Keyboard(
        inline_keyboard=[
            [
                Button(text="🔁 Повторить", callback_data=f"more:{expense_id}"),
                Button(text="↩️ Отменить", callback_data=f"undo:{expense_id}"),
            ],
            [Button(text="💸 Новая трата", callback_data="add")],
            [Button(text="‹ Меню", callback_data="menu")],
        ]
    )


def periods() -> Keyboard:
    return Keyboard(
        inline_keyboard=[
            [
                Button(text="Сегодня", callback_data="an:day"),
                Button(text="Неделя", callback_data="an:week"),
                Button(text="Месяц", callback_data="an:month"),
            ],
            [Button(text="💸 Новая трата", callback_data="add")],
            [Button(text="‹ Меню", callback_data="menu")],
        ]
    )


def automations(presets: list[dict]) -> Keyboard:
    rows = [[Button(text="➕ Новая автоматизация", callback_data="auto:add")]]
    for preset in presets:
        rows.append(
            [
                Button(
                    text=f"🗑 {preset['name']} · {fmt_money(preset['amount'])}",
                    callback_data=f"auto:del:{preset['id']}",
                )
            ]
        )
    rows.append([Button(text="‹ Меню", callback_data="menu")])
    return Keyboard(inline_keyboard=rows)


def confirm_delete(preset_id: int) -> Keyboard:
    return Keyboard(
        inline_keyboard=[
            [
                Button(text="Удалить", callback_data=f"auto:delok:{preset_id}"),
                Button(text="Оставить", callback_data="auto"),
            ]
        ]
    )


def cancel(back: str = "menu", text: str = "‹ Отмена") -> Keyboard:
    return Keyboard(inline_keyboard=[[Button(text=text, callback_data=back)]])
