from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from categories import CATEGORIES
from db import Database
from ui import bar, date_range, fmt_money, now_local, percent, plural, utc_iso

PERIODS: dict[str, dict[str, object]] = {
    "day": {"title": "Сегодня", "days": 1, "compare": "ко вчерашнему дню"},
    "week": {"title": "Неделя", "days": 7, "compare": "к прошлой неделе"},
    "month": {"title": "Месяц", "days": 30, "compare": "к прошлому месяцу"},
}


@dataclass
class Stats:
    key: str
    title: str
    days: int
    range_label: str
    compare_label: str
    total: int
    count: int
    by_category: list[tuple[str, int]]
    prev_total: int
    prev_by_category: dict[str, int]
    expenses: list[dict]
    start: datetime
    end: datetime


def _totals(rows: list[dict]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for row in rows:
        category = str(row["category"])
        totals[category] = totals.get(category, 0) + int(row["amount"])
    return totals


async def collect(db: Database, user_id: int, key: str) -> Stats:
    settings = PERIODS[key]
    days = int(settings["days"])

    now = now_local()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=days - 1)
    end = today + timedelta(days=1)
    prev_start = start - timedelta(days=days)
    prev_end = start

    rows = await db.expenses_between(user_id, utc_iso(start), utc_iso(end))
    prev_rows = await db.expenses_between(user_id, utc_iso(prev_start), utc_iso(prev_end))

    current = _totals(rows)
    previous = _totals(prev_rows)
    by_category = sorted(current.items(), key=lambda item: item[1], reverse=True)

    return Stats(
        key=key,
        title=str(settings["title"]),
        days=days,
        range_label=date_range(start, end),
        compare_label=str(settings["compare"]),
        total=sum(current.values()),
        count=len(rows),
        by_category=by_category,
        prev_total=sum(previous.values()),
        prev_by_category=previous,
        expenses=rows,
        start=start,
        end=end,
    )


def _trend(stats: Stats) -> str | None:
    if stats.days <= 1 or stats.prev_total < 10_000:
        return None
    delta = stats.total - stats.prev_total
    change = round(abs(delta) * 100 / stats.prev_total)
    if change < 3:
        return None
    arrow = "↑" if delta > 0 else "↓"
    return f"{arrow} {min(change, 999)}% {stats.compare_label}"


