import asyncio
from aiogram import Bot, Dispatcher
from config import TOKEN
from handlers import common_handlers, admin_handlers, worker_handlers


async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    dp.include_router(common_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(worker_handlers.router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())