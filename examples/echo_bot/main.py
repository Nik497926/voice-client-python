"""Echo bot example — prefix !echo and a simple message logger."""

from __future__ import annotations

import asyncio
import os
import sys

from voice.client import (
    BotClient,
    BotClientOptions,
    CommandService,
    ModuleBase,
    UserStatus,
    alias,
    command,
)


class EchoModule(ModuleBase):
    @command("echo")
    @alias("e")
    async def echo(self, text: str) -> None:
        await self.reply_async(text or "(пусто)")

    @command("ping")
    async def ping(self) -> None:
        await self.reply_async("pong")


async def main() -> None:
    token = os.environ.get("BOT_TOKEN") or os.environ.get("BotToken")
    if not token:
        print("Задайте BOT_TOKEN (токен бота) в переменных окружения.", file=sys.stderr)
        raise SystemExit(1)

    endpoint = os.environ.get("BOTS_API_ENDPOINT", "https://api.iopta.org")
    allow_untrusted = os.environ.get("ALLOW_UNTRUSTED_CERTIFICATES", "").lower() in ("1", "true", "yes")

    options = BotClientOptions(
        bot_token=token,
        bots_api_endpoint=endpoint,
        allow_untrusted_certificates=allow_untrusted,
        text_command_prefix="!",
    )
    client = BotClient.create(options)

    commands = CommandService(client, prefix=options.text_command_prefix)
    commands.add_module(EchoModule)
    commands.initialize()

    async def on_error(ex: BaseException) -> None:
        print(f"[gateway error] {ex}", file=sys.stderr)

    async def on_message(message) -> None:
        if message.author.is_bot:
            return
        print(f"[message] {message.channel_id}: {message.content}")

    client.connection_error.append(on_error)
    client.message_created.append(on_message)

    me = await client.get_me_async()
    print(f"Вошли как {me.username} ({me.id})")
    for group in await client.get_my_groups_async():
        print(f"  группа: {group.name} ({group.id})")

    await client.set_status_async(UserStatus.ONLINE)
    print("Gateway стартует… Ctrl+C для выхода.")
    try:
        await client.run_async()
    except asyncio.CancelledError:
        pass
    finally:
        await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
