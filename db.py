from __future__ import annotations

from aiosqlite import Connection, Row, connect
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from categories import DEFAULT_PRESETS
from ui import now_local, utc_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id      INTEGER NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS expenses (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category   TEXT NOT NULL,
    amount     INTEGER NOT NULL,
    note       TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_expenses_user_date
    ON expenses(user_id, created_at);

CREATE TABLE IF NOT EXISTS presets (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    name     TEXT NOT NULL,
    amount   INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_presets_user
    ON presets(user_id);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[Connection]:
        db = await connect(self.path)
        db.row_factory = Row
        try:
            yield db
        finally:
            await db.close()

    async def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with self._connect() as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.executescript(SCHEMA)
            await db.commit()

    async def ensure_user(self, tg_id: int) -> int:
        async with self._connect() as db:
            cursor = await db.execute(
                "INSERT OR IGNORE INTO users (tg_id, created_at) VALUES (?, ?)",
                (tg_id, utc_iso(now_local())),
            )
            created = cursor.rowcount > 0
            await db.commit()

            cursor = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
            row = await cursor.fetchone()
            user_id = int(row["id"])

            if created:
                for category, presets in DEFAULT_PRESETS.items():
                    for name, amount in presets:
                        await db.execute(
                            "INSERT INTO presets (user_id, category, name, amount) "
                            "VALUES (?, ?, ?, ?)",
                            (user_id, category, name, amount),
                        )
                await db.commit()

            return user_id

    # --- траты ---------------------------------------------------------

    async def add_expense(
        self,
        user_id: int,
        category: str,
        amount: int,
        note: str | None = None,
    ) -> int:
        async with self._connect() as db:
            cursor = await db.execute(
                "INSERT INTO expenses (user_id, category, amount, note, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, category, amount, note, utc_iso(now_local())),
            )
            await db.commit()
            return int(cursor.lastrowid or 0)

    async def get_expense(self, user_id: int, expense_id: int) -> dict | None:
        async with self._connect() as db:
            cursor = await db.execute(
                "SELECT id, category, amount, note, created_at "
                "FROM expenses WHERE id = ? AND user_id = ?",
                (expense_id, user_id),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def delete_expense(self, user_id: int, expense_id: int) -> bool:
        async with self._connect() as db:
            cursor = await db.execute(
                "DELETE FROM expenses WHERE id = ? AND user_id = ?",
                (expense_id, user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def expenses_between(
        self,
        user_id: int,
        start_iso: str,
        end_iso: str,
    ) -> list[dict]:
        async with self._connect() as db:
            cursor = await db.execute(
                "SELECT id, category, amount, note, created_at "
                "FROM expenses "
                "WHERE user_id = ? AND created_at >= ? AND created_at < ? "
                "ORDER BY created_at",
                (user_id, start_iso, end_iso),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # --- автоматизации -------------------------------------------------

    async def presets(self, user_id: int, category: str | None = None) -> list[dict]:
        query = "SELECT id, category, name, amount FROM presets WHERE user_id = ?"
        params: list[object] = [user_id]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY id"
        async with self._connect() as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_preset(self, user_id: int, preset_id: int) -> dict | None:
        async with self._connect() as db:
            cursor = await db.execute(
                "SELECT id, category, name, amount "
                "FROM presets WHERE id = ? AND user_id = ?",
                (preset_id, user_id),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def add_preset(
        self,
        user_id: int,
        category: str,
        name: str,
        amount: int,
    ) -> int:
        async with self._connect() as db:
            cursor = await db.execute(
                "INSERT INTO presets (user_id, category, name, amount) "
                "VALUES (?, ?, ?, ?)",
                (user_id, category, name, amount),
            )
            await db.commit()
            return int(cursor.lastrowid or 0)

    async def delete_preset(self, user_id: int, preset_id: int) -> bool:
        async with self._connect() as db:
            cursor = await db.execute(
                "DELETE FROM presets WHERE id = ? AND user_id = ?",
                (preset_id, user_id),
            )
            await db.commit()
            return cursor.rowcount > 0
