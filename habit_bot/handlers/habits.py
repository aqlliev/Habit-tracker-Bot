from __future__ import annotations

from datetime import date, datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from habit_bot.database import (
    add_habit,
    habits_status_for_user,
    list_habits,
    log_habit_done,
    register_user,
)


router = Router()


def build_reminder_text_and_keyboard(
    habits: list,
) -> tuple[str, InlineKeyboardMarkup | None, bool]:
    lines = ["Habit reminder:"]
    keyboard_rows = []

    for habit in habits:
        prefix = "✅" if habit["is_done"] else "⬜"
        lines.append(f"{prefix} {habit['name']}")

        if not habit["is_done"]:
            keyboard_rows.append(
                [
                    InlineKeyboardButton(
                        text=f"Done: {habit['name']}",
                        callback_data=f"done:{habit['id']}",
                    )
                ]
            )

    all_done = bool(habits) and not keyboard_rows
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows) if keyboard_rows else None
    return "\n".join(lines), keyboard, all_done


@router.message(Command("add"))
async def add_habit_command(message: Message, command: CommandObject) -> None:
    user = message.from_user
    if user is None:
        await message.answer("I could not read your Telegram profile.")
        return

    name = command.args.strip() if command.args else ""
    if not name:
        await message.answer("Send /add followed by a habit name. Example: /add Drink water")
        return

    await register_user(user.id, user.username)
    habit_id = await add_habit(user.id, name)
    await message.answer(f"Added habit #{habit_id}: {name}")


@router.message(Command("list"))
async def list_habits_command(message: Message) -> None:
    user = message.from_user
    if user is None:
        await message.answer("I could not read your Telegram profile.")
        return

    habits = await list_habits(user.id)
    if not habits:
        await message.answer("You do not have any habits yet. Add one with /add <habit name>.")
        return

    lines = [f"#{habit['id']} - {habit['name']}" for habit in habits]
    await message.answer("Your habits:\n" + "\n".join(lines))


@router.message(Command("done"))
async def done_command(message: Message, command: CommandObject) -> None:
    user = message.from_user
    if user is None:
        await message.answer("I could not read your Telegram profile.")
        return

    raw_id = command.args.strip() if command.args else ""
    if not raw_id.isdigit():
        await message.answer("Send /done followed by a habit id. Example: /done 1")
        return

    inserted = await log_habit_done(user.id, int(raw_id), date.today())
    if inserted:
        await message.answer("Marked as done for today.")
    else:
        await message.answer("That habit was already done today, or I could not find it.")


@router.callback_query(F.data.startswith("done:"))
async def reminder_done_callback(callback: CallbackQuery) -> None:
    user = callback.from_user
    raw_id = callback.data.removeprefix("done:") if callback.data else ""

    if not raw_id.isdigit():
        await callback.answer("Invalid habit button.", show_alert=True)
        return

    today = datetime.now(timezone.utc).date()
    inserted = await log_habit_done(user.id, int(raw_id), today)
    habits = await habits_status_for_user(user.id, today)
    text, keyboard, all_done = build_reminder_text_and_keyboard(habits)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard)

    if inserted:
        await callback.answer("Marked as done for today.")
    else:
        await callback.answer("Already done today, or habit not found.", show_alert=True)

    if inserted and all_done and callback.message:
        await callback.message.answer("Congratulations! All habits are done for today.")
