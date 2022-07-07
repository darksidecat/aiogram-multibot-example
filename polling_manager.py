import asyncio
import functools
import logging
from asyncio import AbstractEventLoop, CancelledError, Task, get_running_loop
from contextvars import Context
from typing import Any, Awaitable, Dict, List, Optional

from aiogram import Bot
from aiogram.dispatcher.dispatcher import DEFAULT_BACKOFF_CONFIG, Dispatcher
from aiogram.types import User
from aiogram.utils.backoff import BackoffConfig

logger = logging.getLogger(__name__)


class PollingManager:
    def __init__(self):
        self.polling_tasks: Dict[int, Task] = {}

    def _create_pooling_task(
        self,
        dp: Dispatcher,
        bot: Bot,
        polling_timeout: int,
        handle_as_tasks: bool,
        backoff_config: BackoffConfig,
        allowed_updates: Optional[List[str]],
        **kwargs: Any,
    ):
        asyncio.create_task(
            self._start_bot_polling(
                dp=dp,
                bot=bot,
                polling_timeout=polling_timeout,
                handle_as_tasks=handle_as_tasks,
                backoff_config=backoff_config,
                allowed_updates=allowed_updates,
                **kwargs,
            )
        )

    def start_bot_polling(
        self,
        dp: Dispatcher,
        bot: Bot,
        polling_timeout: int = 10,
        handle_as_tasks: bool = True,
        backoff_config: BackoffConfig = DEFAULT_BACKOFF_CONFIG,
        allowed_updates: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        loop: AbstractEventLoop = get_running_loop()
        # noinspection PyArgumentList
        loop.call_soon(
            functools.partial(
                self._create_pooling_task,
                dp=dp,
                bot=bot,
                polling_timeout=polling_timeout,
                handle_as_tasks=handle_as_tasks,
                backoff_config=backoff_config,
                allowed_updates=allowed_updates,
                **kwargs,
            ),
            context=Context(),
        )

    async def _start_bot_polling(
        self,
        dp: Dispatcher,
        bot: Bot,
        polling_timeout: int = 10,
        handle_as_tasks: bool = True,
        backoff_config: BackoffConfig = DEFAULT_BACKOFF_CONFIG,
        allowed_updates: Optional[List[str]] = None,
        on_bot_startup: Optional[Awaitable] = None,
        on_bot_shutdown: Optional[Awaitable] = None,
        **kwargs: Any,
    ):
        logger.info("Start poling")
        user: User = await bot.me()
        if on_bot_startup:
            await on_bot_startup

        try:
            logger.info(
                "Run polling for bot @%s id=%d - %r",
                user.username,
                bot.id,
                user.full_name,
            )
            polling_task = asyncio.create_task(
                dp._polling(
                    bot=bot,
                    handle_as_tasks=handle_as_tasks,
                    polling_timeout=polling_timeout,
                    backoff_config=backoff_config,
                    allowed_updates=allowed_updates,
                    **kwargs,
                )
            )
            self.polling_tasks[bot.id] = polling_task
            await polling_task
        except CancelledError:
            logger.info("Polling task Canceled")
        finally:
            logger.info(
                "Polling stopped for bot @%s id=%d - %r",
                user.username,
                bot.id,
                user.full_name,
            )
            if on_bot_shutdown:
                await on_bot_shutdown

            await bot.session.close()

    def stop_bot_polling(self, bot_id: int):
        polling_task = self.polling_tasks.pop(bot_id)
        polling_task.cancel()
