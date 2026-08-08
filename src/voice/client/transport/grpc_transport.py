"""gRPC wrappers over generated stubs."""

from __future__ import annotations

from typing import Any, Callable, TypeVar
from urllib.parse import urlparse

import grpc
from google.protobuf import empty_pb2

from voice.client._generated import bots_pb2, bots_pb2_grpc, interactions_pb2, interactions_pb2_grpc
from voice.client.exceptions import BotApiException
from voice.client.options import BotClientOptions

T = TypeVar("T")


def _channel_target(endpoint: str) -> str:
    parsed = urlparse(endpoint if "://" in endpoint else f"https://{endpoint}")
    host = parsed.hostname or endpoint
    port = parsed.port
    if port is None:
        port = 443 if (parsed.scheme or "https") == "https" else 80
    return f"{host}:{port}"


def _secure(endpoint: str) -> bool:
    parsed = urlparse(endpoint if "://" in endpoint else f"https://{endpoint}")
    return (parsed.scheme or "https") == "https"


class _AuthInterceptor(grpc.UnaryUnaryClientInterceptor):
    def __init__(self, token: str) -> None:
        self._token = token

    def intercept_unary_unary(self, continuation, client_call_details, request):
        metadata = []
        if client_call_details.metadata:
            metadata.extend(client_call_details.metadata)
        metadata.append(("authorization", f"Bearer {self._token}"))
        new_details = client_call_details._replace(metadata=metadata)
        return continuation(new_details, request)


def _call(fn: Callable[[], T]) -> T:
    try:
        return fn()
    except grpc.RpcError as ex:
        raise BotApiException.from_rpc_error(ex) from ex


