from __future__ import annotations

import discord
from discord.ext import commands

from bot.config import load_config, save_config
from bot.utils import make_embed


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _int_list(text: str) -> list[int]:
    values: list[int] = []
    for item in _lines(text):
        try:
            values.append(int(item))
        except ValueError:
            continue
    return values


def _mapping(text: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for item in _lines(text):
        if "=" not in item:
            continue
        key, raw_value = item.split("=", 1)
        try:
            values[key.strip()] = int(raw_value.strip())
        except ValueError:
            continue
    return values


def _bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _theme_color(value: str) -> int:
    cleaned = value.strip().lower().replace("#", "")
    if cleaned.startswith("0x"):
        cleaned = cleaned[2:]
    return int(cleaned, 16)


def _can_access_admin_panel(bot: commands.Bot, guild: discord.Guild | None, member: discord.Member) -> bool:
    config = bot.config
    permissions = member.guild_permissions
    moderator_role_id = int(config.roles.get("moderator_mention", 0))
    has_moderator_role = bool(moderator_role_id and any(role.id == moderator_role_id for role in member.roles))
    return bool(
        member.id in config.owner_ids
        or (guild and member.id == guild.owner_id)
        or permissions.administrator
        or permissions.manage_guild
        or has_moderator_role
    )


class ProjectModal(discord.ui.Modal, title="Edit Project Details"):
    project_name = discord.ui.TextInput(label="Project name", max_length=100)
    tagline = discord.ui.TextInput(label="Tagline", max_length=180, required=False)
    vision = discord.ui.TextInput(label="Vision", style=discord.TextStyle.paragraph, max_length=1000, required=False)

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        config = self.bot.config
        config.project["name"] = str(self.project_name.value).strip()
        config.project["tagline"] = str(self.tagline.value).strip()
        config.project["vision"] = str(self.vision.value).strip()
        save_config(config, self.bot.config_path)
        await interaction.response.send_message("Project details updated and saved.", ephemeral=True)


class StatusModal(discord.ui.Modal, title="Edit Status"):
    current_build_status = discord.ui.TextInput(label="Current build status", style=discord.TextStyle.paragraph, max_length=500)
    latest_version = discord.ui.TextInput(label="Latest version", max_length=100)
    build_notes = discord.ui.TextInput(label="Build notes", style=discord.TextStyle.paragraph, max_length=1500, required=False)

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        config = self.bot.config
        config.status["current_build_status"] = str(self.current_build_status.value).strip()
        config.status["latest_version"] = str(self.latest_version.value).strip()
        config.status["build_notes"] = str(self.build_notes.value).strip()
        save_config(config, self.bot.config_path)
        await interaction.response.send_message("Status values updated and saved.", ephemeral=True)


class LinksModal(discord.ui.Modal, title="Edit Links"):
    github = discord.ui.TextInput(label="GitHub URL", max_length=200)
    website = discord.ui.TextInput(label="Website URL", max_length=200)

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        config = self.bot.config
        config.links["github"] = str(self.github.value).strip()
        config.links["website"] = str(self.website.value).strip()
        save_config(config, self.bot.config_path)
        await interaction.response.send_message("Links updated and saved.", ephemeral=True)


class IDsModal(discord.ui.Modal, title="Edit IDs"):
    channels = discord.ui.TextInput(
        label="Channel IDs (key=value per line)",
        style=discord.TextStyle.paragraph,
        placeholder="welcome=123\nbug_reports=456\nfeature_requests=789",
        max_length=1500,
        required=False,
    )
    roles = discord.ui.TextInput(
        label="Role IDs (key=value per line)",
        style=discord.TextStyle.paragraph,
        placeholder="default=123\ntester=456\ndeveloper=789",
        max_length=1500,
        required=False,
    )
    owners = discord.ui.TextInput(
        label="Owner IDs (one per line)",
        style=discord.TextStyle.paragraph,
        placeholder="123456789012345678",
        max_length=1500,
        required=False,
    )

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        config = self.bot.config
        config.channels.update(_mapping(str(self.channels.value)))
        config.roles.update(_mapping(str(self.roles.value)))
        config.owner_ids = _int_list(str(self.owners.value))
        save_config(config, self.bot.config_path)
        await interaction.response.send_message("IDs updated and saved.", ephemeral=True)


class AppearanceModal(discord.ui.Modal, title="Edit Prefix and Theme"):
    prefix = discord.ui.TextInput(label="Bot prefix", max_length=8)
    theme_color = discord.ui.TextInput(label="Theme color (hex like 00C2FF)", max_length=12)

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        config = self.bot.config
        config.bot_prefix = str(self.prefix.value).strip() or config.bot_prefix
        config.theme_color = _theme_color(str(self.theme_color.value))
        save_config(config, self.bot.config_path)
        await interaction.response.send_message("Prefix and theme color updated and saved.", ephemeral=True)


class WelcomeModal(discord.ui.Modal, title="Edit Welcome Settings"):
    dm_message = discord.ui.TextInput(label="Welcome DM message", style=discord.TextStyle.paragraph, max_length=1500, required=False)
    public_message = discord.ui.TextInput(label="Public welcome message", style=discord.TextStyle.paragraph, max_length=1500, required=False)
    default_role = discord.ui.TextInput(label="Assign default role? (yes/no)", max_length=8)

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        config = self.bot.config
        config.welcome["dm_message"] = str(self.dm_message.value).strip()
        config.welcome["public_message"] = str(self.public_message.value).strip()
        config.welcome["assign_default_role"] = _bool(str(self.default_role.value))
        save_config(config, self.bot.config_path)
        await interaction.response.send_message("Welcome settings updated and saved.", ephemeral=True)


class AntiSpamModal(discord.ui.Modal, title="Edit Anti-Spam Settings"):
    message_limit = discord.ui.TextInput(label="Message limit", max_length=4)
    window_seconds = discord.ui.TextInput(label="Window seconds", max_length=4)
    timeout_seconds = discord.ui.TextInput(label="Timeout seconds", max_length=4)

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        config = self.bot.config
        config.anti_spam["message_limit"] = int(self.message_limit.value)
        config.anti_spam["window_seconds"] = int(self.window_seconds.value)
        config.anti_spam["timeout_seconds"] = int(self.timeout_seconds.value)
        save_config(config, self.bot.config_path)
        await interaction.response.send_message("Anti-spam settings updated and saved.", ephemeral=True)


class GitHubModal(discord.ui.Modal, title="Edit GitHub Settings"):
    repo_owner = discord.ui.TextInput(label="Repo owner", max_length=100)
    repo_name = discord.ui.TextInput(label="Repo name", max_length=100)
    poll_interval_minutes = discord.ui.TextInput(label="Poll interval (minutes)", max_length=4)

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        config = self.bot.config
        config.github["repo_owner"] = str(self.repo_owner.value).strip()
        config.github["repo_name"] = str(self.repo_name.value).strip()
        config.github["poll_interval_minutes"] = int(self.poll_interval_minutes.value)
        save_config(config, self.bot.config_path)
        await interaction.response.send_message("GitHub settings updated and saved.", ephemeral=True)


class LoggingModal(discord.ui.Modal, title="Edit Logging Settings"):
    local_file = discord.ui.TextInput(label="Save local log file? (yes/no)", max_length=8)
    file_path = discord.ui.TextInput(label="Log file path", max_length=200)

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        config = self.bot.config
        config.logging["local_file"] = _bool(str(self.local_file.value))
        config.logging["file_path"] = str(self.file_path.value).strip()
        save_config(config, self.bot.config_path)
        await interaction.response.send_message("Logging settings updated and saved.", ephemeral=True)


class StarboardModal(discord.ui.Modal, title="Edit Starboard Settings"):
    channel_id = discord.ui.TextInput(label="Starboard channel ID", max_length=20)
    emoji = discord.ui.TextInput(label="Starboard emoji", max_length=50)
    threshold = discord.ui.TextInput(label="Reaction threshold", max_length=4)
    excluded_channel_ids = discord.ui.TextInput(
        label="Excluded channel IDs (one per line)",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=False,
    )

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        config = self.bot.config
        excluded_ids = _int_list(str(self.excluded_channel_ids.value))
        config.starboard["channel_id"] = int(self.channel_id.value)
        config.starboard["emoji"] = str(self.emoji.value).strip() or "⭐"
        config.starboard["threshold"] = int(self.threshold.value)
        config.starboard["excluded_channel_ids"] = excluded_ids
        save_config(config, self.bot.config_path)
        await interaction.response.send_message("Starboard settings updated and saved.", ephemeral=True)


class TicketsModal(discord.ui.Modal, title="Edit Ticket Settings"):
    category_id = discord.ui.TextInput(label="Tickets category ID", max_length=20)
    log_channel_id = discord.ui.TextInput(label="Ticket log channel ID", max_length=20, required=False)
    support_role_id = discord.ui.TextInput(label="Support role ID", max_length=20, required=False)
    ticket_channel_prefix = discord.ui.TextInput(label="Ticket channel prefix", max_length=32)
    max_open_tickets = discord.ui.TextInput(label="Max open tickets per user", max_length=4)

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        config = self.bot.config
        config.tickets["category_id"] = int(self.category_id.value)
        config.tickets["log_channel_id"] = int(self.log_channel_id.value) if str(self.log_channel_id.value).strip() else 0
        config.tickets["support_role_id"] = int(self.support_role_id.value) if str(self.support_role_id.value).strip() else 0
        config.tickets["ticket_channel_prefix"] = str(self.ticket_channel_prefix.value).strip() or "ticket"
        config.tickets["max_open_tickets"] = max(1, int(self.max_open_tickets.value))
        config.tickets.setdefault("ping_support_role", True)
        save_config(config, self.bot.config_path)
        await interaction.response.send_message("Ticket settings updated and saved. Ping behavior was left unchanged.", ephemeral=True)


class PurgeModal(discord.ui.Modal, title="Purge Messages"):
    amount = discord.ui.TextInput(label="Messages to delete", max_length=4)

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This action only works in a text channel.", ephemeral=True)
            return

        amount = int(self.amount.value)
        if amount < 1 or amount > 200:
            await interaction.response.send_message("Choose between 1 and 200 messages.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"Deleted {len(deleted)} message(s).", ephemeral=True)


class SlowmodeModal(discord.ui.Modal, title="Set Slowmode"):
    seconds = discord.ui.TextInput(label="Slowmode seconds", max_length=5)

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This action only works in a text channel.", ephemeral=True)
            return

        seconds = int(self.seconds.value)
        if seconds < 0 or seconds > 21600:
            await interaction.response.send_message("Slowmode must be between 0 and 21600 seconds.", ephemeral=True)
            return

        await interaction.channel.edit(slowmode_delay=seconds)
        await interaction.response.send_message(f"Slowmode set to {seconds} second(s).", ephemeral=True)


class AdminPanelView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=900)
        self.bot = bot

    def _can_access(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        return _can_access_admin_panel(self.bot, interaction.guild, interaction.user)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not self._can_access(interaction):
            await interaction.response.send_message(
                "This admin panel is restricted to the server owner, configured bot owners, members with Administrator/Manage Server, or the configured moderator role.",
                ephemeral=True,
            )
            return False
        return True

    def _summary_embed(self) -> discord.Embed:
        config = self.bot.config
        owner_ids = "\n".join(f"• {owner_id}" for owner_id in config.owner_ids) or "None"
        embed = make_embed(
            title=f"{config.project_name} Admin Panel",
            description="Use the buttons below to manage project settings, bot behavior, and operational controls.",
            color=config.theme_color,
        )
        embed.add_field(name="Access", value="Owner IDs, server owner, Manage Server, or Administrator", inline=False)
        embed.add_field(name="Bot Prefix", value=config.bot_prefix, inline=True)
        embed.add_field(name="Theme", value=f"#{config.theme_color:06X}", inline=True)
        embed.add_field(name="GitHub", value=config.github_repo or "Not configured", inline=False)
        embed.add_field(name="Current Status", value=config.current_build_status, inline=False)
        embed.add_field(name="Latest Version", value=config.latest_version, inline=True)
        embed.add_field(name="Owner IDs", value=owner_ids, inline=False)
        embed.add_field(name="Channels", value="\n".join(f"• {key}: {value}" for key, value in config.channels.items()) or "None", inline=False)
        ticket_settings = config.tickets
        embed.add_field(
            name="Tickets",
            value="\n".join(
                [
                    f"• Category: {ticket_settings.get('category_id', 0)}",
                    f"• Log Channel: {ticket_settings.get('log_channel_id', 0)}",
                    f"• Support Role: {ticket_settings.get('support_role_id', 0)}",
                    f"• Prefix: {ticket_settings.get('ticket_channel_prefix', 'ticket')}",
                    f"• Max/User: {ticket_settings.get('max_open_tickets', 1)}",
                    f"• Ping Role: {ticket_settings.get('ping_support_role', True)}",
                ]
            ),
            inline=False,
        )
        return embed

    @discord.ui.button(label="Summary", style=discord.ButtonStyle.secondary, row=0)
    async def summary_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=self._summary_embed(), ephemeral=True)

    @discord.ui.button(label="Project", style=discord.ButtonStyle.primary, row=0)
    async def project_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        config = self.bot.config
        modal = ProjectModal(self.bot)
        modal.project_name.default = config.project_name
        modal.tagline.default = config.tagline
        modal.vision.default = config.vision
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Status", style=discord.ButtonStyle.primary, row=0)
    async def status_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        config = self.bot.config
        modal = StatusModal(self.bot)
        modal.current_build_status.default = config.current_build_status
        modal.latest_version.default = config.latest_version
        modal.build_notes.default = config.build_notes
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Links", style=discord.ButtonStyle.primary, row=1)
    async def links_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        config = self.bot.config
        modal = LinksModal(self.bot)
        modal.github.default = config.links.get("github", "")
        modal.website.default = config.links.get("website", "")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="IDs", style=discord.ButtonStyle.primary, row=1)
    async def ids_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        config = self.bot.config
        modal = IDsModal(self.bot)
        modal.channels.default = "\n".join(f"{key}={value}" for key, value in config.channels.items())
        modal.roles.default = "\n".join(f"{key}={value}" for key, value in config.roles.items())
        modal.owners.default = "\n".join(str(owner_id) for owner_id in config.owner_ids)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Prefix/Theme", style=discord.ButtonStyle.primary, row=1)
    async def prefix_theme_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        config = self.bot.config
        modal = AppearanceModal(self.bot)
        modal.prefix.default = config.bot_prefix
        modal.theme_color.default = f"{config.theme_color:06X}"
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary, row=1)
    async def transcript_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This action only works in a text channel.", ephemeral=True)
            return

        cog = self.bot.get_cog("TicketsCog")
        if cog is None or not hasattr(cog, "export_ticket_transcript"):
            await interaction.response.send_message("Ticket system is unavailable right now.", ephemeral=True)
            return

        if not hasattr(interaction.user, "guild_permissions"):
            await interaction.response.send_message("This action only works for server members.", ephemeral=True)
            return

        if not cog._is_ticket_channel(interaction.channel):
            await interaction.response.send_message("This button only works inside a ticket channel.", ephemeral=True)
            return

        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if member is None:
            await interaction.response.send_message("This action only works for server members.", ephemeral=True)
            return

        if not cog._can_manage_tickets(member) and cog._ticket_owner_id(interaction.channel) != member.id:
            await interaction.response.send_message("Only the ticket owner or support staff can export a transcript.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        transcript = await cog.export_ticket_transcript(interaction.channel, member)
        log_channel = await cog._ticket_log_channel(interaction.channel.guild)
        if log_channel is not None:
            await interaction.followup.send("Transcript sent to the ticket log channel.", ephemeral=True)
        else:
            await interaction.followup.send(file=transcript, ephemeral=True)

    @discord.ui.button(label="Welcome", style=discord.ButtonStyle.primary, row=2)
    async def welcome_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        config = self.bot.config
        modal = WelcomeModal(self.bot)
        modal.dm_message.default = config.welcome.get("dm_message", "")
        modal.public_message.default = config.welcome.get("public_message", "")
        modal.default_role.default = "yes" if config.welcome.get("assign_default_role", True) else "no"
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Anti-Spam", style=discord.ButtonStyle.primary, row=2)
    async def anti_spam_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        config = self.bot.config
        modal = AntiSpamModal(self.bot)
        modal.message_limit.default = str(config.anti_spam.get("message_limit", 5))
        modal.window_seconds.default = str(config.anti_spam.get("window_seconds", 8))
        modal.timeout_seconds.default = str(config.anti_spam.get("timeout_seconds", 30))
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="GitHub", style=discord.ButtonStyle.primary, row=2)
    async def github_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        config = self.bot.config
        modal = GitHubModal(self.bot)
        modal.repo_owner.default = config.github.get("repo_owner", "")
        modal.repo_name.default = config.github.get("repo_name", "")
        modal.poll_interval_minutes.default = str(config.github.get("poll_interval_minutes", 5))
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Ticket Panel", style=discord.ButtonStyle.success, row=2)
    async def ticket_panel_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This action only works in a text channel.", ephemeral=True)
            return

        cog = self.bot.get_cog("TicketsCog")
        if cog is None or not hasattr(cog, "post_ticket_panel"):
            await interaction.response.send_message("Ticket system is unavailable right now.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        await cog.post_ticket_panel(interaction.channel)
        await interaction.followup.send(f"Ticket panel posted in {interaction.channel.mention}.", ephemeral=True)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, row=2)
    async def close_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This action only works in a text channel.", ephemeral=True)
            return

        cog = self.bot.get_cog("TicketsCog")
        if cog is None or not hasattr(cog, "close_ticket_channel"):
            await interaction.response.send_message("Ticket system is unavailable right now.", ephemeral=True)
            return

        ticket_cog = cog
        if not hasattr(ticket_cog, "can_close_ticket"):
            await interaction.response.send_message("Ticket system is unavailable right now.", ephemeral=True)
            return

        if not hasattr(interaction.user, "guild_permissions"):
            await interaction.response.send_message("This action only works for server members.", ephemeral=True)
            return

        if not ticket_cog._is_ticket_channel(interaction.channel):
            await interaction.response.send_message("This button only works inside a ticket channel.", ephemeral=True)
            return

        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if member is None:
            await interaction.response.send_message("This action only works for server members.", ephemeral=True)
            return

        if not ticket_cog.can_close_ticket(interaction.channel, member):
            await interaction.response.send_message("Only the ticket owner or support staff can close this ticket.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        await ticket_cog.close_ticket_channel(interaction.channel, member, f"Closed from admin panel by {member}")

    @discord.ui.button(label="Logging", style=discord.ButtonStyle.primary, row=3)
    async def logging_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        config = self.bot.config
        modal = LoggingModal(self.bot)
        modal.local_file.default = "yes" if config.logging.get("local_file", True) else "no"
        modal.file_path.default = config.logging.get("file_path", "logs/bot.log")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Starboard", style=discord.ButtonStyle.primary, row=3)
    async def starboard_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        config = self.bot.config
        modal = StarboardModal(self.bot)
        modal.channel_id.default = str(config.starboard.get("channel_id", 0))
        modal.emoji.default = str(config.starboard.get("emoji", "⭐"))
        modal.threshold.default = str(config.starboard.get("threshold", 3))
        modal.excluded_channel_ids.default = "\n".join(str(channel_id) for channel_id in config.starboard.get("excluded_channel_ids", []))
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Tickets", style=discord.ButtonStyle.primary, row=4)
    async def tickets_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        config = self.bot.config
        modal = TicketsModal(self.bot)
        modal.category_id.default = str(config.tickets.get("category_id", 0))
        modal.log_channel_id.default = str(config.tickets.get("log_channel_id", 0))
        modal.support_role_id.default = str(config.tickets.get("support_role_id", 0))
        modal.ticket_channel_prefix.default = str(config.tickets.get("ticket_channel_prefix", "ticket"))
        modal.max_open_tickets.default = str(config.tickets.get("max_open_tickets", 1))
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Purge", style=discord.ButtonStyle.danger, row=4)
    async def purge_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(PurgeModal(self.bot))

    @discord.ui.button(label="Lock", style=discord.ButtonStyle.danger, row=4)
    async def lock_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This action only works in a text channel.", ephemeral=True)
            return
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message(f"Locked {interaction.channel.mention}.", ephemeral=True)

    @discord.ui.button(label="Unlock", style=discord.ButtonStyle.success, row=4)
    async def unlock_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This action only works in a text channel.", ephemeral=True)
            return
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=None)
        await interaction.response.send_message(f"Unlocked {interaction.channel.mention}.", ephemeral=True)

    @discord.ui.button(label="Slowmode", style=discord.ButtonStyle.secondary, row=4)
    async def slowmode_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(SlowmodeModal(self.bot))

    @discord.ui.button(label="Reload Config", style=discord.ButtonStyle.secondary, row=3)
    async def reload_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        self.bot.config = load_config(self.bot.config_path)
        await interaction.followup.send("Configuration reloaded from disk.", ephemeral=True)

    @discord.ui.button(label="Sync Commands", style=discord.ButtonStyle.success, row=3)
    async def sync_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        if self.bot.config.guild_id:
            guild = discord.Object(id=self.bot.config.guild_id)
            self.bot.tree.copy_global_to(guild=guild)
            await self.bot.tree.sync(guild=guild)
        else:
            await self.bot.tree.sync()
        await interaction.followup.send("Slash commands synced.", ephemeral=True)

    @discord.ui.button(label="Reload Cogs", style=discord.ButtonStyle.danger, row=3)
    async def reload_cogs_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        extensions = (
            "bot.cogs.info",
            "bot.cogs.reports",
            "bot.cogs.onboarding",
            "bot.cogs.roles",
            "bot.cogs.moderation",
            "bot.cogs.github",
            "bot.cogs.starboard",
            "bot.cogs.tickets",
            "bot.cogs.fun",
        )
        for extension in extensions:
            await self.bot.reload_extension(extension)
        await interaction.followup.send("Core cogs reloaded.", ephemeral=True)


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="admin", description="Open the bot admin panel")
    @commands.guild_only()
    async def admin(self, context: commands.Context) -> None:
        allowed = isinstance(context.author, discord.Member) and _can_access_admin_panel(self.bot, context.guild, context.author)
        if not allowed:
            await context.reply(
                "You do not have access to the admin panel. You need to be the server owner, a configured bot owner, have Administrator/Manage Server, or hold the configured moderator role.",
                mention_author=False,
            )
            return

        embed = make_embed(
            title=f"{self.bot.config.project_name} Admin Panel",
            description="Use the buttons below to manage project settings, bot behavior, and operational controls.",
            color=self.bot.config.theme_color,
        )
        embed.add_field(name="Access", value="Trusted owners, server owner, Manage Server, or Administrator", inline=False)
        embed.add_field(name="Editing", value="Saved directly to config.json", inline=True)
        embed.add_field(name="Tip", value="Use the modal fields to update details without touching code.", inline=False)
        await context.reply(embed=embed, view=AdminPanelView(self.bot), mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
