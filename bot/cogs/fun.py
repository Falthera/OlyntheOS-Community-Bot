from __future__ import annotations

import random

import discord
from discord.ext import commands

from bot.utils import make_embed


LINUX_TIPS = [
    "Use `journalctl -xe` to inspect recent service errors quickly.",
    "Use `rg` (ripgrep) for lightning-fast text searches across code and configs.",
    "Use `df -h` and `du -sh *` together to find where disk space went.",
    "Use `systemctl --failed` to spot broken services after boot.",
    "Use `ssh -J jumpbox target` to connect through a bastion host cleanly.",
    "Use `watch -n 1` for live-updating terminal output when debugging.",
]

OPEN_SOURCE_FACTS = [
    "The Linux kernel is one of the largest collaborative software projects ever maintained.",
    "Open source communities often rely on small, well-scoped contributions to keep momentum sustainable.",
    "A good issue report is often as valuable as a small code patch because it saves maintainer time.",
    "Many successful projects use a public roadmap to turn community feedback into visible progress.",
]

SHELL_SNIPPETS: dict[str, dict[str, str]] = {
    "logs": {
        "title": "Log Triage",
        "why": "Inspect recent logs for a service or boot session.",
        "snippet": "journalctl -xeu <service-name>",
        "extra": "Swap <service-name> for the systemd unit you want to inspect.",
    },
    "network": {
        "title": "Network Snapshot",
        "why": "Show IPs, routes, and interface state quickly.",
        "snippet": "ip a && ip route && nmcli dev status",
        "extra": "Great when you need a one-line connectivity sanity check.",
    },
    "storage": {
        "title": "Storage Audit",
        "why": "Find large folders and summarize disk usage.",
        "snippet": "du -xh /home | sort -h | tail -n 20",
        "extra": "Useful before packaging an ISO or cleaning a workstation.",
    },
    "git": {
        "title": "Git Rescue",
        "why": "Recover work or inspect recent history.",
        "snippet": "git status && git log --oneline --decorate -n 10",
        "extra": "Pair with `git stash` when you need to protect WIP quickly.",
    },
    "permissions": {
        "title": "Permission Fix",
        "why": "Normalize file ownership and modes for a local project tree.",
        "snippet": "sudo chown -R $USER:$USER . && chmod -R u+rwX,go+rX .",
        "extra": "Be careful with recursive permission changes on shared systems.",
    },
    "systemd": {
        "title": "Service Health",
        "why": "Check whether a service is active and why it failed.",
        "snippet": "systemctl status <service-name> && journalctl -u <service-name> -b",
        "extra": "Use this when a daemon seems to start but not behave correctly.",
    },
}

ALIASES = [
    {"name": "..", "value": "cd ..", "desc": "Step up one directory."},
    {"name": "ll", "value": "ls -lah", "desc": "List files with sizes and hidden entries."},
    {"name": "gs", "value": "git status --short", "desc": "Show a compact git status."},
    {"name": "ports", "value": "ss -tulpn", "desc": "See what ports are listening."},
]

JOKES = [
    "Why do Linux users make good detectives? They always follow the logs.",
    "Why did the developer love KDE? Because the panel never ghosted them.",
    "Why was the ISO calm under pressure? Because it had good mount support.",
    "Why do shell users never panic? They know every problem can be piped somewhere useful.",
]

MEME_LINES = [
    "I use Arch, by the way… just kidding, I use whatever boots on the first try.",
    "When the repo builds on the first try, that’s not luck — that’s a rare celestial event.",
    "The package manager said no. The maintainer said maybe. The community said patch it.",
    "Me: 'This will be a quick fix.' Also me: three hours deep into systemd logs.",
]

QUOTES = [
    "Ship small things, ship often, and let the community steer the map.",
    "A good distro is built from good defaults, clear docs, and careful tradeoffs.",
    "Open source grows best when contributors can see their impact quickly.",
    "Local-first tools make privacy feel practical instead of theoretical.",
]

