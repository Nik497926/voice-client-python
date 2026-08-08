"""SignalR gateway topics and connection."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable, Optional

from signalrcore.hub_connection_builder import HubConnectionBuilder

from voice.client.options import BotClientOptions

logger = logging.getLogger(__name__)

CHAT_EVENTS = "chat-events"
CHANNEL_EVENTS = "channel-events"
GROUP_EVENTS = "group-events"
INTERACTION_EVENTS = "interaction-events"

ALL_TOPICS = (CHAT_EVENTS, CHANNEL_EVENTS, GROUP_EVENTS, INTERACTION_EVENTS)

MessageHandler = Callable[[str, str], None]
ErrorHandler = Callable[[BaseException], None]


class SignalRBotGatewayConnection:
    """SignalR connection to ``{endpoint}/hubs/bots`` with access_token auth."""

    def __init__(self, options: BotClientOptions) -> None:
        self._options = options
        self._message_handlers: list[MessageHandler] = []
        self._error_handlers: list[ErrorHandler] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue[tuple[str, str] | None] | None = None
        self._pump_task: asyncio.Task[None] | None = None
        self._connection = self._build()

    def _build(self):
        url = f"{self._options.bots_api_endpoint.rstrip('/')}/hubs/bots"
        token = self._options.bot_token

        def access_token_factory() -> str:
            return token

        builder = (
            HubConnectionBuilder()
            .with_url(
                url,
                options={
                    "access_token_factory": access_token_factory,
                    "verify_ssl": not self._options.allow_untrusted_certificates,
                },
            )
            .with_automatic_reconnect(
                {
                    "type": "raw",
                    "keep_alive_interval": 10,
                    "reconnect_interval": 5,
                    "max_attempts": 50,
                }
            )
        )
        connection = builder.build()

        for topic in ALL_TOPICS:
            connection.on(topic, self._make_topic_handler(topic))

        connection.on_error(lambda data: self._emit_error(Exception(str(data))))
        return connection

    def _make_topic_handler(self, topic: str):
        def handler(*args):
            try:
                raw = self._normalize_payload(args)
                self._enqueue(topic, raw)
            except Exception as ex:  # noqa: BLE001
                self._emit_error(ex)

        return handler

    @staticmethod
    def _normalize_payload(args) -> str:
        if not args:
            return "{}"
        payload = args[0] if len(args) == 1 else args
        if isinstance(payload, str):
            return payload
        return json.dumps(payload)

    def _enqueue(self, topic: str, raw: str) -> None:
        loop = self._loop
        queue = self._queue
        if loop is None or queue is None:
            for handler in list(self._message_handlers):
                handler(topic, raw)
            return

        def put() -> None:
            queue.put_nowait((topic, raw))

        loop.call_soon_threadsafe(put)

    def _emit_error(self, error: BaseException) -> None:
        for handler in list(self._error_handlers):
            try:
                handler(error)
            except Exception:  # noqa: BLE001
                logger.exception("gateway error handler failed")

    def on_message(self, handler: MessageHandler) -> None:
        self._message_handlers.append(handler)

    def off_message(self, handler: MessageHandler) -> None:
        if handler in self._message_handlers:
            self._message_handlers.remove(handler)

    def on_error(self, handler: ErrorHandler) -> None:
        self._error_handlers.append(handler)

    def off_error(self, handler: ErrorHandler) -> None:
        if handler in self._error_handlers:
            self._error_handlers.remove(handler)

    async def start_async(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        self._pump_task = asyncio.create_task(self._pump(), name="voice-gateway-pump")
        await self._loop.run_in_executor(None, self._connection.start)

    async def stop_async(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self._connection.stop)
        finally:
            if self._queue is not None:
                await self._queue.put(None)
            if self._pump_task is not None:
                try:
                    await self._pump_task
                except asyncio.CancelledError:
                    pass
                self._pump_task = None
            self._queue = None

    async def _pump(self) -> None:
        assert self._queue is not None
        while True:
            item = await self._queue.get()
            if item is None:
                return
            topic, raw = item
            for handler in list(self._message_handlers):
                try:
                    handler(topic, raw)
                except Exception as ex:  # noqa: BLE001
                    self._emit_error(ex)

    async def aclose(self) -> None:
        await self.stop_async()


from voice.client.gateway.parser import parse_gateway_event  # noqa: E402

__all__ = [
    "ALL_TOPICS",
    "CHANNEL_EVENTS",
    "CHAT_EVENTS",
    "GROUP_EVENTS",
    "INTERACTION_EVENTS",
    "SignalRBotGatewayConnection",
    "parse_gateway_event",
]
