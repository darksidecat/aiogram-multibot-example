import asyncio
import logging
from typing import List

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters.command import Command, CommandObject
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.utils.markdown import html_decoration as fmt
from aiogram.utils.token import TokenValidationError

from polling_manager import PollingManager

logger = logging.getLogger(__name__)

TOKENS = [
    "TOKEN1",
    "TOKEN2",
]
ADMIN_ID = 1234567890


async def set_commands(bot: Bot):
    commands = [
        BotCommand(
            command="add_bot",
            description="add bot, usage '/add_bot 123456789:qwertyuiopasdfgh'",
        ),
        BotCommand(
            command="stop_bot",
            description="stop bot, usage '/stop_bot 123456789'",
        ),
    ]

    await bot.set_my_commands(commands=commands, scope=BotCommandScopeDefault())


async def on_bot_startup(bot: Bot):
    await set_commands(bot)
    await bot.send_message(chat_id=ADMIN_ID, text="Bot started!")


async def on_bot_shutdown(bot: Bot):
    await bot.send_message(chat_id=ADMIN_ID, text="Bot shutdown!")


async def on_startup(bots: List[Bot]):
    for bot in bots:
        await on_bot_startup(bot)


async def on_shutdown(bots: List[Bot]):
    for bot in bots:
        await on_bot_shutdown(bot)


async def add_bot(
    message: types.Message,
    command: CommandObject,
    dp_for_new_bot: Dispatcher,
    polling_manager: PollingManager,
):
    if command.args:
        try:
            bot = Bot(command.args)

            if bot.id in polling_manager.polling_tasks:
                await message.answer("Bot with this id already running")
                return

            # also propagate dp and polling manager to new bot to allow new bot add bots
            await polling_manager.start_bot_polling(
                dp=dp_for_new_bot,
                bot=bot,
                on_bot_startup=on_bot_startup(bot),
                on_bot_shutdown=on_bot_shutdown(bot),
                polling_manager=polling_manager,
                dp_for_new_bot=dp_for_new_bot
            )
            bot_user = await bot.get_me()
            await message.answer(f"New bot started: @{bot_user.username}")
        except (TokenValidationError, TelegramUnauthorizedError) as err:
            await message.answer(fmt.quote(f"{type(err).__name__}: {str(err)}"))
    else:
        await message.answer("Please provide token")


async def stop_bot(
    message: types.Message, command: CommandObject, polling_manager: PollingManager
):
    if command.args:
        try:
            polling_manager.stop_bot_polling(int(command.args))
            await message.answer("Bot stopped")
        except (ValueError, KeyError) as err:
            await message.answer(fmt.quote(f"{type(err).__name__}: {str(err)}"))
    else:
        await message.answer("Please provide bot id")


async def echo(message: types.Message):
    await message.answer(message.text)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    bots = [Bot(token) for token in TOKENS]
    dp = Dispatcher(isolate_events=True)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.message.register(add_bot, Command(commands="add_bot"))
    dp.message.register(stop_bot, Command(commands="stop_bot"))
    dp.message.register(echo)

    polling_manager = PollingManager()

    for bot in bots:
        await bot.get_updates(offset=-1)
    await dp.start_polling(*bots, dp_for_new_bot=dp, polling_manager=polling_manager)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Exit")
