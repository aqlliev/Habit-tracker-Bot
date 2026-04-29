from __future__ import annotations

from datetime import date

import asyncpg


Pool = asyncpg.Pool

pool: Pool | None = None


async def init_pool(database_url: str) -> Pool:
    global pool
    pool = await asyncpg.create_pool(database_url)
    return pool


async def close_pool() -> None:
    global pool
    if pool is not None:
        await pool.close()
        pool = None


def get_pool() -> Pool:
    if pool is None:
        raise RuntimeError("Database pool is not initialized")
    return pool


async def create_tables() -> None:
    db = get_pool()
    async with db.acquire() as connection:
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                username TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS habits (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS habit_logs (
                id BIGSERIAL PRIMARY KEY,
                habit_id BIGINT NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
                completed_date DATE NOT NULL,
                UNIQUE (habit_id, completed_date)
            );
            """
        )


async def register_user(telegram_id: int, username: str | None) -> None:
    db = get_pool()
    async with db.acquire() as connection:
        await connection.execute(
            """
            INSERT INTO users (telegram_id, username)
            VALUES ($1, $2)
            ON CONFLICT (telegram_id)
            DO UPDATE SET username = EXCLUDED.username;
            """,
            telegram_id,
            username,
        )


async def add_habit(user_id: int, name: str) -> int:
    db = get_pool()
    async with db.acquire() as connection:
        return await connection.fetchval(
            """
            INSERT INTO habits (user_id, name)
            VALUES ($1, $2)
            RETURNING id;
            """,
            user_id,
            name,
        )


async def list_habits(user_id: int) -> list[asyncpg.Record]:
    db = get_pool()
    async with db.acquire() as connection:
        return await connection.fetch(
            """
            SELECT id, name, created_at
            FROM habits
            WHERE user_id = $1
            ORDER BY created_at ASC;
            """,
            user_id,
        )


async def log_habit_done(user_id: int, habit_id: int, completed_date: date) -> bool:
    db = get_pool()
    async with db.acquire() as connection:
        result = await connection.execute(
            """
            INSERT INTO habit_logs (habit_id, completed_date)
            SELECT id, $3
            FROM habits
            WHERE id = $1 AND user_id = $2
            ON CONFLICT (habit_id, completed_date) DO NOTHING;
            """,
            habit_id,
            user_id,
            completed_date,
        )
        return result == "INSERT 0 1"


async def habit_stats(user_id: int) -> list[asyncpg.Record]:
    db = get_pool()
    async with db.acquire() as connection:
        return await connection.fetch(
            """
            SELECT
                h.id,
                h.name,
                COUNT(l.id) AS completions,
                MAX(l.completed_date) AS last_completed
            FROM habits h
            LEFT JOIN habit_logs l ON l.habit_id = h.id
            WHERE h.user_id = $1
            GROUP BY h.id, h.name
            ORDER BY h.created_at ASC;
            """,
            user_id,
        )


async def habit_completion_stats(user_id: int) -> list[asyncpg.Record]:
    db = get_pool()
    async with db.acquire() as connection:
        return await connection.fetch(
            """
            SELECT
                h.id,
                h.name,
                COALESCE(
                    ARRAY_AGG(l.completed_date ORDER BY l.completed_date)
                    FILTER (WHERE l.completed_date IS NOT NULL),
                    ARRAY[]::DATE[]
                ) AS completed_dates
            FROM habits h
            LEFT JOIN habit_logs l ON l.habit_id = h.id
            WHERE h.user_id = $1
            GROUP BY h.id, h.name, h.created_at
            ORDER BY h.created_at ASC;
            """,
            user_id,
        )


async def incomplete_habits_for_all_users(completed_date: date) -> list[asyncpg.Record]:
    db = get_pool()
    async with db.acquire() as connection:
        return await connection.fetch(
            """
            SELECT
                u.telegram_id,
                h.id AS habit_id,
                h.name AS habit_name
            FROM users u
            JOIN habits h ON h.user_id = u.telegram_id
            LEFT JOIN habit_logs l
                ON l.habit_id = h.id
                AND l.completed_date = $1
            WHERE l.id IS NULL
            ORDER BY u.telegram_id, h.created_at ASC;
            """,
            completed_date,
        )


async def habits_status_for_user(user_id: int, completed_date: date) -> list[asyncpg.Record]:
    db = get_pool()
    async with db.acquire() as connection:
        return await connection.fetch(
            """
            SELECT
                h.id,
                h.name,
                l.id IS NOT NULL AS is_done
            FROM habits h
            LEFT JOIN habit_logs l
                ON l.habit_id = h.id
                AND l.completed_date = $2
            WHERE h.user_id = $1
            ORDER BY h.created_at ASC;
            """,
            user_id,
            completed_date,
        )
