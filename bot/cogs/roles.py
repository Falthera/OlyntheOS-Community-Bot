from __future__ import annotations

import discord
from discord.ext import commands

from bot.utils import make_embed


class RolesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _role_from_key(self, guild: discord.Guild, key: str) -> discord.Role | None:
        role_id = self.bot.config.roles.get(key)
        return guild.get_role(role_id) if role_id else None

    @commands.hybrid_command(name="tester", description="Assign the Tester role")
    async def tester(self, context: commands.Context) -> None:
        role = self._role_from_key(context.guild, "tester") if context.guild else None
        if role is None:
            await context.reply("Tester role is not configured.", mention_author=False)
            return
        await context.author.add_roles(role, reason="Tester self-assignment")
        embed = make_embed(title="Role Assigned", description=f"You now have the {role.name} role.", color=self.bot.config.theme_color)
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="dev", description="Assign the Developer role")
    @commands.has_permissions(manage_roles=True)
    async def dev(self, context: commands.Context) -> None:
        role = self._role_from_key(context.guild, "developer") if context.guild else None
        if role is None:
            await context.reply("Developer role is not configured.", mention_author=False)
            return
        await context.author.add_roles(role, reason="Developer role assignment")
        embed = make_embed(title="Role Assigned", description=f"You now have the {role.name} role.", color=self.bot.config.theme_color)
        await context.reply(embed=embed, mention_author=False)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        await self._handle_reaction_role(payload, add=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        await self._handle_reaction_role(payload, add=False)

    async def _handle_reaction_role(self, payload: discord.RawReactionActionEvent, add: bool) -> None:
        reaction_roles = self.bot.config.reaction_roles
        if not reaction_roles:
            return
        message_roles = reaction_roles.get(str(payload.message_id))
        if not isinstance(message_roles, dict):
            return
        role_id = message_roles.get(str(payload.emoji))
        if not role_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.NotFound:
                return
        if member is None:
            return
        role = guild.get_role(role_id)
        if role is None:
            return

        try:
            if add:
                await member.add_roles(role, reason="Reaction role added")
            else:
                await member.remove_roles(role, reason="Reaction role removed")
        except discord.Forbidden:
            self.bot.logger.warning("Unable to update reaction role for %s", member)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RolesCog(bot))
