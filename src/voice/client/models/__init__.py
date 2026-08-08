"""Public model types mirroring Voice.Bot.Client.Net.Models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Mapping, Optional, Sequence

from voice.client.intents import BotIntents


class UserStatus(IntEnum):
    ONLINE = 0
    OFFLINE = 1
    DO_NOT_DISTURB = 2
    INVISIBLE = 3


class BotTypingState(IntEnum):
    THINKING = 0
    EXPLORED = 1
    PROCESSING = 2
    REVIEWED = 3
    OPENED = 4
    RE_SEARCH = 5
    FETCHED = 6


class ChannelType(IntEnum):
    TEXT = 0
    VOICE = 1
    DIRECT_MESSAGE = 2
    GROUP_MESSAGE = 3
    TRIBUNE = 4
    POSTS = 5
    FORUM = 6
    EVENTS = 7


class CommandOptionType(IntEnum):
    STRING = 0
    INTEGER = 1
    BOOLEAN = 2
    USER = 3
    CHANNEL = 4
    ROLE = 5
    NUMBER = 6
    SUB_COMMAND = 7
    SUB_COMMAND_GROUP = 8


class InteractionResponseKind(IntEnum):
    CHANNEL_MESSAGE = 0
    DEFERRED_CHANNEL_MESSAGE = 1
    UPDATE_MESSAGE = 2
    DEFERRED_UPDATE_MESSAGE = 3
    MODAL = 4
    AUTOCOMPLETE_RESULT = 5


class InteractionType(IntEnum):
    APPLICATION_COMMAND = 0
    MESSAGE_COMPONENT = 1
    MODAL_SUBMIT = 2
    APPLICATION_COMMAND_AUTOCOMPLETE = 3


def _ts_to_datetime(ts: Any) -> datetime:
    if ts is None:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    if hasattr(ts, "ToDatetime"):
        dt = ts.ToDatetime()
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    seconds = getattr(ts, "seconds", 0) or 0
    nanos = getattr(ts, "nanos", 0) or 0
    return datetime.fromtimestamp(seconds + nanos / 1e9, tz=timezone.utc)


def _opt_str(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    return value


@dataclass(frozen=True, slots=True)
class Bot:
    id: str
    owner_id: str
    username: str
    display_name: str | None
    description: str | None
    avatar_id: str | None
    status: UserStatus
    is_enabled: bool
    created_at: datetime
    updated_at: datetime
    intents: BotIntents

    @classmethod
    def from_grpc(cls, grpc: Any) -> Bot:
        return cls(
            id=grpc.id,
            owner_id=grpc.owner_id,
            username=grpc.username,
            display_name=_opt_str(grpc.display_name),
            description=_opt_str(grpc.description),
            avatar_id=_opt_str(grpc.avatar_id),
            status=UserStatus(int(grpc.user_status)),
            is_enabled=grpc.is_enabled,
            created_at=_ts_to_datetime(grpc.created_at),
            updated_at=_ts_to_datetime(grpc.updated_at),
            intents=BotIntents(int(grpc.intents)),
        )


@dataclass(frozen=True, slots=True)
class User:
    id: str
    username: str
    email: str
    display_name: str | None
    description: str | None
    preferred_language: str | None
    created_at: datetime
    updated_at: datetime
    last_activity: datetime
    is_confirmed: bool
    is_bot: bool
    subscription_type: str
    avatar_id: str | None
    banner_id: str | None
    status: UserStatus

    @classmethod
    def from_grpc(cls, grpc: Any) -> User:
        return cls(
            id=grpc.id,
            username=grpc.username,
            email=grpc.email,
            display_name=_opt_str(grpc.display_name),
            description=_opt_str(grpc.description),
            preferred_language=_opt_str(grpc.preferred_language),
            created_at=_ts_to_datetime(grpc.created_at),
            updated_at=_ts_to_datetime(grpc.updated_at),
            last_activity=_ts_to_datetime(grpc.last_activity),
            is_confirmed=grpc.is_confirmed,
            is_bot=grpc.is_bot,
            subscription_type=grpc.subscription_type,
            avatar_id=_opt_str(grpc.avatar_id),
            banner_id=_opt_str(grpc.banner_id),
            status=UserStatus(int(grpc.user_status)),
        )


@dataclass(frozen=True, slots=True)
class MessageInfo:
    id: str
    channel_id: str
    content: str
    author_id: str
    created_at: datetime
    updated_at: datetime
    is_edited: bool
    is_deleted: bool
    reply_to: str | None
    reactions: Mapping[str, Sequence[str]]
    components_json: str | None = None

    @classmethod
    def from_grpc(cls, grpc: Any) -> MessageInfo:
        reactions = {
            key: list(value.user_ids)
            for key, value in grpc.reactions.items()
        }
        components = None
        try:
            if grpc.HasField("components_json"):
                components = grpc.components_json
        except ValueError:
            # proto3 non-optional string
            components = grpc.components_json or None
        return cls(
            id=grpc.id,
            channel_id=grpc.channel_id,
            content=grpc.content,
            author_id=grpc.author_id,
            created_at=_ts_to_datetime(grpc.created_at),
            updated_at=_ts_to_datetime(grpc.updated_at),
            is_edited=grpc.is_edited,
            is_deleted=grpc.is_deleted,
            reply_to=_opt_str(grpc.reply_to),
            reactions=reactions,
            components_json=components,
        )


@dataclass(frozen=True, slots=True)
class BotGroupInfo:
    id: str
    owner_id: str
    name: str
    created_at: datetime
    avatar_id: str | None
    banner_id: str | None

    @classmethod
    def from_grpc(cls, grpc: Any) -> BotGroupInfo:
        return cls(
            id=grpc.id,
            owner_id=grpc.owner_id,
            name=grpc.name,
            created_at=_ts_to_datetime(grpc.created_at),
            avatar_id=_opt_str(grpc.avatar_id),
            banner_id=_opt_str(grpc.banner_id),
        )


@dataclass(frozen=True, slots=True)
class BotChannelInfo:
    id: str
    category_id: str | None
    name: str
    type: ChannelType
    position: str

    @classmethod
    def from_grpc(cls, grpc: Any) -> BotChannelInfo:
        return cls(
            id=grpc.id,
            category_id=_opt_str(grpc.category_id),
            name=grpc.name,
            type=ChannelType(int(grpc.type)),
            position=grpc.position,
        )


@dataclass(frozen=True, slots=True)
class BotCategoryInfo:
    id: str
    name: str
    position: str
    channels: Sequence[BotChannelInfo]

    @classmethod
    def from_grpc(cls, grpc: Any) -> BotCategoryInfo:
        return cls(
            id=grpc.id,
            name=grpc.name,
            position=grpc.position,
            channels=[BotChannelInfo.from_grpc(c) for c in grpc.channels],
        )


@dataclass(frozen=True, slots=True)
class BotGroupDetails:
    id: str
    owner_id: str
    name: str
    created_at: datetime
    avatar_id: str | None
    banner_id: str | None
    categories: Sequence[BotCategoryInfo]

    @classmethod
    def from_grpc(cls, grpc: Any) -> BotGroupDetails:
        return cls(
            id=grpc.id,
            owner_id=grpc.owner_id,
            name=grpc.name,
            created_at=_ts_to_datetime(grpc.created_at),
            avatar_id=_opt_str(grpc.avatar_id),
            banner_id=_opt_str(grpc.banner_id),
            categories=[BotCategoryInfo.from_grpc(c) for c in grpc.categories],
        )


@dataclass(frozen=True, slots=True)
class BotChannelDetails:
    id: str
    group_id: str
    category_id: str | None
    name: str
    type: ChannelType
    position: str

    @classmethod
    def from_grpc(cls, grpc: Any) -> BotChannelDetails:
        return cls(
            id=grpc.id,
            group_id=grpc.group_id,
            category_id=_opt_str(grpc.category_id),
            name=grpc.name,
            type=ChannelType(int(grpc.type)),
            position=grpc.position,
        )


@dataclass(frozen=True, slots=True)
class BotRole:
    id: str
    group_id: str
    name: str
    position: str
    color: str
    permissions: int

    @classmethod
    def from_grpc(cls, grpc: Any) -> BotRole:
        return cls(
            id=grpc.id,
            group_id=grpc.group_id,
            name=grpc.name,
            position=grpc.position,
            color=grpc.color,
            permissions=int(grpc.permissions),
        )


@dataclass(frozen=True, slots=True)
class JoinVoiceChannelResult:
    token: str
    server_url: str

    @classmethod
    def from_grpc(cls, grpc: Any) -> JoinVoiceChannelResult:
        return cls(token=grpc.token, server_url=grpc.server_url)


@dataclass(frozen=True, slots=True)
class KickUserResult:
    group_id: str
    user_id: str
    success: bool

    @classmethod
    def from_grpc(cls, grpc: Any) -> KickUserResult:
        return cls(group_id=grpc.group_id, user_id=grpc.user_id, success=grpc.success)


@dataclass(frozen=True, slots=True)
class DeleteMessageResult:
    id: str
    success: bool

    @classmethod
    def from_grpc(cls, grpc: Any) -> DeleteMessageResult:
        return cls(id=grpc.id, success=grpc.success)


@dataclass(frozen=True, slots=True)
class DeleteChannelResult:
    id: str
    success: bool

    @classmethod
    def from_grpc(cls, grpc: Any) -> DeleteChannelResult:
        return cls(id=grpc.id, success=grpc.success)


@dataclass(frozen=True, slots=True)
class DeleteCategoryResult:
    id: str
    success: bool

    @classmethod
    def from_grpc(cls, grpc: Any) -> DeleteCategoryResult:
        return cls(id=grpc.id, success=grpc.success)


@dataclass(frozen=True, slots=True)
class CommandOptionDefinition:
    name: str
    description: str
    type: CommandOptionType
    required: bool = False
    autocomplete: bool = False

    def to_wire(self) -> Any:
        from voice.client._generated import interactions_pb2

        return interactions_pb2.CommandOption(
            name=self.name,
            description=self.description,
            type=int(self.type),
            required=self.required,
            autocomplete=self.autocomplete,
        )

    @classmethod
    def from_grpc(cls, grpc: Any) -> CommandOptionDefinition:
        return cls(
            name=grpc.name,
            description=grpc.description,
            type=CommandOptionType(int(grpc.type)),
            required=grpc.required,
            autocomplete=grpc.autocomplete,
        )


@dataclass(frozen=True, slots=True)
class BotCommandDefinition:
    id: str
    bot_id: str
    name: str
    description: str
    options: Sequence[CommandOptionDefinition]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_grpc(cls, grpc: Any) -> BotCommandDefinition:
        return cls(
            id=grpc.id,
            bot_id=grpc.bot_id,
            name=grpc.name,
            description=grpc.description,
            options=[CommandOptionDefinition.from_grpc(o) for o in grpc.options],
            created_at=_ts_to_datetime(grpc.created_at),
            updated_at=_ts_to_datetime(grpc.updated_at),
        )


@dataclass(frozen=True, slots=True)
class InteractionChoice:
    name: str
    value: str


@dataclass(frozen=True, slots=True)
class InteractionResponse:
    kind: InteractionResponseKind
    content: str | None = None
    components_json: str | None = None
    modal_json: str | None = None
    autocomplete_choices: Sequence[InteractionChoice] | Sequence[tuple[str, str]] | None = None
    ephemeral: bool = False
