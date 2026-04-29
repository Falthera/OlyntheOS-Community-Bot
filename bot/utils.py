from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

import discord


def make_embed(title: str, description: str, color: int, footer: str = "OlyntheOS Community Bot") -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(timezone.utc))
    embed.set_footer(text=footer, icon_url="https://cdn-icons-png.flaticon.com/512/906/906343.png")
    return embed


def chunk_lines(items: Iterable[str], max_chars: int = 900) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for item in items:
        item_len = len(item) + 1
        if current and current_len + item_len > max_chars:
            chunks.append("\n".join(current))
            current = [item]
            current_len = len(item)
        else:
            current.append(item)
            current_len += item_len
    if current:
        chunks.append("\n".join(current))
    return chunks


def mention_channel(channel_id: int | None) -> str:
    return f"<#{channel_id}>" if channel_id else "configured channel"
