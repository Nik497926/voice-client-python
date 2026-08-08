"""Slash / component / modal / autocomplete interaction framework."""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable, Optional, Sequence, Type, get_type_hints

from voice.client.commands import convert_argument
from voice.client.components import ComponentBuilder, ModalBuilder
from voice.client.events import BotInteractionEvent
from voice.client.models import (
    CommandOptionDefinition,
    CommandOptionType,
    InteractionChoice,
    InteractionResponse,
    InteractionResponseKind,
    InteractionType,
    MessageInfo,
)

logger = logging.getLogger(__name__)


def slash_command(name: str, description: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn._voice_slash = (name, description)  # type: ignore[attr-defined]
        return fn

    return decorator


def slash_command_option(
    description: str,
    *,
    name: str | None = None,
    required: bool = False,
    autocomplete: bool = False,
) -> Callable[[Any], Any]:
    """Decorator for slash-command parameters (applied to the function with param metadata).

    Prefer annotating via ``slash_command`` handler signature and calling
    ``slash_option(...)`` as a parameter default marker, or use this as::

        @slash_command("ping", "Ping")
        @slash_command_option("Target user", name="user", required=True)
        async def ping(self, user: str): ...

    Multiple ``@slash_command_option`` stack in reverse order of application (bottom-up).
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        options = list(getattr(fn, "_voice_slash_options", []))
        options.insert(0, {"description": description, "name": name, "required": required, "autocomplete": autocomplete})
        fn._voice_slash_options = options  # type: ignore[attr-defined]
        return fn

    return decorator


def component_interaction(custom_id_pattern: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn._voice_component = custom_id_pattern  # type: ignore[attr-defined]
        return fn

    return decorator


def modal_interaction(custom_id_pattern: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn._voice_modal = custom_id_pattern  # type: ignore[attr-defined]
        return fn

    return decorator


def autocomplete_handler(command_name: str, option_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn._voice_autocomplete = (command_name, option_name)  # type: ignore[attr-defined]
        return fn

    return decorator


class InteractionContext:
    def __init__(self, client: Any, interaction: BotInteractionEvent) -> None:
        self.client = client
        self.interaction = interaction

    async def respond_async(
        self,
        content: str,
        *,
        ephemeral: bool = False,
        components: ComponentBuilder | None = None,
    ) -> None:
        await self.client.respond_to_interaction_async(
            self.interaction.interaction_id,
            InteractionResponse(
                kind=InteractionResponseKind.CHANNEL_MESSAGE,
                content=content,
                components_json=components.build() if components else None,
                ephemeral=ephemeral,
            ),
        )

    async def defer_async(self, *, ephemeral: bool = False) -> None:
        await self.client.respond_to_interaction_async(
            self.interaction.interaction_id,
            InteractionResponse(kind=InteractionResponseKind.DEFERRED_CHANNEL_MESSAGE, ephemeral=ephemeral),
        )

    async def update_async(self, content: str, *, components: ComponentBuilder | None = None) -> None:
        await self.client.respond_to_interaction_async(
            self.interaction.interaction_id,
            InteractionResponse(
                kind=InteractionResponseKind.UPDATE_MESSAGE,
                content=content,
                components_json=components.build() if components else None,
            ),
        )

    async def respond_with_modal_async(self, modal: ModalBuilder | str) -> None:
        modal_json = modal if isinstance(modal, str) else modal.build()
        await self.client.respond_to_interaction_async(
            self.interaction.interaction_id,
            InteractionResponse(kind=InteractionResponseKind.MODAL, modal_json=modal_json),
        )

    async def respond_with_autocomplete_async(
        self,
        choices: Sequence[InteractionChoice] | Sequence[tuple[str, str]],
    ) -> None:
        await self.client.respond_to_interaction_async(
            self.interaction.interaction_id,
            InteractionResponse(
                kind=InteractionResponseKind.AUTOCOMPLETE_RESULT,
                autocomplete_choices=choices,
            ),
        )

    async def followup_async(self, content: str, *, components: ComponentBuilder | None = None) -> MessageInfo:
        return await self.client.send_interaction_followup_async(
            self.interaction.interaction_id, content, components=components
        )


class InteractionModuleBase:
    context: InteractionContext

    async def respond_async(
        self, content: str, *, ephemeral: bool = False, components: ComponentBuilder | None = None
    ) -> None:
        await self.context.respond_async(content, ephemeral=ephemeral, components=components)

    async def defer_async(self, *, ephemeral: bool = False) -> None:
        await self.context.defer_async(ephemeral=ephemeral)

    async def update_async(self, content: str, *, components: ComponentBuilder | None = None) -> None:
        await self.context.update_async(content, components=components)

    async def respond_with_modal_async(self, modal: ModalBuilder | str) -> None:
        await self.context.respond_with_modal_async(modal)

    async def respond_with_autocomplete_async(
        self, choices: Sequence[InteractionChoice] | Sequence[tuple[str, str]]
    ) -> None:
        await self.context.respond_with_autocomplete_async(choices)

    async def followup_async(self, content: str, *, components: ComponentBuilder | None = None) -> MessageInfo:
        return await self.context.followup_async(content, components=components)


class HandlerKind(str, Enum):
    SLASH = "slash"
    COMPONENT = "component"
    MODAL = "modal"
    AUTOCOMPLETE = "autocomplete"


@dataclass
class _RegisteredHandler:
    kind: HandlerKind
    match: str
    option_name: str | None
    method: Callable[..., Any]
    module_type: Type[InteractionModuleBase]


class InteractionService:
    def __init__(
        self,
        client: Any,
        module_factory: Callable[[Type[InteractionModuleBase]], InteractionModuleBase] | None = None,
    ) -> None:
        self._client = client
        self._module_factory = module_factory
        self._handlers: list[_RegisteredHandler] = []
        self._initialized = False

    def add_module(self, module_type: Type[InteractionModuleBase]) -> None:
        if not issubclass(module_type, InteractionModuleBase) or inspect.isabstract(module_type):
            raise TypeError(f"{module_type} must be a non-abstract subclass of InteractionModuleBase")

        for _name, method in inspect.getmembers(module_type, predicate=inspect.isfunction):
            slash = getattr(method, "_voice_slash", None)
            if slash is not None:
                self._handlers.append(
                    _RegisteredHandler(HandlerKind.SLASH, slash[0], None, method, module_type)
                )
            component = getattr(method, "_voice_component", None)
            if component is not None:
                self._handlers.append(
                    _RegisteredHandler(HandlerKind.COMPONENT, component, None, method, module_type)
                )
            modal = getattr(method, "_voice_modal", None)
            if modal is not None:
                self._handlers.append(
                    _RegisteredHandler(HandlerKind.MODAL, modal, None, method, module_type)
                )
            autocomplete = getattr(method, "_voice_autocomplete", None)
            if autocomplete is not None:
                self._handlers.append(
                    _RegisteredHandler(
                        HandlerKind.AUTOCOMPLETE, autocomplete[0], autocomplete[1], method, module_type
                    )
                )

    def add_modules_from_module(self, module: Any) -> None:
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, InteractionModuleBase)
                and obj is not InteractionModuleBase
                and not inspect.isabstract(obj)
            ):
                self.add_module(obj)

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._client.interaction_created.append(self._dispatch_async)

    async def register_commands_async(self, *, delete_missing: bool = True) -> None:
        me = await self._client.get_me_async()
        declared = [
            self._build_declared_command(h)
            for h in self._handlers
            if h.kind == HandlerKind.SLASH
        ]
        existing = await self._client.get_bot_commands_async(me.id)
        existing_by_name = {c.name: c for c in existing}

        for command in declared:
            existing_command = existing_by_name.get(command["name"])
            if existing_command is not None:
                if not self._is_same_definition(existing_command, command):
                    await self._client.update_command_async(
                        me.id,
                        existing_command.id,
                        command["name"],
                        command["description"],
                        options=command["options"],
                    )
            else:
                await self._client.register_command_async(
                    me.id,
                    command["name"],
                    command["description"],
                    options=command["options"],
                )

        if delete_missing:
            declared_names = {d["name"] for d in declared}
            for stale in existing:
                if stale.name not in declared_names:
                    await self._client.delete_command_async(me.id, stale.id)

    def _build_declared_command(self, handler: _RegisteredHandler) -> dict[str, Any]:
        name, description = handler.method._voice_slash  # type: ignore[attr-defined]
        stacked = list(getattr(handler.method, "_voice_slash_options", []))
        sig = inspect.signature(handler.method)
        params = [p for p in sig.parameters.values() if p.name != "self"]
        options: list[CommandOptionDefinition] = []
        for i, param in enumerate(params):
            meta = stacked[i] if i < len(stacked) else {
                "description": param.name,
                "name": None,
                "required": False,
                "autocomplete": False,
            }
            option_name = meta.get("name") or param.name.lower()
            hints = {}
            try:
                hints = get_type_hints(handler.method)
            except Exception:  # noqa: BLE001
                pass
            clr = hints.get(param.name, str)
            options.append(
                CommandOptionDefinition(
                    name=option_name,
                    description=meta["description"],
                    type=self._infer_option_type(clr if isinstance(clr, type) else str),
                    required=bool(meta.get("required")),
                    autocomplete=bool(meta.get("autocomplete")),
                )
            )
        return {"name": name, "description": description, "options": options}

    @staticmethod
    def _infer_option_type(clr_type: type) -> CommandOptionType:
        if clr_type in (int,):
            return CommandOptionType.INTEGER
        if clr_type is bool:
            return CommandOptionType.BOOLEAN
        if clr_type is float:
            return CommandOptionType.NUMBER
        return CommandOptionType.STRING

    @staticmethod
    def _is_same_definition(existing: Any, declared: dict[str, Any]) -> bool:
        if existing.description != declared["description"]:
            return False
        existing_opts = [
            (o.name, o.description, int(o.type), o.required, o.autocomplete) for o in existing.options
        ]
        declared_opts = [
            (o.name, o.description, int(o.type), o.required, o.autocomplete) for o in declared["options"]
        ]
        return existing_opts == declared_opts

    async def _dispatch_async(self, interaction: BotInteractionEvent) -> None:
        match: tuple[_RegisteredHandler, str | None] | None = None
        if interaction.type == InteractionType.APPLICATION_COMMAND:
            match = self._find_by_name(HandlerKind.SLASH, interaction.data.command_name)
        elif interaction.type == InteractionType.MESSAGE_COMPONENT:
            match = self._find_by_custom_id(HandlerKind.COMPONENT, interaction.data.custom_id)
        elif interaction.type == InteractionType.MODAL_SUBMIT:
            match = self._find_by_custom_id(HandlerKind.MODAL, interaction.data.custom_id)
        elif interaction.type == InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE:
            match = self._find_autocomplete(interaction.data.command_name, interaction.data.focused_option)

        if match is None:
            return

        handler, capture = match
        if self._module_factory is not None:
            module = self._module_factory(handler.module_type)
        else:
            module = handler.module_type()
        module.context = InteractionContext(self._client, interaction)
        args = self._build_arguments(handler, interaction, capture)
        result = handler.method(module, *args)
        if inspect.isawaitable(result):
            await result

    def _find_by_name(self, kind: HandlerKind, name: str | None) -> tuple[_RegisteredHandler, str | None] | None:
        if not name:
            return None
        for handler in self._handlers:
            if handler.kind == kind and handler.match == name:
                return handler, None
        return None

    def _find_by_custom_id(
        self, kind: HandlerKind, custom_id: str | None
    ) -> tuple[_RegisteredHandler, str | None] | None:
        if not custom_id:
            return None
        for handler in self._handlers:
            if handler.kind != kind:
                continue
            ok, capture = self._try_match_custom_id(handler.match, custom_id)
            if ok:
                return handler, capture
        return None

    def _find_autocomplete(
        self, command_name: str | None, focused_option: str | None
    ) -> tuple[_RegisteredHandler, str | None] | None:
        if not command_name or not focused_option:
            return None
        for handler in self._handlers:
            if (
                handler.kind == HandlerKind.AUTOCOMPLETE
                and handler.match == command_name
                and handler.option_name == focused_option
            ):
                return handler, None
        return None

    @staticmethod
    def _try_match_custom_id(pattern: str, custom_id: str) -> tuple[bool, str | None]:
        star = pattern.find("*")
        if star < 0:
            return pattern == custom_id, None
        prefix = pattern[:star]
        if not custom_id.startswith(prefix):
            return False, None
        return True, custom_id[len(prefix) :]

    def _build_arguments(
        self,
        handler: _RegisteredHandler,
        interaction: BotInteractionEvent,
        wildcard_capture: str | None,
    ) -> list[Any]:
        sig = inspect.signature(handler.method)
        params = [p for p in sig.parameters.values() if p.name != "self"]
        if not params:
            return []
        hints = {}
        try:
            hints = get_type_hints(handler.method)
        except Exception:  # noqa: BLE001
            pass
        stacked = list(getattr(handler.method, "_voice_slash_options", []))
        args: list[Any] = []
        for i, param in enumerate(params):
            meta = stacked[i] if i < len(stacked) else {}
            name = meta.get("name") if isinstance(meta, dict) else None
            name = name or param.name.lower()
            raw: str | None
            if handler.kind == HandlerKind.SLASH:
                raw = (interaction.data.options or {}).get(name)
            elif handler.kind == HandlerKind.COMPONENT:
                raw = wildcard_capture
                if raw is None and interaction.data.values:
                    raw = interaction.data.values[0]
            elif handler.kind == HandlerKind.MODAL:
                raw = (interaction.data.modal_fields or {}).get(name)
                if raw is None:
                    raw = wildcard_capture
            elif handler.kind == HandlerKind.AUTOCOMPLETE:
                raw = (interaction.data.options or {}).get(name) or interaction.data.focused_option
            else:
                raw = None
            target = hints.get(param.name, str)
            if not isinstance(target, type):
                target = str
            args.append(convert_argument(raw, target))
        return args


__all__ = [
    "InteractionContext",
    "InteractionModuleBase",
    "InteractionService",
    "autocomplete_handler",
    "component_interaction",
    "modal_interaction",
    "slash_command",
    "slash_command_option",
]
