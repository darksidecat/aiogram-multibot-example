import asyncio
import logging
from typing import List

from aiogram import Bot, Dispatcher, loggers, types
from aiogram.dispatcher.filters.command import Command, CommandObject
from aiogram.types import BotCommand, BotCommandScopeDefault, User
from aiogram.utils.token import TokenValidationError

TOKENS = [
    "TOKEN1",
    "TOKEN2",
]
ADMIN_ID = 123456789


async def set_commands(bot: Bot):
    commands = [
        BotCommand(
            command="add_bot",
            description="add bot, usage '/add_bot 123456789:qwertyuiopasdfgh'",
        ),
    ]

    await bot.set_my_commands(commands=commands, scope=BotCommandScopeDefault())


async def on_startup(bots: List[Bot]):
    for bot in bots:
        await set_commands(bot)
        await bot.send_message(chat_id=ADMIN_ID, text="Bot started!")


async def on_shutdown(bots: List[Bot]):
    for bot in bots:
        await bot.send_message(chat_id=ADMIN_ID, text="Bot shutdown!")


async def add_bot(message: types.Message, command: CommandObject, dp: Dispatcher):
    if command.args:
        try:
            bot = Bot(command.args)
            workflow_data = {"dispatcher": dp, "bots": [bot], "bot": bot}
            try:
                user: User = await bot.me()
                loggers.dispatcher.info(
                    "Run polling for bot @%s id=%d - %r",
                    user.username,
                    bot.id,
                    user.full_name,
                )
                await dp.emit_startup(**workflow_data)
                await message.answer(f"New bot started: @{user.username}")
                await dp._polling(bot=bot)
            finally:
                await dp.emit_shutdown(**workflow_data)
                await bot.session.close()
                loggers.dispatcher.info("Polling stopped")
        except TokenValidationError as err:
            await message.answer(f"{str(err)}")
    else:
        await message.answer("Please provide token")


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
    dp.message.register(echo)

    for bot in bots:
        await bot.get_updates(offset=-1)
    await dp.start_polling(*bots, dp=dp)


if __name__ == "__main__":
    asyncio.run(main())
