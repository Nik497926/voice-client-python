"""Gateway event DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Optional, Sequence

from voice.client.models import BotTypingState, ChannelType, InteractionType, UserStatus


@dataclass(frozen=True, slots=True)
class MessageAuthor:
    id: str
    username: str
    email: str
    display_name: str | None
    description: str | None
    status: str | None
    preferred_language: str | None
    created_at: datetime
    updated_at: datetime
    last_activity: datetime
    presence_status: UserStatus
    is_confirmed: bool
    is_bot: bool
    subscription_type: str
    avatar_id: str | None
    banner_id: str | None


@dataclass(frozen=True, slots=True)
class MessageAttachment:
    id: str
    uploader_id: str
    file_name: str
    content_type: str
    size_bytes: int
    status: str
    download_url: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class GatewayMessage:
    id: str
    channel_id: str
    author: MessageAuthor
    content: str
    created_at: datetime
    updated_at: datetime
    is_edited: bool
    is_deleted: bool
    reply_to: str | None
    attachments: Sequence[MessageAttachment]
    reactions: Mapping[str, Sequence[str]]


@dataclass(frozen=True, slots=True)
class MessageReactionEvent:
    message_id: str
    channel_id: str
    user_id: str
    emoji: str
    reactions: Mapping[str, Sequence[str]]


@dataclass(frozen=True, slots=True)
class TypingEvent:
    channel_id: str
    user_id: str
    username: str
    is_typing: bool


@dataclass(frozen=True, slots=True)
class BotTypingEvent:
    channel_id: str
    bot_id: str
    username: str
    state: BotTypingState
    is_active: bool


@dataclass(frozen=True, slots=True)
class UserSnapshot:
    id: str
    username: str | None
    display_name: str | None
    avatar_id: str | None
    is_bot: bool


@dataclass(frozen=True, slots=True)
class ChannelPresenceEvent:
    group_id: str
    channel_id: str
    user_id: str
    user: UserSnapshot


@dataclass(frozen=True, slots=True)
class GroupChannelSnapshot:
    id: str
    category_id: str | None
    name: str
    type: ChannelType
    position: str
    users: Sequence[UserSnapshot]


@dataclass(frozen=True, slots=True)
class GroupCategorySnapshot:
    id: str
    name: str
    position: str
    channels: Sequence[GroupChannelSnapshot]


@dataclass(frozen=True, slots=True)
class GroupSnapshot:
    id: str
    owner_id: str
    name: str
    created_at: datetime
    avatar_id: str | None
    banner_id: str | None
    categories: Sequence[GroupCategorySnapshot]


@dataclass(frozen=True, slots=True)
class GroupJoinedEvent:
    group_id: str
    user_id: str
    group: GroupSnapshot


@dataclass(frozen=True, slots=True)
class UserStatusChangedEvent:
    group_id: str
    user_id: str
    presence_status: UserStatus
    last_activity: datetime


@dataclass(frozen=True, slots=True)
class InteractionData:
    command_name: str | None
    options: Mapping[str, str] | None
    custom_id: str | None
    values: Sequence[str] | None
    focused_option: str | None
    modal_fields: Mapping[str, str] | None


@dataclass(frozen=True, slots=True)
class BotInteractionEvent:
    interaction_id: str
    invoking_user_id: str
    channel_id: str
    group_id: str
    type: InteractionType
    data: InteractionData


@dataclass(frozen=True, slots=True)
class UnknownGatewayEvent:
    topic: str
    type: str
    raw_payload_json: str
    timestamp: int