class GrpcBotsApiTransport:
    def __init__(self, options: BotClientOptions) -> None:
        target = _channel_target(options.bots_api_endpoint)
        if _secure(options.bots_api_endpoint):
            if options.allow_untrusted_certificates:
                creds = grpc.ssl_channel_credentials()
                channel = grpc.secure_channel(
                    target,
                    creds,
                    options=(("grpc.ssl_target_name_override", target.split(":")[0]),),
                )
                # Disable verification via channel args is limited; use composite for local dev
                channel = grpc.secure_channel(
                    target,
                    grpc.ssl_channel_credentials(),
                    options=(
                        ("grpc.ssl_target_name_override", target.split(":")[0]),
                    ),
                )
            else:
                channel = grpc.secure_channel(target, grpc.ssl_channel_credentials())
        else:
            channel = grpc.insecure_channel(target)

        intercepted = grpc.intercept_channel(channel, _AuthInterceptor(options.bot_token))
        self._channel = intercepted
        self._client = bots_pb2_grpc.BotsApiStub(intercepted)

    def close(self) -> None:
        self._channel.close()

    def get_me(self) -> Any:
        return _call(lambda: self._client.GetMe(empty_pb2.Empty()))

    def set_status(self, request: bots_pb2.SetStatusRequest) -> None:
        _call(lambda: self._client.SetStatus(request))

    def join_voice_channel(self, request: bots_pb2.JoinVoiceChannelRequest) -> Any:
        return _call(lambda: self._client.JoinVoiceChannel(request))

    def leave_voice_channel(self, request: bots_pb2.LeaveVoiceChannelRequest) -> None:
        _call(lambda: self._client.LeaveVoiceChannel(request))

    def send_message(self, request: bots_pb2.SendMessageRequest) -> Any:
        return _call(lambda: self._client.SendMessage(request))

    def update_message(self, request: bots_pb2.UpdateMessageRequest) -> Any:
        return _call(lambda: self._client.UpdateMessage(request))

    def delete_message(self, request: bots_pb2.DeleteMessageRequest) -> Any:
        return _call(lambda: self._client.DeleteMessage(request))

    def add_reaction(self, request: bots_pb2.ReactionRequest) -> Any:
        return _call(lambda: self._client.AddReaction(request))

    def remove_reaction(self, request: bots_pb2.ReactionRequest) -> Any:
        return _call(lambda: self._client.RemoveReaction(request))

    def get_channel_messages(self, request: bots_pb2.GetChannelMessagesRequest) -> Any:
        return _call(lambda: self._client.GetChannelMessages(request))

    def get_message(self, request: bots_pb2.GetMessageRequest) -> Any:
        return _call(lambda: self._client.GetMessage(request))

    def typing(self, request: bots_pb2.TypingRequest) -> None:
        _call(lambda: self._client.Typing(request))

    def set_typing(self, request: bots_pb2.BotTypingRequest) -> None:
        _call(lambda: self._client.SetTyping(request))

    def get_my_groups(self) -> Any:
        return _call(lambda: self._client.GetMyGroups(empty_pb2.Empty()))

    def get_group(self, request: bots_pb2.GetGroupRequest) -> Any:
        return _call(lambda: self._client.GetGroup(request))

    def get_group_categories(self, request: bots_pb2.GetGroupRequest) -> Any:
        return _call(lambda: self._client.GetGroupCategories(request))

    def get_group_channels(self, request: bots_pb2.GetGroupRequest) -> Any:
        return _call(lambda: self._client.GetGroupChannels(request))

    def get_group_users(self, request: bots_pb2.GetGroupUsersRequest) -> Any:
        return _call(lambda: self._client.GetGroupUsers(request))

    def get_user(self, request: bots_pb2.GetUserRequest) -> Any:
        return _call(lambda: self._client.GetUser(request))

    def kick_user(self, request: bots_pb2.KickUserRequest) -> Any:
        return _call(lambda: self._client.KickUser(request))

    def get_channel(self, request: bots_pb2.GetChannelRequest) -> Any:
        return _call(lambda: self._client.GetChannel(request))

    def respond_to_interaction(self, request: bots_pb2.RespondToInteractionRequest) -> None:
        _call(lambda: self._client.RespondToInteraction(request))

    def send_interaction_followup(self, request: bots_pb2.SendInteractionFollowupRequest) -> Any:
        return _call(lambda: self._client.SendInteractionFollowup(request))

    def create_category(self, request: bots_pb2.CreateCategoryRequest) -> Any:
        return _call(lambda: self._client.CreateCategory(request))

    def get_category(self, request: bots_pb2.GetCategoryRequest) -> Any:
        return _call(lambda: self._client.GetCategory(request))

    def create_channel(self, request: bots_pb2.CreateChannelRequest) -> Any:
        return _call(lambda: self._client.CreateChannel(request))

    def update_channel(self, request: bots_pb2.UpdateChannelRequest) -> Any:
        return _call(lambda: self._client.UpdateChannel(request))

    def update_category(self, request: bots_pb2.UpdateCategoryRequest) -> Any:
        return _call(lambda: self._client.UpdateCategory(request))

    def delete_channel(self, request: bots_pb2.DeleteChannelRequest) -> Any:
        return _call(lambda: self._client.DeleteChannel(request))

    def delete_category(self, request: bots_pb2.DeleteCategoryRequest) -> Any:
        return _call(lambda: self._client.DeleteCategory(request))

    def create_role(self, request: bots_pb2.CreateRoleRequest) -> Any:
        return _call(lambda: self._client.CreateRole(request))

    def update_role(self, request: bots_pb2.UpdateRoleRequest) -> Any:
        return _call(lambda: self._client.UpdateRole(request))

    def delete_role(self, request: bots_pb2.DeleteRoleRequest) -> None:
        _call(lambda: self._client.DeleteRole(request))

    def assign_role(self, request: bots_pb2.RoleAssignmentRequest) -> None:
        _call(lambda: self._client.AssignRole(request))

    def remove_role(self, request: bots_pb2.RoleAssignmentRequest) -> None:
        _call(lambda: self._client.RemoveRole(request))

    def get_group_roles(self, request: bots_pb2.GetGroupRolesRequest) -> Any:
        return _call(lambda: self._client.GetGroupRoles(request))


class GrpcInteractionsAdminTransport:
    def __init__(self, options: BotClientOptions) -> None:
        target = _channel_target(options.bots_api_endpoint)
        if _secure(options.bots_api_endpoint):
            channel = grpc.secure_channel(target, grpc.ssl_channel_credentials())
        else:
            channel = grpc.insecure_channel(target)
        intercepted = grpc.intercept_channel(channel, _AuthInterceptor(options.bot_token))
        self._channel = intercepted
        self._client = interactions_pb2_grpc.InteractionsApiStub(intercepted)

    def close(self) -> None:
        self._channel.close()

    def register_command(self, request: interactions_pb2.RegisterCommandRequest) -> Any:
        return _call(lambda: self._client.RegisterCommand(request))

    def update_command(self, request: interactions_pb2.UpdateCommandRequest) -> Any:
        return _call(lambda: self._client.UpdateCommand(request))

    def delete_command(self, request: interactions_pb2.DeleteCommandRequest) -> None:
        _call(lambda: self._client.DeleteCommand(request))

    def get_bot_commands(self, request: interactions_pb2.GetBotCommandsRequest) -> Any:
        return _call(lambda: self._client.GetBotCommands(request))
