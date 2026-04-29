from __future__ import annotations

import logging
import re
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any

import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

from bot.config import BotConfig, ConfigError, load_config
from bot.logging_utils import configure_logging


class OlyntheOSBot(commands.Bot):
    def __init__(self, config: BotConfig, config_path: str = "config.json"):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True
        intents.reactions = True
        super().__init__(command_prefix=config.bot_prefix, intents=intents, help_command=None)
        self.config = config
        self.config_path = config_path
        self.logger = logging.getLogger("olyntheos.bot")
        self.command_history: dict[int, deque[datetime]] = defaultdict(deque)
        self.last_github_event_id: str | None = None

    def _is_direct_mention(self, message: discord.Message) -> bool:
        return self.user is not None and self.user in message.mentions

    def _is_greeting(self, message: discord.Message) -> bool:
        content = message.content.strip().lower()
        if not content:
            return False
        greeting_pattern = r"^(hi|hello|hey|yo|sup|hai|hii|good\s+morning|good\s+night|good\s+evening)(\s+.*)?$"
        if re.match(greeting_pattern, content):
            return True
        return bool(self.user and self.user.mentioned_in(message) and any(word in content for word in ("hi", "hello", "hey")))

    async def _reply_to_message(self, message: discord.Message) -> None:
        if self.user is None or message.author.bot:
            return

        if self._is_direct_mention(message):
            await message.reply(
                f"Hey {message.author.mention} — I’m here. Use `!ping` to check latency, or mention me with a question.",
                mention_author=False,
            )
            return

        if self._is_greeting(message):
            lower = message.content.strip().lower()
            if lower.startswith("good morning"):
                reply_text = f"Good morning, {message.author.mention} ☀️ Ready to build something cool today?"
            elif lower.startswith("good night"):
                reply_text = f"Good night, {message.author.mention} 🌙 Rest well — I’ll be here when you’re back."
            elif lower.startswith("good evening"):
                reply_text = f"Good evening, {message.author.mention} ✨ Hope the build queue is behaving tonight."
            else:
                reply_text = f"Hi {message.author.mention} 👋 Use `!ping` if you want to check my response time."
            await message.reply(
                reply_text,
                mention_author=False,
            )

    async def setup_hook(self) -> None:
        await self.load_extension("bot.cogs.info")
        await self.load_extension("bot.cogs.reports")
        await self.load_extension("bot.cogs.onboarding")
        await self.load_extension("bot.cogs.roles")
        await self.load_extension("bot.cogs.moderation")
        await self.load_extension("bot.cogs.github")
        await self.load_extension("bot.cogs.starboard")
        await self.load_extension("bot.cogs.tickets")
        await self.load_extension("bot.cogs.fun")
        await self.load_extension("bot.cogs.admin")
        if self.config.guild_id:
            guild = discord.Object(id=self.config.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self) -> None:
        self.logger.info("Logged in as %s", self.user)
        activity = discord.Activity(type=discord.ActivityType.watching, name=f"{self.config.project_name} development")
        await self.change_presence(activity=activity)

    async def on_command_completion(self, context: commands.Context[Any]) -> None:
        channel_id = self.config.channels.get("command_log")
        if channel_id and context.guild:
            channel = context.guild.get_channel(channel_id)
            if isinstance(channel, discord.TextChannel):
                embed = discord.Embed(
                    title="Command Used",
                    description=f"{context.author.mention} used `{context.command}`",
                    color=self.config.theme_color,
                    timestamp=datetime.now(timezone.utc),
                )
                embed.add_field(name="Channel", value=context.channel.mention, inline=True)
                embed.add_field(name="Location", value=f"{context.guild.name}", inline=True)
                await channel.send(embed=embed)

    async def on_command_error(self, context: commands.Context[Any], error: Exception) -> None:
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingPermissions):
            await context.reply("You do not have permission to use that command.", mention_author=False)
            return
        if isinstance(error, commands.CommandOnCooldown):
            await context.reply(f"Please wait {error.retry_after:.1f}s before using that again.", mention_author=False)
            return

        self.logger.error("Command error in %s", context.command, exc_info=(type(error), error, error.__traceback__))
        channel_id = self.config.channels.get("command_log")
        if channel_id and context.guild:
            channel = context.guild.get_channel(channel_id)
            if isinstance(channel, discord.TextChannel):
                await channel.send(f"Error in `{context.command}`: `{type(error).__name__}`")
        await context.reply("An unexpected error occurred while processing the command.", mention_author=False)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        await self._reply_to_message(message)
        await self._anti_spam_check(message)
        await self.process_commands(message)

    async def _anti_spam_check(self, message: discord.Message) -> None:
        spam_cfg = self.config.anti_spam
        message_limit = int(spam_cfg.get("message_limit", 5))
        window_seconds = int(spam_cfg.get("window_seconds", 8))
        timeout_seconds = int(spam_cfg.get("timeout_seconds", 30))
        timestamps = self.command_history[message.author.id]
        now = datetime.now(timezone.utc)
        timestamps.append(now)
        while timestamps and (now - timestamps[0]).total_seconds() > window_seconds:
            timestamps.popleft()
        if len(timestamps) < message_limit:
            return

        member = message.author if isinstance(message.author, discord.Member) else None
        if member is None:
            return

        try:
            timeout_until = datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds)
            await member.timeout(timeout_until, reason="Anti-spam trigger")
        except Exception:
            self.logger.exception("Failed to apply anti-spam timeout for %s", member)
        channel_id = self.config.channels.get("moderation_log")
        if channel_id:
            channel = message.guild.get_channel(channel_id)
            if isinstance(channel, discord.TextChannel):
                await channel.send(f"Anti-spam timeout applied to {member.mention} for rapid messaging.")
        timestamps.clear()


def run_bot() -> None:
    load_dotenv()
    token = os.getenv("TOKEN")
    if not token:
        raise ConfigError("Missing TOKEN environment variable.")

    config = load_config()
    configure_logging(bool(config.logging.get("local_file", True)), config.logging.get("file_path", "logs/bot.log"))
    bot = OlyntheOSBot(config)
    bot.run(token)