def build_advice(stats: Stats) -> tuple[list[str], int]:
    """Возвращает советы и ориентир экономии в копейках."""
    total = stats.total
    if total <= 0:
        return [], 0

    by = dict(stats.by_category)
    candidates: list[tuple[int, int, str]] = []

    def count_category(code: str) -> int:
        return sum(1 for row in stats.expenses if row.get("category") == code)

    transport = by.get("transport", 0)
    rides = count_category("transport")
    if transport > 0 and rides >= 5:
        save = int(transport * 0.12)
        candidates.append(
            (
                1,
                save,
                f"<b>Транспорт.</b> {rides} "
                f"{plural(rides, 'поездка', 'поездки', 'поездок')} на {fmt_money(transport)}. "
                "Если маршрут повторяется, абонемент или проездной обычно выгоднее "
                "разовых билетов — проверьте тарифы перевозчика.",
            )
        )

    coffee = by.get("coffee", 0)
    coffee_buys = count_category("coffee")
    if coffee > 0 and coffee_buys >= 3:
        save = int(coffee * 0.3)
        candidates.append(
            (
                1,
                save,
                f"<b>Кофе.</b> {coffee_buys} "
                f"{plural(coffee_buys, 'покупка', 'покупки', 'покупок')} на {fmt_money(coffee)}. "
                "Термокружка или кофе дома сохраняют ритуал, но обходятся заметно дешевле.",
            )
        )

    food = by.get("food", 0)
    if food >= 500 and food / total >= 0.15:
        save = int(food * 0.15)
        candidates.append(
            (
                1,
                save,
                f"<b>Еда вне дома.</b> {fmt_money(food)} — {percent(food, total)} расходов. "
                "Пара домашних ужинов в неделю вместо спонтанной доставки экономит "
                "без отказа от любимых блюд.",
            )
        )

    groceries = by.get("groceries", 0)
    if groceries >= 1500:
        save = int(groceries * 0.08)
        candidates.append(
            (
                1,
                save,
                f"<b>Продукты.</b> {fmt_money(groceries)}. Список перед магазином и покупки "
                "не на голодный желудок обычно сокращают чек на 10–15%.",
            )
        )

    subscriptions = by.get("subscriptions", 0)
    if subscriptions > 0:
        save = int(subscriptions * 0.3)
        candidates.append(
            (
                1,
                save,
                f"<b>Подписки.</b> {fmt_money(subscriptions)}. Раз в месяц проверяйте, "
                "чем реально пользовались: отключение лишнего не меняет привычки, "
                "но возвращает деньги.",
            )
        )

    fun = by.get("fun", 0)
    if fun >= 500 and fun / total >= 0.2:
        save = int(fun * 0.1)
        candidates.append(
            (
                1,
                save,
                f"<b>Развлечения.</b> {fmt_money(fun)} — {percent(fun, total)} расходов. "
                "Не урезайте, а задайте недельный лимит: так спонтанные траты "
                "не съедят бюджет.",
            )
        )

    clothes = by.get("clothes", 0)
    if clothes >= 3000:
        save = int(clothes * 0.1)
        candidates.append(
            (
                1,
                save,
                f"<b>Одежда.</b> {fmt_money(clothes)}. Правило 24 часов перед покупкой "
                "дороже 3 000 ₽ помогает оставить только то, что действительно нравится.",
            )
        )

    if stats.days > 1 and stats.prev_total >= 10_000:
        growth = stats.total - stats.prev_total
        if growth > 0 and growth / stats.prev_total >= 0.2:
            change = min(round(growth * 100 / stats.prev_total), 999)
            growth_code: str | None = None
            growth_value = 0
            for code, amount in stats.by_category:
                diff = amount - stats.prev_by_category.get(code, 0)
                if diff > growth_value:
                    growth_code, growth_value = code, diff
            detail = ""
            if growth_code is not None:
                emoji, label = CATEGORIES.get(growth_code, ("✨", growth_code))
                detail = (
                    f" Сильнее всего выросла категория {emoji} {label} "
                    f"(+{fmt_money(growth_value)})."
                )
            candidates.insert(
                0,
                (
                    0,
                    0,
                    f"<b>Тренд.</b> Расходы выше прошлого периода на {change}%.{detail} "
                    "Начните с этой категории — часто достаточно одного осознанного решения.",
                ),
            )

    candidates.sort(key=lambda item: (item[0], -item[1]))
    tips = [text for _, _, text in candidates[:3]]

    if len(tips) < 2:
        if total <= 500:
            tips.append(
                "<b>Спокойный период.</b> Крупных зон роста нет — хороший момент, "
                "чтобы проверить подписки и автоплатежи."
            )
        else:
            tips.append(
                "<b>Привычка.</b> Отмечайте частые траты автоматизациями: меньше усилий — "
                "точнее картина и проще замечать лишнее."
            )

    savings = sum(save for group, save, _ in candidates[:3] if group == 1)
    if savings > total * 0.4:
        savings = int(total * 0.4)

    return tips, savings


def render(stats: Stats) -> str:
    lines = [f"📊 <b>{stats.title}</b>", f"<i>{stats.range_label}</i>"]

    if stats.total <= 0:
        lines += [
            "",
            "Пока нет трат за этот период.",
            "Добавьте первую — и я покажу, куда уходят деньги.",
        ]
        return "\n".join(lines)

    lines += ["", f"<b>{fmt_money(stats.total)}</b>"]

    meta = f"{stats.count} {plural(stats.count, 'трата', 'траты', 'трат')}"
    if stats.days > 1:
        per_day = round(stats.total / stats.days / 100) * 100
        meta += f" · {fmt_money(per_day)} в день"
    lines.append(meta)

    trend = _trend(stats)
    if trend:
        lines.append(f"<i>{trend}</i>")

    lines.append("")
    for code, amount in stats.by_category[:5]:
        emoji, label = CATEGORIES.get(code, ("✨", code))
        lines.append(f"{emoji} {label} · {fmt_money(amount)} · {percent(amount, stats.total)}")
        lines.append(bar(amount / stats.total))
        lines.append("")

    if len(stats.by_category) > 5:
        rest = sum(amount for _, amount in stats.by_category[5:])
        extra = len(stats.by_category) - 5
        lines.append(
            f"… и ещё {extra} "
            f"{plural(extra, 'категория', 'категории', 'категорий')} · {fmt_money(rest)}"
        )
        lines.append("")

    tips, savings = build_advice(stats)
    if tips:
        lines.append("💡 <b>Как тратить меньше</b>")
        lines.append("")
        for tip in tips:
            lines.append(f"— {tip}")
            lines.append("")
        if savings >= 5_000:
            lines.append(
                f"<i>Ориентир экономии — ≈ {fmt_money(savings)} "
                "без отказа от привычек.</i>"
            )

    return "\n".join(lines).rstrip()
