from __future__ import annotations

from typing import Final

# code -> (emoji, название)
CATEGORIES: Final[dict[str, tuple[str, str]]] = {
    "transport": ("🚌", "Транспорт"),
    "groceries": ("🛒", "Продукты"),
    "food": ("🍔", "Еда вне дома"),
    "coffee": ("☕", "Кофе"),
    "home": ("🏠", "Жильё"),
    "health": ("💊", "Здоровье"),
    "fun": ("🎬", "Развлечения"),
    "clothes": ("👕", "Одежда"),
    "subscriptions": ("📱", "Подписки"),
    "other": ("✨", "Другое"),
}

CATEGORY_ORDER: Final[tuple[str, ...]] = (
    "transport",
    "groceries",
    "food",
    "coffee",
    "home",
    "health",
    "fun",
    "clothes",
    "subscriptions",
    "other",
)

# Автоматизации, которые создаются при первом запуске.
# Суммы указаны в копейках: 105 = 1,05 ₽, 200 = 2 ₽.
DEFAULT_PRESETS: Final[dict[str, tuple[tuple[str, int], ...]]] = {
    "transport": (
        ("Автобус", 105),
        ("Маршрутка", 200),
    ),
}
