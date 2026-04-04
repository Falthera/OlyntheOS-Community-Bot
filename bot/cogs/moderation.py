from __future__ import annotations

from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

from bot.config import save_config
from bot.utils import make_embed


class ModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.warned_members: dict[int, int] = {}

    def _next_case_number(self) -> int:
        cases = self.bot.config.warning_cases
        if not cases:
            return 1
        return max(int(case.get("case_number", 0)) for case in cases) + 1

    def _member_cases(self, member_id: int) -> list[dict[str, object]]:
        return [case for case in self.bot.config.warning_cases if int(case.get("member_id", 0)) == member_id]

    def _format_case(self, case: dict[str, object]) -> str:
        reason = str(case.get("reason", "No reason provided"))
        moderator_id = int(case.get("moderator_id", 0))
        moderator = f"<@{moderator_id}>" if moderator_id else "Unknown"
        created_at = str(case.get("created_at", "Unknown time"))
        case_number = case.get("case_number", "?")
        return f"**Case #{case_number}** • {created_at} • {moderator}\n{reason}"

    async def _save_cases(self) -> None:
        save_config(self.bot.config, self.bot.config_path)

    @commands.hybrid_command(name="warn", description="Warn a member")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, context: commands.Context, member: discord.Member, *, reason: str = "No reason provided") -> None:
        case_number = self._next_case_number()
        self.warned_members[member.id] = self.warned_members.get(member.id, 0) + 1
        case = {
            "case_number": case_number,
            "member_id": member.id,
            "moderator_id": context.author.id,
            "reason": reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.bot.config.warning_cases.append(case)
        await self._save_cases()
        embed = make_embed(title="Member Warned", description=f"{member.mention} has been warned.", color=self.bot.config.theme_color)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Warnings", value=str(self.warned_members[member.id]), inline=True)
        embed.add_field(name="Case", value=f"#{case_number}", inline=True)
        await context.reply(embed=embed, mention_author=False)
        await self._log_action(context.guild, f"{context.author} warned {member} | {reason}")

    @commands.hybrid_command(name="cases", aliases=["warnings"], description="Show a member's warning history")
    @commands.has_permissions(moderate_members=True)
    async def cases(self, context: commands.Context, member: discord.Member) -> None:
        cases = self._member_cases(member.id)
        embed = make_embed(
            title=f"Warning History for {member.display_name}",
            description=f"Total cases: {len(cases)}",
            color=self.bot.config.theme_color,
        )
        if not cases:
            embed.add_field(name="History", value="No warning cases recorded.", inline=False)
        else:
            for case in cases[-10:]:
                embed.add_field(
                    name=f"Case #{case.get('case_number', '?')}",
                    value=self._format_case(case),
                    inline=False,
                )
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="clearwarnings", description="Clear a member's warning history")
    @commands.has_permissions(moderate_members=True)
    async def clearwarnings(self, context: commands.Context, member: discord.Member) -> None:
        remaining = [case for case in self.bot.config.warning_cases if int(case.get("member_id", 0)) != member.id]
        removed = len(self.bot.config.warning_cases) - len(remaining)
        self.bot.config.warning_cases = remaining
        self.warned_members.pop(member.id, None)
        await self._save_cases()

        embed = make_embed(
            title="Warning History Cleared",
            description=f"Removed {removed} case(s) for {member.mention}.",
            color=self.bot.config.theme_color,
        )
        await context.reply(embed=embed, mention_author=False)
        await self._log_action(context.guild, f"{context.author} cleared {removed} warning case(s) for {member}")

    @commands.hybrid_command(name="mute", description="Timeout a member")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, context: commands.Context, member: discord.Member, minutes: int, *, reason: str = "No reason provided") -> None:
        timeout_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        await member.timeout(timeout_until, reason=reason)
        embed = make_embed(title="Member Muted", description=f"{member.mention} has been timed out for {minutes} minute(s).", color=self.bot.config.theme_color)
        embed.add_field(name="Reason", value=reason, inline=False)
        await context.reply(embed=embed, mention_author=False)
        await self._log_action(context.guild, f"{context.author} muted {member} for {minutes}m | {reason}")

    @commands.hybrid_command(name="kick", description="Kick a member")
    @commands.has_permissions(kick_members=True)
    async def kick(self, context: commands.Context, member: discord.Member, *, reason: str = "No reason provided") -> None:
        await member.kick(reason=reason)
        embed = make_embed(title="Member Kicked", description=f"{member} has been kicked.", color=self.bot.config.theme_color)
        embed.add_field(name="Reason", value=reason, inline=False)
        await context.reply(embed=embed, mention_author=False)
        await self._log_action(context.guild, f"{context.author} kicked {member} | {reason}")

    @commands.hybrid_command(name="purge", description="Delete a number of recent messages")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, context: commands.Context, amount: int) -> None:
        if amount < 1 or amount > 200:
            await context.reply("Please choose a number between 1 and 200.", mention_author=False)
            return

        deleted = await context.channel.purge(limit=amount + 1)
        confirmation = await context.send(f"Deleted {len(deleted) - 1} message(s).")
        await confirmation.delete(delay=4)
        await self._log_action(context.guild, f"{context.author} purged {len(deleted) - 1} message(s) in {context.channel}")

    @commands.hybrid_command(name="lock", description="Lock a text channel")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, context: commands.Context, channel: discord.TextChannel | None = None, *, reason: str = "No reason provided") -> None:
        target = channel or context.channel
        if not isinstance(target, discord.TextChannel):
            await context.reply("This command can only be used in or on a text channel.", mention_author=False)
            return

        await target.set_permissions(target.guild.default_role, send_messages=False, reason=reason)
        embed = make_embed(title="Channel Locked", description=f"{target.mention} has been locked.", color=self.bot.config.theme_color)
        embed.add_field(name="Reason", value=reason, inline=False)
        await context.reply(embed=embed, mention_author=False)
        await self._log_action(context.guild, f"{context.author} locked {target} | {reason}")

    @commands.hybrid_command(name="unlock", description="Unlock a text channel")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, context: commands.Context, channel: discord.TextChannel | None = None, *, reason: str = "No reason provided") -> None:
        target = channel or context.channel
        if not isinstance(target, discord.TextChannel):
            await context.reply("This command can only be used in or on a text channel.", mention_author=False)
            return

        await target.set_permissions(target.guild.default_role, send_messages=None, reason=reason)
        embed = make_embed(title="Channel Unlocked", description=f"{target.mention} has been unlocked.", color=self.bot.config.theme_color)
        embed.add_field(name="Reason", value=reason, inline=False)
        await context.reply(embed=embed, mention_author=False)
        await self._log_action(context.guild, f"{context.author} unlocked {target} | {reason}")

    @commands.hybrid_command(name="slowmode", description="Set slowmode for a text channel")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, context: commands.Context, seconds: int, channel: discord.TextChannel | None = None) -> None:
        target = channel or context.channel
        if not isinstance(target, discord.TextChannel):
            await context.reply("This command can only be used in or on a text channel.", mention_author=False)
            return
        if seconds < 0 or seconds > 21600:
            await context.reply("Slowmode must be between 0 and 21600 seconds.", mention_author=False)
            return

        await target.edit(slowmode_delay=seconds)
        embed = make_embed(title="Slowmode Updated", description=f"{target.mention} is now set to {seconds} second(s).", color=self.bot.config.theme_color)
        await context.reply(embed=embed, mention_author=False)
        await self._log_action(context.guild, f"{context.author} set slowmode on {target} to {seconds}s")

    async def _log_action(self, guild: discord.Guild | None, message: str) -> None:
        if guild is None:
            return
        channel_id = self.bot.config.channels.get("moderation_log")
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            await channel.send(message)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationCog(bot))
