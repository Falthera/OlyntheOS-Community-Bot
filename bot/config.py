from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import os


@dataclass(slots=True)
class ProjectRoadmapItem:
    phase: str
    description: str


@dataclass(slots=True)
class BotConfig:
    bot_prefix: str = "!"
    theme_color: int = 0x00C2FF
    guild_id: int = 0
    owner_ids: list[int] = field(default_factory=list)
    channels: dict[str, int] = field(default_factory=dict)
    roles: dict[str, int] = field(default_factory=dict)
    links: dict[str, str] = field(default_factory=dict)
    project: dict[str, Any] = field(default_factory=dict)
    status: dict[str, str] = field(default_factory=dict)
    github: dict[str, Any] = field(default_factory=dict)
    starboard: dict[str, Any] = field(default_factory=dict)
    tickets: dict[str, Any] = field(default_factory=dict)
    anti_spam: dict[str, int] = field(default_factory=dict)
    welcome: dict[str, Any] = field(default_factory=dict)
    logging: dict[str, Any] = field(default_factory=dict)
    reaction_roles: dict[str, dict[str, int]] = field(default_factory=dict)
    warning_cases: list[dict[str, Any]] = field(default_factory=list)

    @property
    def github_repo(self) -> str:
        owner = self.github.get("repo_owner", "")
        name = self.github.get("repo_name", "")
        return f"{owner}/{name}".strip("/")

    @property
    def github_api_url(self) -> str:
        return f"https://api.github.com/repos/{self.github_repo}/events"

    @property
    def roadmap(self) -> list[ProjectRoadmapItem]:
        return [ProjectRoadmapItem(**item) for item in self.project.get("roadmap", [])]

    @property
    def features(self) -> list[str]:
        return list(self.project.get("features", []))

    @property
    def project_name(self) -> str:
        return self.project.get("name", "Project")

    @property
    def tagline(self) -> str:
        return self.project.get("tagline", "")

    @property
    def vision(self) -> str:
        return self.project.get("vision", "")

    @property
    def current_build_status(self) -> str:
        return self.status.get("current_build_status", "Status unavailable")

    @property
    def latest_version(self) -> str:
        return self.status.get("latest_version", "Unknown")

    @property
    def build_notes(self) -> str:
        return self.status.get("build_notes", "No build notes available.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "bot_prefix": self.bot_prefix,
            "theme_color": self.theme_color,
            "guild_id": self.guild_id,
            "owner_ids": self.owner_ids,
            "channels": self.channels,
            "roles": self.roles,
            "links": self.links,
            "project": self.project,
            "status": self.status,
            "github": self.github,
            "starboard": self.starboard,
            "tickets": self.tickets,
            "anti_spam": self.anti_spam,
            "welcome": self.welcome,
            "logging": self.logging,
            "reaction_roles": self.reaction_roles,
            "warning_cases": self.warning_cases,
        }


class ConfigError(RuntimeError):
    pass


def load_config(config_path: str | os.PathLike[str] = "config.json") -> BotConfig:
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(
            f"Missing config file: {path}. Copy config.example.json to config.json and fill in your values."
        )

    with path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    return BotConfig(
        bot_prefix=raw.get("bot_prefix", "!"),
        theme_color=raw.get("theme_color", 0x00C2FF),
        guild_id=raw.get("guild_id", 0),
        owner_ids=raw.get("owner_ids", []),
        channels=raw.get("channels", {}),
        roles=raw.get("roles", {}),
        links=raw.get("links", {}),
        project=raw.get("project", {}),
        status=raw.get("status", {}),
        github=raw.get("github", {}),
        starboard=raw.get("starboard", {}),
        tickets=raw.get("tickets", {}),
        anti_spam=raw.get("anti_spam", {}),
        welcome=raw.get("welcome", {}),
        logging=raw.get("logging", {}),
        reaction_roles=raw.get("reaction_roles", {}),
        warning_cases=raw.get("warning_cases", []),
    )


def save_config(config: BotConfig, config_path: str | os.PathLike[str] = "config.json") -> None:
    path = Path(config_path)
    with path.open("w", encoding="utf-8") as file:
        json.dump(config.to_dict(), file, indent=2, ensure_ascii=False)
        file.write("\n")
