from __future__ import annotations

import io
import json
import re
from datetime import datetime, timezone

import discord
from discord.ext import commands

from bot.utils import make_embed


TICKET_TOPIC_PREFIX = "OlyntheOS-TICKET"

TICKET_TYPES: dict[str, tuple[str, str]] = {
    "support": ("Support", "🛠️"),
    "bug": ("Bug Report", "🐛"),
    "feature": ("Feature Request", "✨"),
    "general": ("General Help", "💬"),
}


def _truncate(value: str, limit: int = 1024) -> str:
    return value if len(value) <= limit else value[: limit - 3] + "..."


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "ticket"


class TicketOpenModal(discord.ui.Modal, title="Open a Support Ticket"):
    reason = discord.ui.TextInput(
        label="Describe your request",
        style=discord.TextStyle.paragraph,
        placeholder="Describe the issue or request in a few words.",
        max_length=800,
    )

    def __init__(self, bot: commands.Bot, ticket_type: str = "support"):
        super().__init__(timeout=300)
        self.bot = bot
        self.ticket_type = ticket_type

    async def on_submit(self, interaction: discord.Interaction) -> None:
        cog = interaction.client.get_cog("TicketsCog")
        if not isinstance(cog, TicketsCog):
            await interaction.response.send_message("Ticket system is unavailable right now.", ephemeral=True)
            return

        await cog.create_ticket(interaction, str(self.reason.value), self.ticket_type)


class TicketTypeSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        options = [
            discord.SelectOption(label=label, value=value, emoji=emoji)
            for value, (label, emoji) in TICKET_TYPES.items()
        ]
        super().__init__(
            placeholder="Choose a ticket type",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="olyntheos:tickets:type-select",
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction) -> None:
        cog = interaction.client.get_cog("TicketsCog")
        if not isinstance(cog, TicketsCog):
            await interaction.response.send_message("Ticket system is unavailable right now.", ephemeral=True)
            return

        await interaction.response.send_modal(TicketOpenModal(self.bot, self.values[0]))


