"""BotClient facade."""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Optional, Sequence

from voice.client._generated import bots_pb2, interactions_pb2
from voice.client.components import ComponentBuilder
from voice.client.events import (
    BotInteractionEvent,
    BotTypingEvent,
    ChannelPresenceEvent,
    GatewayMessage,
    GroupJoinedEvent,
    MessageReactionEvent,
    TypingEvent,
    UnknownGatewayEvent,
    UserStatusChangedEvent,
)
from voice.client.gateway import SignalRBotGatewayConnection
from voice.client.gateway.parser import parse_gateway_event
from voice.client.models import (
    Bot,
    BotCategoryInfo,
    BotChannelDetails,
    BotChannelInfo,
    BotCommandDefinition,
    BotGroupDetails,
    BotGroupInfo,
    BotRole,
    BotTypingState,
    ChannelType,
    CommandOptionDefinition,
    DeleteCategoryResult,
    DeleteChannelResult,
    DeleteMessageResult,
    InteractionChoice,
    InteractionResponse,
    InteractionResponseKind,
    JoinVoiceChannelResult,
    KickUserResult,
    MessageInfo,
    User,
    UserStatus,
)
from voice.client.options import BotClientOptions
from voice.client.transport import GrpcBotsApiTransport, GrpcInteractionsAdminTransport

AsyncHandler = Callable[..., Awaitable[None]]


