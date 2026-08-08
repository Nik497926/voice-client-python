# voice-client (Python)

Python SDK для Voice Bot API: gRPC `BotsApi` + SignalR gateway `/hubs/bots`, слэш- и текстовые команды, билдеры компонентов.

Репозиторий: [github.com/Nik497926/voice-client-python](https://github.com/Nik497926/voice-client-python)

## Установка

Из GitHub (пока не на PyPI):

```bash
pip install git+https://github.com/Nik497926/voice-client-python.git
```

Локально из исходников:

```bash
pip install -e ".[dev]"
python scripts/generate_proto.py   # при необходимости пересобрать stubs
```

## Быстрый старт

```python
import asyncio
from voice.client import BotClient, BotClientOptions, UserStatus

async def main():
    client = BotClient.create(BotClientOptions(
        bot_token="ibot_...",
        bots_api_endpoint="https://api.iopta.org",
    ))

    async def on_message(message):
        if message.author.is_bot:
            return
        print(message.content)

    client.message_created.append(on_message)

    me = await client.get_me_async()
    print(f"Вошли как {me.username}")
    await client.set_status_async(UserStatus.ONLINE)
    await client.run_async()  # поднимает gateway и ждёт

asyncio.run(main())
```

## Текстовые команды

```python
from voice.client import CommandService, ModuleBase, command, alias

class PingModule(ModuleBase):
    @command("ping")
    @alias("p")
    async def ping(self):
        await self.reply_async("pong")

commands = CommandService(client, prefix="!")
commands.add_module(PingModule)
commands.initialize()
```

## Слэш-команды

```python
from voice.client import InteractionService, InteractionModuleBase, slash_command

class SlashModule(InteractionModuleBase):
    @slash_command("hello", "Поприветствовать")
    async def hello(self):
        await self.respond_async("Привет!")

interactions = InteractionService(client)
interactions.add_module(SlashModule)
interactions.initialize()
await interactions.register_commands_async()
```

## Компоненты

```python
from voice.client import ComponentBuilder, ButtonStyle

components = (
    ComponentBuilder()
    .with_button(lambda b: b.with_custom_id("ok").with_label("OK").with_style(ButtonStyle.SUCCESS))
)
await client.send_message_async(channel_id, "Выберите:", components=components)
```

## Пример

См. [`examples/echo_bot/main.py`](examples/echo_bot/main.py):

```bash
set BOT_TOKEN=ibot_...
python examples/echo_bot/main.py
```

## Генерация protobuf

```bash
python scripts/generate_proto.py
# или
bash scripts/generate_proto.sh
```

Сгенерированный код лежит в `src/voice/client/_generated/` (`bots_pb2`, `bots_pb2_grpc`, `common_pb2`, `interactions_pb2`, `interactions_pb2_grpc`).

## Зависимости

- `grpcio`, `protobuf` — gRPC API
- `signalrcore` — ASP.NET Core SignalR gateway
- `httpx` — HTTP-утилиты

Auth: gRPC — `Authorization: Bearer {bot_token}`; gateway — `access_token` на handshake.
