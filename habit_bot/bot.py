import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiohttp import web

from habit_bot.config import get_settings
from habit_bot.database import close_pool, create_tables, init_pool
from habit_bot.handlers import habits, start, stats
from habit_bot.scheduler import setup_scheduler


async def health_check(request: web.Request) -> web.Response:
    _ = request
    return web.json_response({"status": "ok"})


async def start_health_server() -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", "8080"))
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    logging.info("Health check server started on port %s", port)
    return runner


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()

    dispatcher.include_router(start.router)
    dispatcher.include_router(habits.router)
    dispatcher.include_router(stats.router)

    await init_pool(settings.database_url)
    await create_tables()

    scheduler = setup_scheduler(bot, settings)
    scheduler.start()
    health_runner = await start_health_server()

    try:
        await dispatcher.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await health_runner.cleanup()
        await close_pool()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
