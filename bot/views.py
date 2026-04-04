from __future__ import annotations

import discord


def _truncate(value: str, limit: int = 1024) -> str:
    return value if len(value) <= limit else value[: limit - 3] + "..."


class BugReportModal(discord.ui.Modal, title="LuminOS Bug Report"):
    def __init__(self, bot: discord.Client):
        super().__init__(timeout=300)
        self.bot = bot
        self.os_version = discord.ui.TextInput(label="OS version", placeholder="e.g. 0.1.0-alpha", max_length=120)
        self.description = discord.ui.TextInput(label="Issue description", style=discord.TextStyle.paragraph, max_length=1000)
        self.steps = discord.ui.TextInput(label="Steps to reproduce", style=discord.TextStyle.paragraph, max_length=1000)
        self.logs = discord.ui.TextInput(label="Optional logs", style=discord.TextStyle.paragraph, required=False, max_length=1000)
        self.add_item(self.os_version)
        self.add_item(self.description)
        self.add_item(self.steps)
        self.add_item(self.logs)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        from bot.utils import make_embed

        config = self.bot.config
        channel_id = config.channels.get("bug_reports")
        channel = interaction.guild.get_channel(channel_id) if interaction.guild and channel_id else None
        if channel is None:
            await interaction.response.send_message("Bug reports channel is not configured.", ephemeral=True)
            return

        embed = make_embed(
            title="New Bug Report",
            description="A new bug report has been submitted by a community member.",
            color=config.theme_color,
        )
        embed.add_field(name="Reporter", value=_truncate(f"{interaction.user.mention} ({interaction.user})"), inline=False)
        embed.add_field(name="OS Version", value=_truncate(str(self.os_version.value), 256), inline=True)
        embed.add_field(name="Description", value=_truncate(str(self.description.value)), inline=False)
        embed.add_field(name="Steps to Reproduce", value=_truncate(str(self.steps.value)), inline=False)
        embed.add_field(name="Logs", value=_truncate(str(self.logs.value or "No logs provided.")), inline=False)

        mention_id = config.roles.get("moderator_mention")
        mention_text = f"<@&{mention_id}>" if mention_id else ""
        await channel.send(content=mention_text, embed=embed)
        await interaction.response.send_message("Your bug report has been submitted. Thank you.", ephemeral=True)


class FeatureRequestModal(discord.ui.Modal, title="LuminOS Feature Request"):
    def __init__(self, bot: discord.Client):
        super().__init__(timeout=300)
        self.bot = bot
        self.feature = discord.ui.TextInput(label="Feature suggestion", style=discord.TextStyle.paragraph, max_length=1500)
        self.add_item(self.feature)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        from bot.utils import make_embed

        config = self.bot.config
        channel_id = config.channels.get("feature_requests")
        channel = interaction.guild.get_channel(channel_id) if interaction.guild and channel_id else None
        if channel is None:
            await interaction.response.send_message("Feature requests channel is not configured.", ephemeral=True)
            return

        embed = make_embed(
            title="New Feature Request",
            description=_truncate(str(self.feature.value), 3500),
            color=config.theme_color,
        )
        embed.add_field(name="Requested by", value=_truncate(f"{interaction.user.mention} ({interaction.user})"), inline=False)
        message = await channel.send(embed=embed)
        try:
            await message.add_reaction("👍")
            await message.add_reaction("👎")
        except discord.Forbidden:
            pass
        await interaction.response.send_message("Your feature request has been posted. Thank you.", ephemeral=True)


class ReportLauncherView(discord.ui.View):
    def __init__(self, bot: discord.Client, report_type: str, requester_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.report_type = report_type
        self.requester_id = requester_id

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.primary)
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message("Only the command user can continue this flow.", ephemeral=True)
            return
        if self.report_type == "bug":
            await interaction.response.send_modal(BugReportModal(self.bot))
        else:
            await interaction.response.send_modal(FeatureRequestModal(self.bot))