CHALLENGES = [
    "Find one service on your system and inspect its logs with `journalctl -u <service> -b`.",
    "Use `rg` to find a string in your config directory without opening a GUI editor.",
    "Check your disk usage and identify the top 3 biggest directories in your home folder.",
    "Share one Linux command in chat that saves you time every week.",
]

BADGES = [
    {"name": "Log Detective", "desc": "Awarded to anyone who knows how to tame a noisy systemd journal."},
    {"name": "Patch Pioneer", "desc": "Awarded to contributors who ship small, consistent improvements."},
    {"name": "ISO Trailblazer", "desc": "Awarded to anyone who helps improve the build pipeline or installer flow."},
    {"name": "Kernel Curious", "desc": "Awarded to people who ask smart questions about how Linux works under the hood."},
]

DEVLOG_ENTRIES = [
    "ISO builder rewrite is progressing toward a concurrent Go + Bubble Tea workflow.",
    "Local AI packaging and Calamares customization are active focus areas.",
    "Community workflows, Discord roles, and launch prep are being tightened up.",
    "Roadmap alignment is centered on privacy-first defaults and ethical local AI.",
]


class FunCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Show bot latency in milliseconds")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ping(self, context: commands.Context) -> None:
        latency_ms = round(self.bot.latency * 1000)
        embed = make_embed(
            title="Pong!",
            description=f"Latency: **{latency_ms} ms**",
            color=self.bot.config.theme_color,
        )
        embed.add_field(name="Hint", value="If the bot is mentioned directly, it can reply with a greeting too.", inline=False)
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="tip", description="Show a random Linux productivity tip")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def tip(self, context: commands.Context) -> None:
        tip = random.choice(LINUX_TIPS)
        embed = make_embed(
            title="Linux Tip",
            description=tip,
            color=self.bot.config.theme_color,
        )
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="snippet", description="Show a Linux shell snippet by topic")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def snippet(self, context: commands.Context, topic: str | None = None) -> None:
        chosen_topic = (topic or random.choice(list(SHELL_SNIPPETS.keys()))).lower()
        data = SHELL_SNIPPETS.get(chosen_topic)
        if data is None:
            available = ", ".join(sorted(SHELL_SNIPPETS))
            await context.reply(f"Unknown topic. Try one of: {available}", mention_author=False)
            return

        embed = make_embed(
            title=data["title"],
            description=data["why"],
            color=self.bot.config.theme_color,
        )
        embed.add_field(name="Snippet", value=f"```bash\n{data['snippet']}\n```", inline=False)
        embed.add_field(name="Extra", value=data["extra"], inline=False)
        embed.set_footer(text=f"Topic: {chosen_topic}")
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="fact", description="Show a random open-source fact")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def fact(self, context: commands.Context) -> None:
        fact = random.choice(OPEN_SOURCE_FACTS)
        embed = make_embed(
            title="Open Source Fact",
            description=fact,
            color=self.bot.config.theme_color,
        )
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="alias", description="Show a useful terminal alias")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def alias(self, context: commands.Context) -> None:
        alias_info = random.choice(ALIASES)
        embed = make_embed(
            title=f"Alias: {alias_info['name']}",
            description=alias_info["desc"],
            color=self.bot.config.theme_color,
        )
        embed.add_field(name="Definition", value=f"```bash\nalias {alias_info['name']}='{alias_info['value']}'\n```", inline=False)
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="idea", description="Show a fun community project idea")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def idea(self, context: commands.Context) -> None:
        ideas = [
            "Create a weekly 'fix one bug' community event to help new contributors land their first patch.",
            "Host a 'terminal trick of the week' channel where members share their best Linux shortcuts.",
            "Run ISO build sprints with small visible milestones so contributors can see progress fast.",
            "Publish a public 'community wishlist' and let members vote on the next polish target.",
        ]
        embed = make_embed(
            title="Community Idea",
            description=random.choice(ideas),
            color=self.bot.config.theme_color,
        )
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="joke", description="Tell a Linux/open-source joke")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def joke(self, context: commands.Context) -> None:
        embed = make_embed(
            title="Linux Joke",
            description=random.choice(JOKES),
            color=self.bot.config.theme_color,
        )
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="meme", description="Show a lightweight Linux meme line")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def meme(self, context: commands.Context) -> None:
        embed = make_embed(
            title="Linux Meme",
            description=random.choice(MEME_LINES),
            color=self.bot.config.theme_color,
        )
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="morning", description="Send a friendly good morning message")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def morning(self, context: commands.Context) -> None:
        embed = make_embed(
            title="Good Morning",
            description=f"Good morning, {context.author.mention} ☀️ Have a smooth build day.",
            color=self.bot.config.theme_color,
        )
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="night", description="Send a friendly good night message")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def night(self, context: commands.Context) -> None:
        embed = make_embed(
            title="Good Night",
            description=f"Good night, {context.author.mention} 🌙 Time to rest and let the logs sleep too.",
            color=self.bot.config.theme_color,
        )
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="quote", description="Show a community or open-source quote")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def quote(self, context: commands.Context) -> None:
        embed = make_embed(
            title="Community Quote",
            description=random.choice(QUOTES),
            color=self.bot.config.theme_color,
        )
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="challenge", description="Show a Linux/community challenge")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def challenge(self, context: commands.Context) -> None:
        embed = make_embed(
            title="Terminal Challenge",
            description=random.choice(CHALLENGES),
            color=self.bot.config.theme_color,
        )
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="poll", description="Create a small community poll")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def poll(self, context: commands.Context, *, question: str) -> None:
        embed = make_embed(
            title="Community Poll",
            description=question,
            color=self.bot.config.theme_color,
        )
        embed.set_footer(text=f"Poll started by {context.author.display_name}")
        message = await context.reply(embed=embed, mention_author=False)
        try:
            await message.add_reaction("👍")
            await message.add_reaction("👎")
        except discord.Forbidden:
            pass

    @commands.hybrid_command(name="statuscheck", description="Get a playful server health response")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def statuscheck(self, context: commands.Context) -> None:
        responses = [
            "All systems nominal — vibes are stable and logs are quiet.",
            "Status: currently compiling good ideas into better ones.",
            "Healthy enough to ship, curious enough to improve.",
            "Running smooth, but I still recommend checking the logs anyway.",
        ]
        embed = make_embed(
            title="Status Check",
            description=random.choice(responses),
            color=self.bot.config.theme_color,
        )
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="devlog", description="Show a short project development update")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def devlog(self, context: commands.Context) -> None:
        embed = make_embed(
            title="Project Devlog",
            description=random.choice(DEVLOG_ENTRIES),
            color=self.bot.config.theme_color,
        )
        embed.add_field(name="Current Build Notes", value=self.bot.config.build_notes, inline=False)
        embed.add_field(name="Latest Version", value=self.bot.config.latest_version, inline=True)
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="buildday", description="Show a build-of-the-day highlight")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def buildday(self, context: commands.Context) -> None:
        highlights = [
            "Today's build focus: stabilizing the installer and keeping the desktop polished.",
            "Today's build focus: tightening up local AI packaging and testing startup flows.",
            "Today's build focus: stress-testing core tools and watching for regressions.",
            "Today's build focus: improving the community pipeline from feedback to merge.",
        ]
        embed = make_embed(
            title="Build of the Day",
            description=random.choice(highlights),
            color=self.bot.config.theme_color,
        )
        await context.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="badge", description="Assign a fun community badge")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def badge(self, context: commands.Context) -> None:
        badge = random.choice(BADGES)
        embed = make_embed(
            title=f"Badge Earned: {badge['name']}",
            description=badge["desc"],
            color=self.bot.config.theme_color,
        )
        embed.set_footer(text=f"Congrats, {context.author.display_name}!")
        await context.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FunCog(bot))