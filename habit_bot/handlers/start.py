from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from habit_bot.database import register_user


router = Router()


@router.message(CommandStart())
async def start_command(message: Message) -> None:
    user = message.from_user
    if user is None:
        await message.answer("I could not read your Telegram profile.")
        return

    await register_user(user.id, user.username)
    await message.answer(
        "Welcome! I will help you track your habits.\n\n"
        "Available commands:\n"
        "/add <name> - add a new habit\n"
        "/list - show your habits and their IDs\n"
        "/done <habit_id> - mark a habit done today\n"
        "/stats - show your habit stats"
    )