class TicketPanelOpenButton(discord.ui.Button):
    def __init__(self, bot: commands.Bot):
        super().__init__(
            label="Open Ticket",
            style=discord.ButtonStyle.primary,
            emoji="🎫",
            custom_id="olyntheos:tickets:open",
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(TicketOpenModal(self.bot))


class TicketPanelView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(TicketTypeSelect(bot))
        self.add_item(TicketPanelOpenButton(bot))


class TicketControlView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    def _cog(self) -> TicketsCog | None:
        cog = self.bot.get_cog("TicketsCog")
        return cog if isinstance(cog, TicketsCog) else None

    def _channel(self, interaction: discord.Interaction) -> discord.TextChannel | None:
        return interaction.channel if isinstance(interaction.channel, discord.TextChannel) else None

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary, emoji="🧷", custom_id="olyntheos:tickets:claim")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        cog = self._cog()
        channel = self._channel(interaction)
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if cog is None or channel is None or member is None or not cog._is_ticket_channel(channel):
            await interaction.response.send_message("This button only works inside a ticket channel.", ephemeral=True)
            return
        if not cog._can_manage_tickets(member):
            await interaction.response.send_message("Only support staff can claim tickets.", ephemeral=True)
            return

        await cog.claim_ticket(channel, member)
        await interaction.response.send_message("Ticket claimed.", ephemeral=True)

    @discord.ui.button(label="Unclaim", style=discord.ButtonStyle.secondary, emoji="♻️", custom_id="olyntheos:tickets:unclaim")
    async def unclaim_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        cog = self._cog()
        channel = self._channel(interaction)
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if cog is None or channel is None or member is None or not cog._is_ticket_channel(channel):
            await interaction.response.send_message("This button only works inside a ticket channel.", ephemeral=True)
            return
        if not cog._can_manage_tickets(member):
            await interaction.response.send_message("Only support staff can unclaim tickets.", ephemeral=True)
            return

        await cog.unclaim_ticket(channel)
        await interaction.response.send_message("Ticket unclaimed.", ephemeral=True)

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary, emoji="📄", custom_id="olyntheos:tickets:transcript")
    async def transcript_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        cog = self._cog()
        channel = self._channel(interaction)
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if cog is None or channel is None or member is None or not cog._is_ticket_channel(channel):
            await interaction.response.send_message("This button only works inside a ticket channel.", ephemeral=True)
            return
        if not cog._can_manage_tickets(member) and channel.topic and cog._ticket_owner_id(channel) != member.id:
            await interaction.response.send_message("Only the ticket owner or support staff can export a transcript.", ephemeral=True)
            return

        transcript = await cog._build_transcript(channel)
        log_channel = await cog._ticket_log_channel(channel.guild)
        if log_channel is not None:
            await log_channel.send(content=f"Transcript for {channel.mention}", file=transcript)
            await interaction.response.send_message("Transcript sent to the ticket log channel.", ephemeral=True)
        else:
            await interaction.response.send_message(file=transcript, ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="olyntheos:tickets:close")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        cog = self._cog()
        channel = self._channel(interaction)
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if cog is None or channel is None or member is None or not cog._is_ticket_channel(channel):
            await interaction.response.send_message("This button only works inside a ticket channel.", ephemeral=True)
            return

        if not cog.can_close_ticket(channel, member):
            await interaction.response.send_message("Only the ticket owner or support staff can close this ticket.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        await cog.close_ticket_channel(channel, member, "Closed via ticket controls")
        await interaction.followup.send("Ticket closed.", ephemeral=True)


class TicketsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _settings(self) -> dict[str, object]:
        return self.bot.config.tickets

    def _category_id(self) -> int:
        return int(self._settings().get("category_id", 0))

    def _log_channel_id(self) -> int:
        return int(self._settings().get("log_channel_id", 0))

    def _support_role_id(self) -> int:
        return int(self._settings().get("support_role_id", 0))

    def _ticket_prefix(self) -> str:
        prefix = str(self._settings().get("ticket_channel_prefix", "ticket")).strip().lower()
        return _slugify(prefix)

    def _max_open_tickets(self) -> int:
        return max(1, int(self._settings().get("max_open_tickets", 1)))

    def _ping_support_role(self) -> bool:
        return bool(self._settings().get("ping_support_role", True))

    def _topic_payload(self, owner_id: int, reason: str, claimed_by: int = 0) -> str:
        payload = {
            "owner_id": owner_id,
            "claimed_by": claimed_by,
            "reason": reason,
            "ticket_type": "support",
        }
        return f"{TICKET_TOPIC_PREFIX} {json.dumps(payload, separators=(",", ":"), ensure_ascii=False)}"

    def _ticket_type_label(self, ticket_type: str) -> str:
        return TICKET_TYPES.get(ticket_type, (ticket_type.title(), "🎫"))[0]

    def _ticket_type_emoji(self, ticket_type: str) -> str:
        return TICKET_TYPES.get(ticket_type, (ticket_type.title(), "🎫"))[1]

    def _parse_topic(self, topic: str | None) -> dict[str, object] | None:
        if not topic or not topic.startswith(TICKET_TOPIC_PREFIX):
            return None
        raw = topic[len(TICKET_TOPIC_PREFIX) :].strip()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _is_ticket_channel(self, channel: discord.abc.GuildChannel | None) -> bool:
        return isinstance(channel, discord.TextChannel) and self._parse_topic(channel.topic) is not None

    def _ticket_owner_id(self, channel: discord.TextChannel) -> int | None:
        payload = self._parse_topic(channel.topic)
        if not payload:
            return None
        try:
            return int(payload.get("owner_id", 0)) or None
        except (TypeError, ValueError):
            return None

    def _ticket_claimed_by(self, channel: discord.TextChannel) -> int | None:
        payload = self._parse_topic(channel.topic)
        if not payload:
            return None
        try:
            claimed_by = int(payload.get("claimed_by", 0))
            return claimed_by or None
        except (TypeError, ValueError):
            return None

    def _find_open_ticket(self, guild: discord.Guild, member_id: int) -> discord.TextChannel | None:
        for channel in guild.text_channels:
            if self._ticket_owner_id(channel) == member_id:
                return channel
        return None

    def _can_manage_tickets(self, member: discord.Member) -> bool:
        permissions = member.guild_permissions
        support_role_id = self._support_role_id()
        has_support_role = bool(support_role_id and any(role.id == support_role_id for role in member.roles))
        return bool(permissions.administrator or permissions.manage_channels or permissions.manage_guild or has_support_role)

    def _ticket_permissions(self, guild: discord.Guild, owner: discord.Member) -> dict[discord.abc.Snowflake, discord.PermissionOverwrite]:
        permissions: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            owner: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True),
        }
        support_role_id = self._support_role_id()
        support_role = guild.get_role(support_role_id) if support_role_id else None
        if support_role is not None:
            permissions[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True)
        me = guild.me
        if me is not None:
            permissions[me] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True, attach_files=True, embed_links=True)
        return permissions

    async def _ticket_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        channel_id = self._log_channel_id()
        if not channel_id:
            return None
        channel = guild.get_channel(channel_id)
        return channel if isinstance(channel, discord.TextChannel) else None

    async def _ticket_category(self, guild: discord.Guild) -> discord.CategoryChannel | None:
        channel_id = self._category_id()
        if not channel_id:
            return None
        channel = guild.get_channel(channel_id)
        return channel if isinstance(channel, discord.CategoryChannel) else None

    async def _open_ticket_channel(
        self,
        guild: discord.Guild,
        member: discord.Member,
        reason: str,
        ticket_type: str = "support",
    ) -> discord.TextChannel | None:
        category = await self._ticket_category(guild)
        if category is None:
            return None

        existing_ticket = self._find_open_ticket(guild, member.id)
        max_open_tickets = self._max_open_tickets()
        user_ticket_count = sum(1 for channel in guild.text_channels if self._ticket_owner_id(channel) == member.id)
        if existing_ticket is not None and user_ticket_count >= max_open_tickets:
            return existing_ticket

        channel_name = f"{self._ticket_prefix()}-{_slugify(ticket_type)}-{_slugify(member.display_name)}"
        payload = {
            "owner_id": member.id,
            "claimed_by": 0,
            "reason": _truncate(reason, 400),
            "ticket_type": ticket_type,
        }
        topic = f"{TICKET_TOPIC_PREFIX} {json.dumps(payload, separators=(",", ":"), ensure_ascii=False)}"
        overwrites = self._ticket_permissions(guild, member)
        ticket_channel = await guild.create_text_channel(
            name=channel_name[:100],
            category=category,
            topic=topic,
            overwrites=overwrites,
            reason=f"Ticket opened by {member}",
        )

        support_role = guild.get_role(self._support_role_id())
        mention_text = support_role.mention if support_role and self._ping_support_role() else ""
        ticket_label = self._ticket_type_label(ticket_type)
        ticket_emoji = self._ticket_type_emoji(ticket_type)
        embed = make_embed(
            title=f"{ticket_emoji} {ticket_label} Opened",
            description="Thanks for reaching out. A staff member will be with you shortly.",
            color=self.bot.config.theme_color,
        )
        embed.add_field(name="Requester", value=f"{member.mention} ({member})", inline=False)
        embed.add_field(name="Type", value=ticket_label, inline=True)
        embed.add_field(name="Reason", value=_truncate(reason, 900), inline=False)
        embed.add_field(name="Channel", value=ticket_channel.mention, inline=True)
        embed.add_field(name="Status", value="Open", inline=True)
        await ticket_channel.send(content=mention_text, embed=embed, view=TicketControlView(self.bot))
        await self._send_log(guild, "Ticket opened", member, ticket_channel, reason)
        return ticket_channel

    async def create_ticket(self, interaction: discord.Interaction, reason: str, ticket_type: str = "support") -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Tickets can only be opened inside the server.", ephemeral=True)
            return

        guild = interaction.guild
        member = interaction.user
        if await self._ticket_category(guild) is None:
            await interaction.response.send_message("Ticket category is not configured.", ephemeral=True)
            return

        existing_ticket = self._find_open_ticket(guild, member.id)
        if existing_ticket is not None and sum(1 for channel in guild.text_channels if self._ticket_owner_id(channel) == member.id) >= self._max_open_tickets():
            await interaction.response.send_message(f"You already have an open ticket: {existing_ticket.mention}", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        ticket_channel = await self._open_ticket_channel(guild, member, reason, ticket_type)
        if ticket_channel is None:
            await interaction.followup.send("Ticket category is not configured.", ephemeral=True)
            return
        if ticket_channel is existing_ticket:
            await interaction.followup.send(f"You already have an open ticket: {ticket_channel.mention}", ephemeral=True)
            return

        await interaction.followup.send(f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)

    async def build_panel_embed(self) -> discord.Embed:
        embed = make_embed(
            title=f"{self.bot.config.project_name} Support Tickets",
            description="Choose a ticket type, describe the issue, and the bot will open a private support channel.",
            color=self.bot.config.theme_color,
        )
        embed.add_field(name="Ticket Types", value="• Support\n• Bug Report\n• Feature Request\n• General Help", inline=False)
        embed.add_field(name="Guidelines", value="• Be clear and concise\n• One topic per ticket\n• Staff will reply as soon as possible", inline=False)
        return embed

    async def post_ticket_panel(self, channel: discord.TextChannel) -> discord.Message:
        return await channel.send(embed=await self.build_panel_embed(), view=TicketPanelView(self.bot))

    async def _send_log(self, guild: discord.Guild, title: str, member: discord.Member, channel: discord.TextChannel, reason: str, closed_by: discord.Member | None = None) -> None:
        log_channel = await self._ticket_log_channel(guild)
        if log_channel is None:
            return

        embed = make_embed(title=title, description=f"{member.mention} {title.lower()} in {channel.mention}.", color=self.bot.config.theme_color)
        embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=False)
        embed.add_field(name="Channel", value=channel.mention, inline=True)
        embed.add_field(name="Reason", value=_truncate(reason, 900), inline=False)
        if closed_by is not None:
            embed.add_field(name="Closed By", value=f"{closed_by.mention} ({closed_by.id})", inline=False)
        await log_channel.send(embed=embed)

    async def claim_ticket(self, channel: discord.TextChannel, member: discord.Member) -> None:
        payload = self._parse_topic(channel.topic) or {}
        payload["claimed_by"] = member.id
        payload.setdefault("owner_id", self._ticket_owner_id(channel) or 0)
        payload.setdefault("reason", "No reason provided")
        payload.setdefault("ticket_type", "support")
        await channel.edit(topic=f"{TICKET_TOPIC_PREFIX} {json.dumps(payload, separators=(",", ":"), ensure_ascii=False)}")
        await channel.send(embed=make_embed(title="Ticket Claimed", description=f"{member.mention} has claimed this ticket.", color=self.bot.config.theme_color))

    async def unclaim_ticket(self, channel: discord.TextChannel) -> None:
        payload = self._parse_topic(channel.topic) or {}
        payload["claimed_by"] = 0
        payload.setdefault("owner_id", self._ticket_owner_id(channel) or 0)
        payload.setdefault("reason", "No reason provided")
        payload.setdefault("ticket_type", "support")
        await channel.edit(topic=f"{TICKET_TOPIC_PREFIX} {json.dumps(payload, separators=(",", ":"), ensure_ascii=False)}")
        await channel.send(embed=make_embed(title="Ticket Unclaimed", description="This ticket is no longer claimed.", color=self.bot.config.theme_color))

    def can_close_ticket(self, channel: discord.TextChannel, member: discord.Member) -> bool:
        owner_id = self._ticket_owner_id(channel)
        return bool(owner_id is not None and (member.id == owner_id or self._can_manage_tickets(member)))

    async def close_ticket_channel(self, channel: discord.TextChannel, member: discord.Member, reason: str) -> None:
        owner_id = self._ticket_owner_id(channel)
        if owner_id is None:
            return

        transcript = await self._build_transcript(channel)
        log_channel = await self._ticket_log_channel(channel.guild)
        if log_channel is not None:
            payload = self._parse_topic(channel.topic) or {}
            owner = channel.guild.get_member(owner_id)
            embed = make_embed(
                title="Ticket Closed",
                description=f"Ticket channel {channel.mention} was closed.",
                color=self.bot.config.theme_color,
            )
            embed.add_field(name="Owner", value=owner.mention if owner else f"<@{owner_id}>", inline=False)
            embed.add_field(name="Closed By", value=member.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Claimed By", value=f"<@{int(payload.get('claimed_by', 0))}>" if int(payload.get("claimed_by", 0)) else "Unclaimed", inline=True)
            await log_channel.send(embed=embed, file=transcript)
        else:
            await channel.send(file=transcript)

        await channel.delete(reason=f"Ticket closed by {member} | {reason}")

    async def _build_transcript(self, channel: discord.TextChannel) -> discord.File:
        lines: list[str] = []
        async for message in channel.history(limit=1000, oldest_first=True):
            timestamp = message.created_at.astimezone(timezone.utc).isoformat()
            content = message.content or ""
            attachments = " ".join(attachment.url for attachment in message.attachments)
            line = f"[{timestamp}] {message.author} ({message.author.id}): {content}"
            if attachments:
                line = f"{line} {attachments}"
            lines.append(line)

        transcript = "\n".join(lines) or "No messages recorded."
        if len(transcript) > 55000:
            transcript = transcript[:55000] + "\n\n[Transcript truncated]"
        buffer = io.BytesIO(transcript.encode("utf-8"))
        filename = f"ticket-{channel.id}-transcript.txt"
        buffer.seek(0)
        return discord.File(buffer, filename=filename)

    async def build_transcript_file(self, channel: discord.TextChannel) -> discord.File:
        return await self._build_transcript(channel)

    async def export_ticket_transcript(self, channel: discord.TextChannel, requester: discord.Member) -> discord.File:
        transcript = await self._build_transcript(channel)
        log_channel = await self._ticket_log_channel(channel.guild)
        if log_channel is not None:
            await log_channel.send(content=f"Transcript for {channel.mention} requested by {requester.mention}", file=transcript)
            return await self._build_transcript(channel)
        return transcript

    @commands.hybrid_command(name="ticket", description="Open a support ticket")
    async def ticket(self, context: commands.Context, *, reason: str = "No reason provided") -> None:
        if context.guild is None or not isinstance(context.author, discord.Member):
            await context.reply("Tickets can only be opened inside the server.", mention_author=False)
            return

        existing_ticket = self._find_open_ticket(context.guild, context.author.id)
        if existing_ticket is not None and sum(1 for channel in context.guild.text_channels if self._ticket_owner_id(channel) == context.author.id) >= self._max_open_tickets():
            await context.reply(f"You already have an open ticket: {existing_ticket.mention}", mention_author=False)
            return

        ticket_channel = await self._open_ticket_channel(context.guild, context.author, reason)
        if ticket_channel is None:
            await context.reply("Ticket category is not configured.", mention_author=False)
            return
        if existing_ticket is not None and ticket_channel.id == existing_ticket.id:
            await context.reply(f"You already have an open ticket: {ticket_channel.mention}", mention_author=False)
            return

        await context.reply(f"Your ticket has been created: {ticket_channel.mention}", mention_author=False)

    @commands.hybrid_command(name="ticketpanel", description="Send the ticket panel")
    @commands.has_permissions(manage_guild=True)
    async def ticketpanel(self, context: commands.Context, channel: discord.TextChannel | None = None) -> None:
        target_channel = channel or context.channel
        if not isinstance(target_channel, discord.TextChannel):
            await context.reply("This command can only be used in a text channel.", mention_author=False)
            return

        await self.post_ticket_panel(target_channel)
        await context.reply(f"Ticket panel posted in {target_channel.mention}.", mention_author=False)

    @commands.hybrid_command(name="ticketclose", description="Close the current ticket")
    async def ticketclose(self, context: commands.Context, *, reason: str = "Closed by staff") -> None:
        if not isinstance(context.channel, discord.TextChannel) or not self._is_ticket_channel(context.channel):
            await context.reply("This command can only be used inside a ticket channel.", mention_author=False)
            return

        member = context.author if isinstance(context.author, discord.Member) else None
        owner_id = self._ticket_owner_id(context.channel)
        if member is None or owner_id is None:
            await context.reply("This ticket could not be identified.", mention_author=False)
            return
        if member.id != owner_id and not self._can_manage_tickets(member):
            await context.reply("Only the ticket owner or support staff can close this ticket.", mention_author=False)
            return

        await context.reply("Closing ticket in 5 seconds. A transcript will be saved first.", mention_author=False)
        await self.close_ticket_channel(context.channel, member, reason)

    @commands.hybrid_command(name="ticketclaim", description="Claim the current ticket")
    @commands.has_permissions(manage_channels=True)
    async def ticketclaim(self, context: commands.Context) -> None:
        if not isinstance(context.channel, discord.TextChannel) or not self._is_ticket_channel(context.channel):
            await context.reply("This command can only be used inside a ticket channel.", mention_author=False)
            return
        if not isinstance(context.author, discord.Member):
            return

        await self.claim_ticket(context.channel, context.author)
        embed = make_embed(title="Ticket Claimed", description=f"{context.author.mention} has claimed this ticket.", color=self.bot.config.theme_color)
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="ticketadd", description="Add a member to the current ticket")
    @commands.has_permissions(manage_channels=True)
    async def ticketadd(self, context: commands.Context, member: discord.Member) -> None:
        if not isinstance(context.channel, discord.TextChannel) or not self._is_ticket_channel(context.channel):
            await context.reply("This command can only be used inside a ticket channel.", mention_author=False)
            return

        await context.channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True)
        await context.reply(f"Added {member.mention} to this ticket.", mention_author=False)

    @commands.hybrid_command(name="ticketremove", description="Remove a member from the current ticket")
    @commands.has_permissions(manage_channels=True)
    async def ticketremove(self, context: commands.Context, member: discord.Member) -> None:
        if not isinstance(context.channel, discord.TextChannel) or not self._is_ticket_channel(context.channel):
            await context.reply("This command can only be used inside a ticket channel.", mention_author=False)
            return

        await context.channel.set_permissions(member, overwrite=None)
        await context.reply(f"Removed {member.mention} from this ticket.", mention_author=False)

    @commands.hybrid_command(name="ticketrename", description="Rename the current ticket channel")
    @commands.has_permissions(manage_channels=True)
    async def ticketrename(self, context: commands.Context, *, name: str) -> None:
        if not isinstance(context.channel, discord.TextChannel) or not self._is_ticket_channel(context.channel):
            await context.reply("This command can only be used inside a ticket channel.", mention_author=False)
            return

        new_name = f"{self._ticket_prefix()}-{_slugify(name)}"[:100]
        await context.channel.edit(name=new_name)
        await context.reply(f"Ticket renamed to {new_name}.", mention_author=False)


async def setup(bot: commands.Bot) -> None:
    view = TicketPanelView(bot)
    bot.add_view(view)
    bot.add_view(TicketControlView(bot))
    await bot.add_cog(TicketsCog(bot))