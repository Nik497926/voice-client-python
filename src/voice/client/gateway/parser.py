"""Pure (topic, json) -> parse result mapping."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from voice.client.events import (
    BotInteractionEvent,
    BotTypingEvent,
    ChannelPresenceEvent,
    GatewayMessage,
    GroupCategorySnapshot,
    GroupChannelSnapshot,
    GroupJoinedEvent,
    GroupSnapshot,
    InteractionData,
    MessageAttachment,
    MessageAuthor,
    MessageReactionEvent,
    TypingEvent,
    UnknownGatewayEvent,
    UserSnapshot,
    UserStatusChangedEvent,
)
from voice.client.gateway import CHANNEL_EVENTS, CHAT_EVENTS, GROUP_EVENTS, INTERACTION_EVENTS
from voice.client.models import BotTypingState, ChannelType, InteractionType, UserStatus


def _parse_dt(value: Any) -> datetime:
    if value is None:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.fromtimestamp(0, tz=timezone.utc)
    return datetime.fromtimestamp(0, tz=timezone.utc)


def _cid(value: Any) -> str:
    return "" if value is None else str(value)


def _author(data: dict[str, Any]) -> MessageAuthor:
    return MessageAuthor(
        id=_cid(data.get("Id") or data.get("id")),
        username=str(data.get("Username") or data.get("username") or ""),
        email=str(data.get("Email") or data.get("email") or ""),
        display_name=data.get("DisplayName") or data.get("displayName"),
        description=data.get("Description") or data.get("description"),
        status=data.get("Status") or data.get("status"),
        preferred_language=data.get("PreferredLanguage") or data.get("preferredLanguage"),
        created_at=_parse_dt(data.get("CreatedAt") or data.get("createdAt")),
        updated_at=_parse_dt(data.get("UpdatedAt") or data.get("updatedAt")),
        last_activity=_parse_dt(data.get("LastActivity") or data.get("lastActivity")),
        presence_status=UserStatus(int(data.get("PresenceStatus") or data.get("presenceStatus") or 0)),
        is_confirmed=bool(data.get("IsConfirmed") if "IsConfirmed" in data else data.get("isConfirmed", False)),
        is_bot=bool(data.get("IsBot") if "IsBot" in data else data.get("isBot", False)),
        subscription_type=str(data.get("SubscriptionType") or data.get("subscriptionType") or ""),
        avatar_id=_cid(data.get("AvatarId") or data.get("avatarId")) or None,
        banner_id=_cid(data.get("BannerId") or data.get("bannerId")) or None,
    )


def _gateway_message(payload: dict[str, Any]) -> GatewayMessage:
    author_raw = payload.get("Author") or payload.get("author") or {}
    attachments = []
    for a in payload.get("Attachments") or payload.get("attachments") or []:
        attachments.append(
            MessageAttachment(
                id=_cid(a.get("Id") or a.get("id")),
                uploader_id=_cid(a.get("UploaderId") or a.get("uploaderId")),
                file_name=str(a.get("FileName") or a.get("fileName") or ""),
                content_type=str(a.get("ContentType") or a.get("contentType") or ""),
                size_bytes=int(a.get("SizeBytes") or a.get("sizeBytes") or 0),
                status=str(a.get("Status") or a.get("status") or ""),
                download_url=str(a.get("DownloadUrl") or a.get("downloadUrl") or ""),
                expires_at=_parse_dt(a.get("ExpiresAt") or a.get("expiresAt")),
            )
        )
    reactions_raw = payload.get("Reactions") or payload.get("reactions") or {}
    reactions = {str(k): [str(x) for x in (v or [])] for k, v in reactions_raw.items()}
    reply = payload.get("ReplyTo") if "ReplyTo" in payload else payload.get("replyTo")
    return GatewayMessage(
        id=_cid(payload.get("Id") or payload.get("id")),
        channel_id=_cid(payload.get("ChannelId") or payload.get("channelId")),
        author=_author(author_raw),
        content=str(payload.get("Content") or payload.get("content") or ""),
        created_at=_parse_dt(payload.get("CreatedAt") or payload.get("createdAt")),
        updated_at=_parse_dt(payload.get("UpdatedAt") or payload.get("updatedAt")),
        is_edited=bool(payload.get("IsEdited") if "IsEdited" in payload else payload.get("isEdited", False)),
        is_deleted=bool(payload.get("IsDeleted") if "IsDeleted" in payload else payload.get("isDeleted", False)),
        reply_to=_cid(reply) or None,
        attachments=attachments,
        reactions=reactions,
    )


def _reaction(payload: dict[str, Any]) -> MessageReactionEvent:
    reactions_raw = payload.get("Reactions") or payload.get("reactions") or {}
    return MessageReactionEvent(
        message_id=_cid(payload.get("MessageId") or payload.get("messageId")),
        channel_id=_cid(payload.get("ChannelId") or payload.get("channelId")),
        user_id=_cid(payload.get("UserId") or payload.get("userId")),
        emoji=str(payload.get("Emoji") or payload.get("emoji") or ""),
        reactions={str(k): [str(x) for x in (v or [])] for k, v in reactions_raw.items()},
    )


def _user_snapshot(data: dict[str, Any]) -> UserSnapshot:
    return UserSnapshot(
        id=_cid(data.get("Id") or data.get("id")),
        username=data.get("Username") or data.get("username"),
        display_name=data.get("DisplayName") or data.get("displayName"),
        avatar_id=_cid(data.get("AvatarId") or data.get("avatarId")) or None,
        is_bot=bool(data.get("IsBot") if "IsBot" in data else data.get("isBot", False)),
    )


def _group_snapshot(data: dict[str, Any]) -> GroupSnapshot:
    categories = []
    for cat in data.get("Categories") or data.get("categories") or []:
        channels = []
        for ch in cat.get("Channels") or cat.get("channels") or []:
            users = [_user_snapshot(u) for u in ch.get("Users") or ch.get("users") or []]
            channels.append(
                GroupChannelSnapshot(
                    id=_cid(ch.get("Id") or ch.get("id")),
                    category_id=_cid(ch.get("CategoryId") or ch.get("categoryId")) or None,
                    name=str(ch.get("Name") or ch.get("name") or ""),
                    type=ChannelType(int(ch.get("Type") or ch.get("type") or 0)),
                    position=str(ch.get("Position") or ch.get("position") or ""),
                    users=users,
                )
            )
        categories.append(
            GroupCategorySnapshot(
                id=_cid(cat.get("Id") or cat.get("id")),
                name=str(cat.get("Name") or cat.get("name") or ""),
                position=str(cat.get("Position") or cat.get("position") or ""),
                channels=channels,
            )
        )
    return GroupSnapshot(
        id=_cid(data.get("Id") or data.get("id")),
        owner_id=_cid(data.get("OwnerId") or data.get("ownerId")),
        name=str(data.get("Name") or data.get("name") or ""),
        created_at=_parse_dt(data.get("CreatedAt") or data.get("createdAt")),
        avatar_id=_cid(data.get("AvatarId") or data.get("avatarId")) or None,
        banner_id=_cid(data.get("BannerId") or data.get("bannerId")) or None,
        categories=categories,
    )


def _interaction(payload: dict[str, Any]) -> BotInteractionEvent:
    data = payload.get("Data") or payload.get("data") or {}
    options = data.get("Options") or data.get("options")
    if isinstance(options, dict):
        options = {str(k): str(v) for k, v in options.items()}
    else:
        options = None
    modal = data.get("ModalFields") or data.get("modalFields")
    if isinstance(modal, dict):
        modal = {str(k): str(v) for k, v in modal.items()}
    else:
        modal = None
    values = data.get("Values") or data.get("values")
    return BotInteractionEvent(
        interaction_id=_cid(payload.get("InteractionId") or payload.get("interactionId")),
        invoking_user_id=_cid(payload.get("InvokingUserId") or payload.get("invokingUserId")),
        channel_id=_cid(payload.get("ChannelId") or payload.get("channelId")),
        group_id=_cid(payload.get("GroupId") or payload.get("groupId")),
        type=InteractionType(int(payload.get("Type") if payload.get("Type") is not None else payload.get("type") or 0)),
        data=InteractionData(
            command_name=data.get("CommandName") or data.get("commandName"),
            options=options,
            custom_id=data.get("CustomId") or data.get("customId"),
            values=[str(v) for v in values] if values else None,
            focused_option=data.get("FocusedOption") or data.get("focusedOption"),
            modal_fields=modal,
        ),
    )


def parse_gateway_event(topic: str, raw: str) -> dict[str, Any]:
    try:
        envelope = json.loads(raw)
    except Exception as ex:  # noqa: BLE001
        return {"kind": "parse_error", "error": ex}

    etype = str(envelope.get("Type") or envelope.get("type") or "")
    payload_json = envelope.get("PayloadJson") or envelope.get("payloadJson") or "{}"
    try:
        payload = json.loads(payload_json) if isinstance(payload_json, str) else (payload_json or {})
    except Exception as ex:  # noqa: BLE001
        return {"kind": "parse_error", "error": ex}

    group_id = _cid(envelope.get("GroupId") or envelope.get("groupId"))
    chat_id = _cid(envelope.get("ChatId") or envelope.get("chatId"))
    user_id = _cid(envelope.get("UserId") or envelope.get("userId"))
    timestamp = int(envelope.get("Timestamp") or envelope.get("timestamp") or 0)

    try:
        if topic == CHAT_EVENTS:
            if etype == "MessageCreated":
                return {"kind": "message_created", "message": _gateway_message(payload)}
            if etype == "MessageUpdated":
                return {"kind": "message_updated", "message": _gateway_message(payload)}
            if etype == "MessageDeleted":
                return {
                    "kind": "message_deleted",
                    "message_id": _cid(payload.get("Id") or payload.get("id")),
                    "success": bool(payload.get("Success") if "Success" in payload else payload.get("success", False)),
                }
            if etype == "MessageReactionAdded":
                return {"kind": "reaction_added", "reaction": _reaction(payload)}
            if etype == "MessageReactionRemoved":
                return {"kind": "reaction_removed", "reaction": _reaction(payload)}
            if etype == "UserTyping":
                return {
                    "kind": "user_typing",
                    "event": TypingEvent(
                        channel_id=_cid(payload.get("ChannelId") or payload.get("channelId") or chat_id),
                        user_id=_cid(payload.get("UserId") or payload.get("userId") or user_id),
                        username=str(payload.get("Username") or payload.get("username") or ""),
                        is_typing=bool(
                            payload.get("IsTyping") if "IsTyping" in payload else payload.get("isTyping", True)
                        ),
                    ),
                }
            if etype == "BotTyping":
                return {
                    "kind": "bot_typing",
                    "event": BotTypingEvent(
                        channel_id=_cid(payload.get("ChannelId") or payload.get("channelId") or chat_id),
                        bot_id=_cid(payload.get("BotId") or payload.get("botId") or user_id),
                        username=str(payload.get("Username") or payload.get("username") or ""),
                        state=BotTypingState(int(payload.get("State") or payload.get("state") or 0)),
                        is_active=bool(
                            payload.get("IsActive") if "IsActive" in payload else payload.get("isActive", True)
                        ),
                    ),
                }
        elif topic == CHANNEL_EVENTS:
            user = _user_snapshot(payload if isinstance(payload, dict) else {})
            event = ChannelPresenceEvent(
                group_id=group_id, channel_id=chat_id, user_id=user_id or user.id, user=user
            )
            if etype == "UserConnected":
                return {"kind": "user_connected", "event": event}
            if etype == "UserDisconnected":
                return {"kind": "user_disconnected", "event": event}
        elif topic == GROUP_EVENTS:
            if etype == "UserJoined":
                return {
                    "kind": "user_joined_group",
                    "event": GroupJoinedEvent(group_id=group_id, user_id=user_id, group=_group_snapshot(payload)),
                }
            if etype == "UserStatusChanged":
                return {
                    "kind": "user_status_changed",
                    "event": UserStatusChangedEvent(
                        group_id=group_id,
                        user_id=_cid(payload.get("UserId") or payload.get("userId") or user_id),
                        presence_status=UserStatus(
                            int(payload.get("PresenceStatus") or payload.get("presenceStatus") or 0)
                        ),
                        last_activity=_parse_dt(payload.get("LastActivity") or payload.get("lastActivity")),
                    ),
                }
        elif topic == INTERACTION_EVENTS:
            if etype == "InteractionCreated":
                return {"kind": "interaction_created", "event": _interaction(payload)}

        raw_payload = payload_json if isinstance(payload_json, str) else json.dumps(payload_json)
        return {
            "kind": "unknown",
            "event": UnknownGatewayEvent(
                topic=topic, type=etype, raw_payload_json=raw_payload, timestamp=timestamp
            ),
        }
    except Exception as ex:  # noqa: BLE001
        return {"kind": "parse_error", "error": ex}
