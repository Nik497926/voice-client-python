"""Prefix (text) command framework."""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Sequence, Type, get_type_hints

from voice.client.components import ComponentBuilder
from voice.client.events import GatewayMessage
from voice.client.models import MessageInfo

logger = logging.getLogger(__name__)


def command(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn._voice_command = name  # type: ignore[attr-defined]
        return fn

    return decorator


def alias(*aliases: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn._voice_aliases = aliases  # type: ignore[attr-defined]
        return fn

    return decorator


def tokenize(input_text: str) -> list[str]:
    """Whitespace tokenizer with quoted substrings — matches .NET CommandArgumentParser."""
    tokens: list[str] = []
    i = 0
    length = len(input_text)
    while i < length:
        while i < length and input_text[i].isspace():
            i += 1
        if i >= length:
            break
        if input_text[i] == '"':
            closing = input_text.find('"', i + 1)
            if closing < 0:
                tokens.append(input_text[i + 1 :])
                break
            tokens.append(input_text[i + 1 : closing])
            i = closing + 1
        else:
            start = i
            while i < length and not input_text[i].isspace():
                i += 1
            tokens.append(input_text[start:i])
    return tokens


def convert_argument(raw: str | None, target_type: type) -> Any:
    if raw is None:
        if target_type in (str,):
            return None
        if target_type is bool:
            return False
        if target_type in (int,):
            return 0
        if target_type is float:
            return 0.0
        return None
    if target_type is str or target_type is Any:
        return raw
    if target_type is bool:
        return raw.lower() in ("1", "true", "yes", "y", "on")
    if target_type is int:
        try:
            return int(raw)
        except ValueError:
            return 0
    if target_type is float:
        try:
            return float(raw)
        except ValueError:
            return 0.0
    return raw


class CommandContext:
    def __init__(self, client: Any, message: GatewayMessage) -> None:
        self.client = client
        self.message = message

    @property
    def channel_id(self) -> str:
        return self.message.channel_id

    @property
    def author_id(self) -> str:
        return self.message.author.id

    async def reply_async(
        self,
        content: str,
        components: ComponentBuilder | None = None,
    ) -> MessageInfo:
        return await self.client.send_message_async(
            self.message.channel_id,
            content,
            reply_to=self.message.id,
            components=components,
        )


class ModuleBase:
    context: CommandContext

    async def reply_async(self, content: str, components: ComponentBuilder | None = None) -> MessageInfo:
        return await self.context.reply_async(content, components)


@dataclass
class _RegisteredCommand:
    name: str
    aliases: Sequence[str]
    method: Callable[..., Any]
    module_type: Type[ModuleBase]

    def matches(self, command_name: str) -> bool:
        needle = command_name.lower()
        if self.name.lower() == needle:
            return True
        return any(a.lower() == needle for a in self.aliases)


class CommandService:
    def __init__(
        self,
        client: Any,
        prefix: str = "!",
        module_factory: Callable[[Type[ModuleBase]], ModuleBase] | None = None,
    ) -> None:
        self._client = client
        self.prefix = prefix
        self._module_factory = module_factory
        self._commands: list[_RegisteredCommand] = []
        self._initialized = False
        self.command_execution_failed: list[
            Callable[[BaseException, GatewayMessage], Awaitable[None]]
        ] = []

    def add_module(self, module_type: Type[ModuleBase]) -> None:
        if not issubclass(module_type, ModuleBase) or inspect.isabstract(module_type):
            raise TypeError(f"{module_type} must be a non-abstract subclass of ModuleBase")
        for _name, method in inspect.getmembers(module_type, predicate=inspect.isfunction):
            cmd_name = getattr(method, "_voice_command", None)
            if cmd_name is None:
                continue
            aliases = getattr(method, "_voice_aliases", ())
            self._commands.append(_RegisteredCommand(cmd_name, aliases, method, module_type))

    def add_modules_from_module(self, module: Any) -> None:
        """Register every ModuleBase subclass found in a Python module object."""
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, ModuleBase) and obj is not ModuleBase and not inspect.isabstract(obj):
                self.add_module(obj)

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._client.message_created.append(self._dispatch_async)

    async def _dispatch_async(self, message: GatewayMessage) -> None:
        if message.author.is_bot:
            return
        if not self.prefix or not message.content.startswith(self.prefix):
            return
        tokens = tokenize(message.content[len(self.prefix) :])
        if not tokens:
            return
        command = next((c for c in self._commands if c.matches(tokens[0])), None)
        if command is None:
            return

        if self._module_factory is not None:
            module = self._module_factory(command.module_type)
        else:
            module = command.module_type()
        module.context = CommandContext(self._client, message)

        try:
            args = self._build_arguments(command.method, tokens[1:])
            result = command.method(module, *args)
            if inspect.isawaitable(result):
                await result
        except Exception as ex:  # noqa: BLE001
            for handler in list(self.command_execution_failed):
                await handler(ex, message)

    def _build_arguments(self, method: Callable[..., Any], tokens: Sequence[str]) -> list[Any]:
        sig = inspect.signature(method)
        params = [p for p in sig.parameters.values() if p.name != "self"]
        if not params:
            return []
        hints = {}
        try:
            hints = get_type_hints(method)
        except Exception:  # noqa: BLE001
            hints = {p.name: p.annotation for p in params if p.annotation is not inspect.Parameter.empty}

        args: list[Any] = []
        for i, param in enumerate(params):
            target = hints.get(param.name, str)
            if target is inspect.Parameter.empty:
                target = str
            is_trailing_string = i == len(params) - 1 and target is str
            if is_trailing_string:
                raw = " ".join(tokens[i:]) if i < len(tokens) else None
            else:
                raw = tokens[i] if i < len(tokens) else None
            args.append(convert_argument(raw, target if isinstance(target, type) else str))
        return args


__all__ = [
    "CommandContext",
    "CommandService",
    "ModuleBase",
    "alias",
    "command",
    "convert_argument",
    "tokenize",
]
