from __future__ import annotations

import logging
import os
from typing import Any

import aiohttp
import discord
from discord.ext import commands, tasks

from bot.utils import make_embed


class GitHubCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None
        self.logger = logging.getLogger("luminos.github")
        self.repo_missing_reported = False

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession(headers={"Accept": "application/vnd.github+json"})
        interval = int(self.bot.config.github.get("poll_interval_minutes", 5))
        self.poll_github.change_interval(minutes=interval)
        self.poll_github.start()

    async def cog_unload(self) -> None:
        self.poll_github.cancel()
        if self.session is not None:
            await self.session.close()

    @tasks.loop(minutes=5)
    async def poll_github(self) -> None:
        config = self.bot.config
        repo = config.github_repo
        if not repo or self.session is None:
            return

        url = config.github_api_url
        headers: dict[str, str] = {}
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with self.session.get(url, headers=headers, timeout=20) as response:
            if response.status != 200:
                if response.status == 404:
                    if not self.repo_missing_reported:
                        self.logger.warning("GitHub repo not found at %s. Check repo_owner/repo_name in config.json", url)
                        self.repo_missing_reported = True
                else:
                    self.logger.warning("GitHub API returned %s", response.status)
                return
            events: list[dict[str, Any]] = await response.json()

        self.repo_missing_reported = False

        if not events:
            return

        if self.bot.last_github_event_id is None:
            self.bot.last_github_event_id = events[0].get("id")
            return

        channel_id = config.channels.get("github_updates")
        channel = self.bot.get_channel(channel_id) if channel_id else None
        if not isinstance(channel, discord.TextChannel):
            return

        last_event_id = self.bot.last_github_event_id
        new_events = []
        for event in events:
            if event.get("id") == last_event_id:
                break
            new_events.append(event)

        if events:
            self.bot.last_github_event_id = events[0].get("id")

        for event in reversed(new_events):
            await self._dispatch_event(channel, event)

    @poll_github.before_loop
    async def before_poll_github(self) -> None:
        await self.bot.wait_until_ready()

    @poll_github.error
    async def poll_github_error(self, error: Exception) -> None:
        self.logger.error("GitHub polling failed", exc_info=(type(error), error, error.__traceback__))

    async def _dispatch_event(self, channel: discord.TextChannel, event: dict[str, Any]) -> None:
        config = self.bot.config
        event_type = event.get("type")
        payload = event.get("payload", {})
        actor = event.get("actor", {}).get("login", "someone")

        if event_type == "PushEvent":
            commit_count = len(payload.get("commits", []))
            branch = event.get("repo", {}).get("name", config.github_repo)
            embed = make_embed(
                title="New Commit Push",
                description=f"{actor} pushed {commit_count} commit(s) to {branch}.",
                color=config.theme_color,
            )
            await channel.send(embed=embed)
        elif event_type == "ReleaseEvent" and payload.get("action") == "published":
            release = payload.get("release", {})
            embed = make_embed(
                title="New Release Published",
                description=release.get("name") or release.get("tag_name") or "A new release was published.",
                color=config.theme_color,
            )
            await channel.send(embed=embed)
        elif event_type == "IssuesEvent":
            issue = payload.get("issue", {})
            action = payload.get("action", "updated")
            embed = make_embed(
                title=f"Issue {action.title()}",
                description=issue.get("title", "Issue update"),
                color=config.theme_color,
            )
            await channel.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    cog = GitHubCog(bot)
    await bot.add_cog(cog)
