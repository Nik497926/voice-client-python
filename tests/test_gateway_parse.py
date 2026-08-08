"""Tests for gateway event parser."""

import json
from datetime import datetime, timezone
from uuid import uuid4

from voice.client.gateway.parser import (
    CHANNEL_EVENTS,
    CHAT_EVENTS,
    GROUP_EVENTS,
    INTERACTION_EVENTS,
    parse_gateway_event,
)


def _envelope(event_type: str, payload: object, **extra) -> str:
    body = {
        "Type": event_type,
        "PayloadJson": json.dumps(payload),
        "Timestamp": 1_700_000_000_000,
        "GroupId": str(extra.get("group_id", "")),
        "ChatId": str(extra.get("chat_id", "")),
        "UserId": str(extra.get("user_id", "")),
        "MessageId": str(extra.get("message_id", "")),
    }
    return json.dumps(body)


def _author(author_id: str, username: str, is_bot: bool) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "Id": author_id,
        "Username": username,
        "Email": f"{username}@example.com",
        "DisplayName": None,
        "Description": None,
        "Status": None,
        "PreferredLanguage": None,
        "CreatedAt": now,
        "UpdatedAt": now,
        "LastActivity": now,
        "PresenceStatus": 0,
        "IsConfirmed": True,
        "IsBot": is_bot,
        "SubscriptionType": "None",
        "AvatarId": None,
        "BannerId": None,
    }


def test_parse_message_created():
    message_id = str(uuid4())
    channel_id = str(uuid4())
    author_id = str(uuid4())
    payload = {
        "Id": message_id,
        "ChannelId": channel_id,
        "Author": _author(author_id, "my_bot", True),
        "Content": "hello",
        "CreatedAt": datetime.now(timezone.utc).isoformat(),
        "UpdatedAt": datetime.now(timezone.utc).isoformat(),
        "IsEdited": False,
        "IsDeleted": False,
        "ReplyTo": None,
        "Attachments": [],
        "Reactions": {},
    }
    result = parse_gateway_event(CHAT_EVENTS, _envelope("MessageCreated", payload))
    assert result["kind"] == "message_created"
    assert result["message"].id == message_id
    assert result["message"].content == "hello"
    assert result["message"].author.id == author_id
    assert result["message"].author.is_bot is True


def test_parse_message_deleted():
    message_id = str(uuid4())
    result = parse_gateway_event(CHAT_EVENTS, _envelope("MessageDeleted", {"Id": message_id, "Success": True}))
    assert result["kind"] == "message_deleted"
    assert result["message_id"] == message_id
    assert result["success"] is True


def test_parse_reaction_added():
    message_id = str(uuid4())
    user_id = str(uuid4())
    payload = {
        "MessageId": message_id,
        "ChannelId": str(uuid4()),
        "UserId": user_id,
        "Emoji": "👍",
        "Added": True,
        "Reactions": {"👍": [user_id]},
    }
    result = parse_gateway_event(CHAT_EVENTS, _envelope("MessageReactionAdded", payload))
    assert result["kind"] == "reaction_added"
    assert result["reaction"].emoji == "👍"
    assert user_id in result["reaction"].reactions["👍"]


def test_parse_user_connected():
    group_id = str(uuid4())
    chat_id = str(uuid4())
    user_id = str(uuid4())
    payload = {"Id": user_id, "Username": "alice", "DisplayName": None, "AvatarId": None, "IsBot": False}
    result = parse_gateway_event(
        CHANNEL_EVENTS,
        _envelope("UserConnected", payload, group_id=group_id, chat_id=chat_id, user_id=user_id),
    )
    assert result["kind"] == "user_connected"
    assert result["event"].group_id == group_id
    assert result["event"].channel_id == chat_id
    assert result["event"].user_id == user_id
    assert result["event"].user.username == "alice"


def test_parse_user_status_changed():
    group_id = str(uuid4())
    user_id = str(uuid4())
    payload = {
        "UserId": user_id,
        "PresenceStatus": 2,
        "LastActivity": datetime.now(timezone.utc).isoformat(),
    }
    result = parse_gateway_event(
        GROUP_EVENTS,
        _envelope("UserStatusChanged", payload, group_id=group_id),
    )
    assert result["kind"] == "user_status_changed"
    assert result["event"].group_id == group_id
    assert result["event"].user_id == user_id
    assert int(result["event"].presence_status) == 2


def test_parse_interaction_created():
    interaction_id = str(uuid4())
    payload = {
        "InteractionId": interaction_id,
        "InvokingUserId": str(uuid4()),
        "ChannelId": str(uuid4()),
        "GroupId": str(uuid4()),
        "Type": 0,
        "Data": {"CommandName": "ping", "Options": {}},
    }
    result = parse_gateway_event(INTERACTION_EVENTS, _envelope("InteractionCreated", payload))
    assert result["kind"] == "interaction_created"
    assert result["event"].interaction_id == interaction_id
    assert result["event"].data.command_name == "ping"


def test_parse_unknown_type():
    result = parse_gateway_event(CHAT_EVENTS, _envelope("SomethingNew", {"x": 1}))
    assert result["kind"] == "unknown"
    assert result["event"].type == "SomethingNew"


def test_parse_bad_envelope():
    result = parse_gateway_event(CHAT_EVENTS, "not-json")
    assert result["kind"] == "parse_error"
