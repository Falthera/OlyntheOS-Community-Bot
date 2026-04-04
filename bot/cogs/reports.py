from __future__ import annotations

import discord
from discord.ext import commands

from bot.views import ReportLauncherView
from bot.utils import make_embed


class ReportsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="bug", description="Submit a bug report")
    async def bug(self, context: commands.Context) -> None:
        embed = make_embed(
            title="Bug Report",
            description="Click Continue to open the structured bug report form.",
            color=self.bot.config.theme_color,
        )
        await context.reply(embed=embed, view=ReportLauncherView(self.bot, "bug", context.author.id), mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReportsCog(bot))
