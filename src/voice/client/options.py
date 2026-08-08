"""Configuration for BotClient.create."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class BotClientOptions:
    """Mutable options matching .NET BotClientOptions."""

    bot_token: str
    bots_api_endpoint: str = "https://api.iopta.org"
    allow_untrusted_certificates: bool = False
    text_command_prefix: str = "!"
    configure_channel_options: Optional[Callable[[list[tuple[str, Any]]], None]] = field(default=None, repr=False)
