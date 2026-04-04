from __future__ import annotations

import discord
from discord.ext import commands

from bot.utils import make_embed, chunk_lines


class InfoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="about", description="Show information about the project")
    async def about(self, context: commands.Context) -> None:
        config = self.bot.config
        features = "\n".join(f"• {item}" for item in config.features)
        description = config.tagline or config.vision or "Developer-focused Linux distribution"
        embed = make_embed(
            title=f"About {config.project_name}",
            description=description,
            color=config.theme_color,
        )
        if config.vision and config.vision != description:
            embed.add_field(name="Vision", value=config.vision, inline=False)
        embed.add_field(name="Highlights", value=features or "• Feature details coming soon", inline=False)
        embed.add_field(name="Website", value=config.links.get("website", "Not configured"), inline=False)
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="roadmap", description="Show the project roadmap")
    async def roadmap(self, context: commands.Context) -> None:
        config = self.bot.config
        embed = make_embed(
            title=f"{config.project_name} Roadmap",
            description="A high-level view of the project phases.",
            color=config.theme_color,
        )
        for index, phase in enumerate(config.roadmap, start=1):
            embed.add_field(name=f"{index}. {phase.phase}", value=phase.description, inline=False)
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="github", description="Show the GitHub repository")
    async def github(self, context: commands.Context) -> None:
        config = self.bot.config
        embed = make_embed(
            title="GitHub Repository",
            description=f"Source code and development activity for {config.project_name}.",
            color=config.theme_color,
        )
        embed.add_field(name="Repository", value=config.links.get("github", "Not configured"), inline=False)
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="website", description="Show the project website")
    async def website(self, context: commands.Context) -> None:
        config = self.bot.config
        embed = make_embed(
            title="Project Website",
            description="Official project information and community resources.",
            color=config.theme_color,
        )
        embed.add_field(name="Website", value=config.links.get("website", "Not configured"), inline=False)
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="status", description="Show the current build status")
    async def status(self, context: commands.Context) -> None:
        config = self.bot.config
        embed = make_embed(title=f"{config.project_name} Status", description=config.current_build_status, color=config.theme_color)
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="version", description="Show the latest OS version")
    async def version(self, context: commands.Context) -> None:
        config = self.bot.config
        embed = make_embed(title=f"{config.project_name} Version", description=f"Latest version: {config.latest_version}", color=config.theme_color)
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="build", description="Show the latest build notes")
    async def build(self, context: commands.Context) -> None:
        config = self.bot.config
        embed = make_embed(title=f"{config.project_name} Build Notes", description=config.build_notes, color=config.theme_color)
        await context.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(InfoCog(bot))
