from __future__ import annotations

import discord
from discord.ext import commands

from bot.utils import make_embed


class OnboardingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        config = self.bot.config
        if config.welcome.get("assign_default_role", True):
            role_id = config.roles.get("default")
            if role_id:
                role = member.guild.get_role(role_id)
                if role is not None:
                    try:
                        await member.add_roles(role, reason="Default onboarding role")
                    except discord.Forbidden:
                        self.bot.logger.warning("Missing permission to assign default role to %s", member)

        welcome_channel_id = config.channels.get("welcome")
        welcome_channel = member.guild.get_channel(welcome_channel_id) if welcome_channel_id else None
        if isinstance(welcome_channel, discord.TextChannel):
            public_message = config.welcome.get(
                "public_message",
                f"Welcome {member.mention}!\n\nPlease start in #start-here, review #rules, and introduce yourself to the community.",
            )
            embed = make_embed(
                title=f"Welcome to {config.project_name}",
                description=public_message,
                color=config.theme_color,
            )
            await welcome_channel.send(content=member.mention, embed=embed)

        dm_message = config.welcome.get("dm_message")
        if dm_message:
            try:
                await member.send(dm_message)
            except discord.Forbidden:
                pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OnboardingCog(bot))