class BotClient:
    """Typed facade over BotsApi + InteractionsApi + SignalR gateway."""

    def __init__(
        self,
        transport: GrpcBotsApiTransport,
        gateway: SignalRBotGatewayConnection,
        interactions_admin: GrpcInteractionsAdminTransport,
    ) -> None:
        self._transport = transport
        self._gateway = gateway
        self._interactions_admin = interactions_admin

        self.message_created: list[Callable[[GatewayMessage], Awaitable[None]]] = []
        self.message_updated: list[Callable[[GatewayMessage], Awaitable[None]]] = []
        self.message_deleted: list[Callable[[str, bool], Awaitable[None]]] = []
        self.reaction_added: list[Callable[[MessageReactionEvent], Awaitable[None]]] = []
        self.reaction_removed: list[Callable[[MessageReactionEvent], Awaitable[None]]] = []
        self.user_typing: list[Callable[[TypingEvent], Awaitable[None]]] = []
        self.bot_typing: list[Callable[[BotTypingEvent], Awaitable[None]]] = []
        self.user_connected: list[Callable[[ChannelPresenceEvent], Awaitable[None]]] = []
        self.user_disconnected: list[Callable[[ChannelPresenceEvent], Awaitable[None]]] = []
        self.user_joined_group: list[Callable[[GroupJoinedEvent], Awaitable[None]]] = []
        self.user_status_changed: list[Callable[[UserStatusChangedEvent], Awaitable[None]]] = []
        self.interaction_created: list[Callable[[BotInteractionEvent], Awaitable[None]]] = []
        self.unhandled_event: list[Callable[[UnknownGatewayEvent], Awaitable[None]]] = []
        self.connection_error: list[Callable[[BaseException], Awaitable[None]]] = []

        self._gateway.on_message(self._on_gateway_message)
        self._gateway.on_error(self._on_gateway_error)

    @classmethod
    def create(cls, options: BotClientOptions) -> BotClient:
        if not options.bot_token:
            raise ValueError("bot_token is required")
        return cls(
            GrpcBotsApiTransport(options),
            SignalRBotGatewayConnection(options),
            GrpcInteractionsAdminTransport(options),
        )

    async def start_gateway_async(self) -> None:
        await self._gateway.start_async()

    async def stop_gateway_async(self) -> None:
        await self._gateway.stop_async()

    async def close(self) -> None:
        await self.stop_gateway_async()
        self._transport.close()
        self._interactions_admin.close()

    async def run_async(self) -> None:
        await self.start_gateway_async()
        try:
            await asyncio.Event().wait()
        finally:
            await self.close()

    def _on_gateway_message(self, topic: str, raw: str) -> None:
        asyncio.get_event_loop().create_task(self._dispatch_gateway(topic, raw))

    def _on_gateway_error(self, error: BaseException) -> None:
        asyncio.get_event_loop().create_task(self._emit(self.connection_error, error))

    async def _dispatch_gateway(self, topic: str, raw: str) -> None:
        result = parse_gateway_event(topic, raw)
        kind = result.get("kind")
        if kind == "parse_error":
            await self._emit(self.connection_error, result["error"])
            return
        if kind == "message_created":
            await self._emit(self.message_created, result["message"])
        elif kind == "message_updated":
            await self._emit(self.message_updated, result["message"])
        elif kind == "message_deleted":
            await self._emit(self.message_deleted, result["message_id"], result["success"])
        elif kind == "reaction_added":
            await self._emit(self.reaction_added, result["reaction"])
        elif kind == "reaction_removed":
            await self._emit(self.reaction_removed, result["reaction"])
        elif kind == "user_typing":
            await self._emit(self.user_typing, result["event"])
        elif kind == "bot_typing":
            await self._emit(self.bot_typing, result["event"])
        elif kind == "user_connected":
            await self._emit(self.user_connected, result["event"])
        elif kind == "user_disconnected":
            await self._emit(self.user_disconnected, result["event"])
        elif kind == "user_joined_group":
            await self._emit(self.user_joined_group, result["event"])
        elif kind == "user_status_changed":
            await self._emit(self.user_status_changed, result["event"])
        elif kind == "interaction_created":
            await self._emit(self.interaction_created, result["event"])
        elif kind == "unknown":
            await self._emit(self.unhandled_event, result["event"])

    async def _emit(self, handlers: list, *args) -> None:
        for handler in list(handlers):
            await handler(*args)

    # --- Profile ---
    async def get_me_async(self) -> Bot:
        return await asyncio.to_thread(lambda: Bot.from_grpc(self._transport.get_me()))

    async def set_status_async(self, status: UserStatus, status_text: str | None = None) -> None:
        req = bots_pb2.SetStatusRequest(status=int(status))
        if status_text is not None:
            req.StatusText = status_text
        await asyncio.to_thread(self._transport.set_status, req)

    # --- Messages ---
    async def send_message_async(
        self,
        channel_id: str,
        content: str,
        *,
        reply_to: str | None = None,
        attachment_ids: Sequence[str] | None = None,
        components: ComponentBuilder | None = None,
    ) -> MessageInfo:
        req = bots_pb2.SendMessageRequest(channel_id=channel_id, content=content)
        if reply_to:
            req.reply_to = reply_to
        if attachment_ids:
            req.attachment_ids.extend(attachment_ids)
        if components is not None:
            req.components_json = components.build()
        return await asyncio.to_thread(lambda: MessageInfo.from_grpc(self._transport.send_message(req)))

    async def update_message_async(
        self, message_id: str, content: str, *, components: ComponentBuilder | None = None
    ) -> MessageInfo:
        req = bots_pb2.UpdateMessageRequest(message_id=message_id, content=content)
        if components is not None:
            req.components_json = components.build()
        return await asyncio.to_thread(lambda: MessageInfo.from_grpc(self._transport.update_message(req)))

    async def delete_message_async(self, message_id: str) -> DeleteMessageResult:
        req = bots_pb2.DeleteMessageRequest(message_id=message_id)
        return await asyncio.to_thread(lambda: DeleteMessageResult.from_grpc(self._transport.delete_message(req)))

    async def add_reaction_async(self, message_id: str, emoji: str) -> MessageInfo:
        req = bots_pb2.ReactionRequest(message_id=message_id, emoji=emoji)
        return await asyncio.to_thread(lambda: MessageInfo.from_grpc(self._transport.add_reaction(req)))

    async def remove_reaction_async(self, message_id: str, emoji: str) -> MessageInfo:
        req = bots_pb2.ReactionRequest(message_id=message_id, emoji=emoji)
        return await asyncio.to_thread(lambda: MessageInfo.from_grpc(self._transport.remove_reaction(req)))

    async def get_channel_messages_async(
        self, channel_id: str, *, limit: int = 50, before_id: str | None = None
    ) -> list[MessageInfo]:
        req = bots_pb2.GetChannelMessagesRequest(channel_id=channel_id, limit=limit)
        if before_id:
            req.before_id = before_id
        resp = await asyncio.to_thread(self._transport.get_channel_messages, req)
        return [MessageInfo.from_grpc(m) for m in resp.messages]

    async def get_message_async(self, message_id: str) -> MessageInfo:
        req = bots_pb2.GetMessageRequest(message_id=message_id)
        return await asyncio.to_thread(lambda: MessageInfo.from_grpc(self._transport.get_message(req)))

    async def typing_async(self, channel_id: str, is_typing: bool = True) -> None:
        await asyncio.to_thread(
            self._transport.typing, bots_pb2.TypingRequest(channel_id=channel_id, is_typing=is_typing)
        )

    async def set_typing_async(self, state: BotTypingState, channel_id: str) -> None:
        await asyncio.to_thread(
            self._transport.set_typing,
            bots_pb2.BotTypingRequest(channel_id=channel_id, state=int(state)),
        )

    # --- Groups ---
    async def get_my_groups_async(self) -> list[BotGroupInfo]:
        resp = await asyncio.to_thread(self._transport.get_my_groups)
        return [BotGroupInfo.from_grpc(g) for g in resp.groups]

    async def get_group_async(self, group_id: str) -> BotGroupDetails:
        req = bots_pb2.GetGroupRequest(group_id=group_id)
        return await asyncio.to_thread(lambda: BotGroupDetails.from_grpc(self._transport.get_group(req)))

    async def get_group_categories_async(self, group_id: str) -> list[BotCategoryInfo]:
        req = bots_pb2.GetGroupRequest(group_id=group_id)
        resp = await asyncio.to_thread(self._transport.get_group_categories, req)
        return [BotCategoryInfo.from_grpc(c) for c in resp.categories]

    async def get_group_channels_async(self, group_id: str) -> list[BotChannelInfo]:
        req = bots_pb2.GetGroupRequest(group_id=group_id)
        resp = await asyncio.to_thread(self._transport.get_group_channels, req)
        return [BotChannelInfo.from_grpc(c) for c in resp.channels]

    async def get_group_users_async(self, group_id: str) -> list[User]:
        req = bots_pb2.GetGroupUsersRequest(group_id=group_id)
        resp = await asyncio.to_thread(self._transport.get_group_users, req)
        return [User.from_grpc(u) for u in resp.users]

    async def get_user_async(self, user_id: str) -> User:
        req = bots_pb2.GetUserRequest(user_id=user_id)
        return await asyncio.to_thread(lambda: User.from_grpc(self._transport.get_user(req)))

    async def kick_user_async(self, group_id: str, user_id: str) -> KickUserResult:
        req = bots_pb2.KickUserRequest(group_id=group_id, user_id=user_id)
        return await asyncio.to_thread(lambda: KickUserResult.from_grpc(self._transport.kick_user(req)))

    async def get_channel_async(self, channel_id: str) -> BotChannelDetails:
        req = bots_pb2.GetChannelRequest(channel_id=channel_id)
        return await asyncio.to_thread(lambda: BotChannelDetails.from_grpc(self._transport.get_channel(req)))

    async def create_category_async(self, group_id: str, name: str) -> BotCategoryInfo:
        req = bots_pb2.CreateCategoryRequest(group_id=group_id, name=name)
        return await asyncio.to_thread(lambda: BotCategoryInfo.from_grpc(self._transport.create_category(req)))

    async def get_category_async(self, category_id: str) -> BotCategoryInfo:
        req = bots_pb2.GetCategoryRequest(category_id=category_id)
        return await asyncio.to_thread(lambda: BotCategoryInfo.from_grpc(self._transport.get_category(req)))

    async def create_channel_async(self, category_id: str, name: str, channel_type: ChannelType) -> BotChannelInfo:
        req = bots_pb2.CreateChannelRequest(category_id=category_id, name=name, type=int(channel_type))
        return await asyncio.to_thread(lambda: BotChannelInfo.from_grpc(self._transport.create_channel(req)))

    async def update_channel_async(self, channel_id: str, name: str) -> BotChannelInfo:
        req = bots_pb2.UpdateChannelRequest(channel_id=channel_id, name=name)
        return await asyncio.to_thread(lambda: BotChannelInfo.from_grpc(self._transport.update_channel(req)))

    async def update_category_async(self, category_id: str, name: str) -> BotCategoryInfo:
        req = bots_pb2.UpdateCategoryRequest(category_id=category_id, name=name)
        return await asyncio.to_thread(lambda: BotCategoryInfo.from_grpc(self._transport.update_category(req)))

    async def delete_channel_async(self, channel_id: str) -> DeleteChannelResult:
        req = bots_pb2.DeleteChannelRequest(channel_id=channel_id)
        return await asyncio.to_thread(lambda: DeleteChannelResult.from_grpc(self._transport.delete_channel(req)))

    async def delete_category_async(self, category_id: str) -> DeleteCategoryResult:
        req = bots_pb2.DeleteCategoryRequest(category_id=category_id)
        return await asyncio.to_thread(lambda: DeleteCategoryResult.from_grpc(self._transport.delete_category(req)))

    # --- Roles ---
    async def create_role_async(
        self, group_id: str, name: str, *, color: str | None = None, permissions: int = 0
    ) -> BotRole:
        req = bots_pb2.CreateRoleRequest(group_id=group_id, name=name, permissions=permissions)
        if color is not None:
            req.color = color
        return await asyncio.to_thread(lambda: BotRole.from_grpc(self._transport.create_role(req)))

    async def update_role_async(
        self, role_id: str, name: str, permissions: int, *, color: str | None = None
    ) -> BotRole:
        req = bots_pb2.UpdateRoleRequest(role_id=role_id, name=name, permissions=permissions)
        if color is not None:
            req.color = color
        return await asyncio.to_thread(lambda: BotRole.from_grpc(self._transport.update_role(req)))

    async def delete_role_async(self, role_id: str) -> None:
        await asyncio.to_thread(self._transport.delete_role, bots_pb2.DeleteRoleRequest(role_id=role_id))

    async def assign_role_async(self, group_id: str, target_user_id: str, role_id: str) -> None:
        await asyncio.to_thread(
            self._transport.assign_role,
            bots_pb2.RoleAssignmentRequest(group_id=group_id, target_user_id=target_user_id, role_id=role_id),
        )

    async def remove_role_async(self, group_id: str, target_user_id: str, role_id: str) -> None:
        await asyncio.to_thread(
            self._transport.remove_role,
            bots_pb2.RoleAssignmentRequest(group_id=group_id, target_user_id=target_user_id, role_id=role_id),
        )

    async def get_group_roles_async(self, group_id: str) -> list[BotRole]:
        req = bots_pb2.GetGroupRolesRequest(group_id=group_id)
        resp = await asyncio.to_thread(self._transport.get_group_roles, req)
        return [BotRole.from_grpc(r) for r in resp.roles]

    # --- Voice ---
    async def join_voice_channel_async(self, channel_id: str) -> JoinVoiceChannelResult:
        req = bots_pb2.JoinVoiceChannelRequest(channel_id=channel_id)
        return await asyncio.to_thread(
            lambda: JoinVoiceChannelResult.from_grpc(self._transport.join_voice_channel(req))
        )

    async def leave_voice_channel_async(self, channel_id: str) -> None:
        await asyncio.to_thread(
            self._transport.leave_voice_channel, bots_pb2.LeaveVoiceChannelRequest(channel_id=channel_id)
        )

    # --- Interactions ---
    async def respond_to_interaction_async(self, interaction_id: str, response: InteractionResponse) -> None:
        req = bots_pb2.RespondToInteractionRequest(
            interaction_id=interaction_id,
            kind=int(response.kind),
            content=response.content or "",
            components_json=response.components_json or "",
            modal_json=response.modal_json or "",
            ephemeral=response.ephemeral,
        )
        if response.autocomplete_choices:
            for choice in response.autocomplete_choices:
                if isinstance(choice, InteractionChoice):
                    req.autocomplete_choices.append(bots_pb2.InteractionChoice(name=choice.name, value=choice.value))
                else:
                    name, value = choice
                    req.autocomplete_choices.append(bots_pb2.InteractionChoice(name=name, value=value))
        await asyncio.to_thread(self._transport.respond_to_interaction, req)

    async def send_interaction_followup_async(
        self, interaction_id: str, content: str, *, components: ComponentBuilder | None = None
    ) -> MessageInfo:
        req = bots_pb2.SendInteractionFollowupRequest(interaction_id=interaction_id, content=content)
        if components is not None:
            req.components_json = components.build()
        return await asyncio.to_thread(
            lambda: MessageInfo.from_grpc(self._transport.send_interaction_followup(req))
        )

    # --- Slash command admin ---
    async def register_command_async(
        self,
        bot_id: str,
        name: str,
        description: str,
        *,
        options: Sequence[CommandOptionDefinition] | None = None,
        default_member_permissions: int = 0,
    ) -> BotCommandDefinition:
        req = interactions_pb2.RegisterCommandRequest(
            bot_id=bot_id,
            name=name,
            description=description,
            default_member_permissions=default_member_permissions,
        )
        if options:
            req.options.extend(o.to_wire() for o in options)
        return await asyncio.to_thread(
            lambda: BotCommandDefinition.from_grpc(self._interactions_admin.register_command(req))
        )

    async def update_command_async(
        self,
        bot_id: str,
        command_id: str,
        name: str,
        description: str,
        *,
        options: Sequence[CommandOptionDefinition] | None = None,
        default_member_permissions: int = 0,
    ) -> BotCommandDefinition:
        req = interactions_pb2.UpdateCommandRequest(
            bot_id=bot_id,
            command_id=command_id,
            name=name,
            description=description,
            default_member_permissions=default_member_permissions,
        )
        if options:
            req.options.extend(o.to_wire() for o in options)
        return await asyncio.to_thread(
            lambda: BotCommandDefinition.from_grpc(self._interactions_admin.update_command(req))
        )

    async def delete_command_async(self, bot_id: str, command_id: str) -> None:
        await asyncio.to_thread(
            self._interactions_admin.delete_command,
            interactions_pb2.DeleteCommandRequest(bot_id=bot_id, command_id=command_id),
        )

    async def get_bot_commands_async(self, bot_id: str) -> list[BotCommandDefinition]:
        req = interactions_pb2.GetBotCommandsRequest(bot_id=bot_id)
        resp = await asyncio.to_thread(self._interactions_admin.get_bot_commands, req)
        return [BotCommandDefinition.from_grpc(c) for c in resp.commands]
