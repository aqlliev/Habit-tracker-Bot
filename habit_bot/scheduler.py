import logging
from collections import defaultdict
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from habit_bot.config import Settings
from habit_bot.database import incomplete_habits_for_all_users


logger = logging.getLogger(__name__)


async def send_daily_reminder(bot: Bot) -> None:
    today = datetime.now(timezone.utc).date()
    rows = await incomplete_habits_for_all_users(today)

    habits_by_user: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for row in rows:
        habits_by_user[row["telegram_id"]].append((row["habit_id"], row["habit_name"]))

    for telegram_id, habits in habits_by_user.items():
        habit_lines = "\n".join(f"- {name}" for _, name in habits)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"Done: {name}",
                        callback_data=f"done:{habit_id}",
                    )
                ]
                for habit_id, name in habits
            ]
        )

        try:
            await bot.send_message(
                telegram_id,
                "Good morning! A small step today still counts.\n\n"
                "You have not completed these habits yet:\n"
                f"{habit_lines}",
                reply_markup=keyboard,
            )
        except TelegramAPIError:
            logger.exception("Failed to send daily reminder to user %s", telegram_id)


def setup_scheduler(bot: Bot, settings: Settings) -> AsyncIOScheduler:
    _ = settings
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        send_daily_reminder,
        trigger="cron",
        hour=9,
        minute=0,
        args=[bot],
        id="daily_habit_reminder",
        replace_existing=True,
    )
    return scheduler
