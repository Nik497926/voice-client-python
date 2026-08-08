"""Voice bot client SDK.

Install::

    pip install git+https://github.com/Nik497926/voice-client-python.git

Quick start::

    from voice.client import BotClient, BotClientOptions

    client = BotClient.create(BotClientOptions(bot_token="ibot_..."))
"""

from voice.client.client import BotClient
from voice.client.commands import (
    CommandContext,
    CommandService,
    ModuleBase,
    alias,
    command,
    tokenize,
)
from voice.client.components import (
    ActionRowBuilder,
    ButtonBuilder,
    ButtonStyle,
    CheckboxBuilder,
    ComboBoxBuilder,
    ComponentBuilder,
    ModalBuilder,
    SelectMenuBuilder,
    TextInputBuilder,
    TextInputStyle,
)
from voice.client.exceptions import BotApiException
from voice.client.intents import BotIntents
from voice.client.interactions import (
    InteractionContext,
    InteractionModuleBase,
    InteractionService,
    autocomplete_handler,
    component_interaction,
    modal_interaction,
    slash_command,
    slash_command_option,
)
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
    CommandOptionType,
    DeleteCategoryResult,
    DeleteChannelResult,
    DeleteMessageResult,
    InteractionChoice,
    InteractionResponse,
    InteractionResponseKind,
    InteractionType,
    JoinVoiceChannelResult,
    KickUserResult,
    MessageInfo,
    User,
    UserStatus,
)
from voice.client.options import BotClientOptions

__all__ = [
    "ActionRowBuilder",
    "Bot",
    "BotApiException",
    "BotCategoryInfo",
    "BotChannelDetails",
    "BotChannelInfo",
    "BotClient",
    "BotClientOptions",
    "BotCommandDefinition",
    "BotGroupDetails",
    "BotGroupInfo",
    "BotIntents",
    "BotRole",
    "BotTypingState",
    "ButtonBuilder",
    "ButtonStyle",
    "ChannelType",
    "CheckboxBuilder",
    "ComboBoxBuilder",
    "CommandContext",
    "CommandOptionDefinition",
    "CommandOptionType",
    "CommandService",
    "ComponentBuilder",
    "DeleteCategoryResult",
    "DeleteChannelResult",
    "DeleteMessageResult",
    "InteractionChoice",
    "InteractionContext",
    "InteractionModuleBase",
    "InteractionResponse",
    "InteractionResponseKind",
    "InteractionService",
    "InteractionType",
    "JoinVoiceChannelResult",
    "KickUserResult",
    "MessageInfo",
    "ModalBuilder",
    "ModuleBase",
    "SelectMenuBuilder",
    "TextInputBuilder",
    "TextInputStyle",
    "User",
    "UserStatus",
    "alias",
    "autocomplete_handler",
    "command",
    "component_interaction",
    "modal_interaction",
    "slash_command",
    "slash_command_option",
    "tokenize",
]

__version__ = "0.1.0"
