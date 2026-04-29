from datetime import date, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from habit_bot.database import habit_completion_stats


router = Router()


def current_streak(completed_dates: set[date], today: date) -> int:
    streak = 0
    day = today

    while day in completed_dates:
        streak += 1
        day -= timedelta(days=1)

    return streak


def completion_rate(completed_dates: set[date], today: date, days: int = 30) -> int:
    start_date = today - timedelta(days=days - 1)
    completed_count = sum(
        1
        for offset in range(days)
        if start_date + timedelta(days=offset) in completed_dates
    )
    return round((completed_count / days) * 100)


def weekly_bar(completed_dates: set[date], today: date) -> str:
    days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    return "".join("🟩" if day in completed_dates else "⬜" for day in days)


@router.message(Command("stats"))
async def stats_command(message: Message) -> None:
    user = message.from_user
    if user is None:
        await message.answer("I could not read your Telegram profile.")
        return

    today = date.today()
    stats = await habit_completion_stats(user.id)
    if not stats:
        await message.answer("No habits yet. Add your first one with /add <habit name>.")
        return

    lines = ["Habit stats:"]
    for habit in stats:
        completed_dates = set(habit["completed_dates"])
        streak = current_streak(completed_dates, today)
        rate = completion_rate(completed_dates, today)
        bar = weekly_bar(completed_dates, today)

        lines.extend(
            [
                "",
                f"#{habit['id']} - {habit['name']}",
                f"Current streak: {streak} day{'s' if streak != 1 else ''}",
                f"Last 30 days: {rate}%",
                f"Last 7 days: {bar}",
            ]
        )

    await message.answer("\n".join(lines))
