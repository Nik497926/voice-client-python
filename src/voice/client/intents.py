"""Gateway / RPC intent flags (mirror of .NET BotIntents)."""

from __future__ import annotations

from enum import IntFlag


class BotIntents(IntFlag):
    NONE = 0
    GUILDS = 1 << 0
    GUILD_MESSAGES = 1 << 1
    GUILD_VOICE_STATES = 1 << 2
    APPLICATION_COMMANDS = 1 << 3

    def has(self, required: BotIntents) -> bool:
        return (self & required) == required
