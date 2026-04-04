from __future__ import annotations

from typing import Any

import discord
from discord.ext import commands

from bot.utils import make_embed


class StarboardCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.starboard_index: dict[int, int] = {}

    def _settings(self) -> dict[str, Any]:
        return self.bot.config.starboard

    def _emoji(self) -> str:
        return str(self._settings().get("emoji", "⭐"))

    def _threshold(self) -> int:
        return max(1, int(self._settings().get("threshold", 3)))

    def _channel_id(self) -> int:
        return int(self._settings().get("channel_id", 0))

    def _excluded_channel_ids(self) -> set[int]:
        excluded = self._settings().get("excluded_channel_ids", [])
        return {int(channel_id) for channel_id in excluded if str(channel_id).isdigit()}

    async def _get_starboard_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        channel_id = self._channel_id()
        if not channel_id:
            return None
        channel = guild.get_channel(channel_id)
        return channel if isinstance(channel, discord.TextChannel) else None

    async def _get_source_message(self, payload: discord.RawReactionActionEvent) -> discord.Message | None:
        channel = self.bot.get_channel(payload.channel_id)
        if not isinstance(channel, discord.TextChannel):
            return None
        try:
            return await channel.fetch_message(payload.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    def _matching_reaction_count(self, message: discord.Message) -> int:
        target_emoji = self._emoji()
        for reaction in message.reactions:
            if str(reaction.emoji) == target_emoji:
                return reaction.count
        return 0

    async def _find_existing_starboard_message(self, starboard_channel: discord.TextChannel, source_message: discord.Message) -> discord.Message | None:
        mapped_message_id = self.starboard_index.get(source_message.id)
        if mapped_message_id is not None:
            try:
                return await starboard_channel.fetch_message(mapped_message_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                self.starboard_index.pop(source_message.id, None)

        source_jump_url = source_message.jump_url
        async for candidate in starboard_channel.history(limit=200):
            if not candidate.embeds:
                continue
            embed = candidate.embeds[0]
            if not embed.fields:
                continue
            jump_field = next((field for field in embed.fields if field.name == "Source"), None)
            if jump_field is not None and jump_field.value == source_jump_url:
                self.starboard_index[source_message.id] = candidate.id
                return candidate
        return None

    def _build_embed(self, message: discord.Message, stars: int) -> discord.Embed:
        content = message.content or "*No text content.*"
        embed = make_embed(
            title=f"{self._emoji()} Starboard • {stars}",
            description=content[:4000],
            color=self.bot.config.theme_color,
        )
        embed.add_field(name="Author", value=f"{message.author.mention} ({message.author})", inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Source", value=f"[Go to message]({message.jump_url})", inline=True)
        if message.attachments:
            attachment = message.attachments[0]
            if attachment.content_type and attachment.content_type.startswith("image/"):
                embed.set_image(url=attachment.url)
            else:
                embed.add_field(name="Attachment", value=attachment.url, inline=False)
        if message.embeds:
            embed.add_field(name="Embeds", value=f"{len(message.embeds)} embed(s) attached", inline=True)
        embed.set_footer(text="LuminOS Starboard")
        return embed

    async def _upsert_starboard_entry(self, message: discord.Message, stars: int) -> None:
        starboard_channel = await self._get_starboard_channel(message.guild)
        if starboard_channel is None:
            return

        existing = await self._find_existing_starboard_message(starboard_channel, message)
        if stars < self._threshold():
            if existing is not None:
                await existing.delete()
            self.starboard_index.pop(message.id, None)
            return

        embed = self._build_embed(message, stars)
        if existing is None:
            starboard_message = await starboard_channel.send(embed=embed)
            self.starboard_index[message.id] = starboard_message.id
            return

        await existing.edit(embed=embed)
        self.starboard_index[message.id] = existing.id

    async def _handle_payload(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        if channel.id in self._excluded_channel_ids():
            return

        starboard_channel = await self._get_starboard_channel(channel.guild)
        if starboard_channel is not None and channel.id == starboard_channel.id:
            return

        if str(payload.emoji) != self._emoji():
            return

        message = await self._get_source_message(payload)
        if message is None or message.author.bot:
            return

        stars = self._matching_reaction_count(message)
        await self._upsert_starboard_entry(message, stars)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        await self._handle_payload(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        await self._handle_payload(payload)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StarboardCog(bot))