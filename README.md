# LuminOS Discord Bot

A modular, production-ready Discord bot for the LuminOS community, a Debian 13.4 + KDE Plasma distribution with local AI at its core.

## Features

- Project info commands: `!about`, `!roadmap`, `!github`, `!website`
- Status commands: `!status`, `!version`, `!build`
- Interactive bug reports
- Welcome/onboarding automation
- Role self-assignment and optional reaction roles
- Discord admin panel for editing project settings, links, IDs, and syncing commands
- Moderation commands: `!warn`, `!cases`, `!warnings`, `!clearwarnings`, `!mute`, `!kick`, `!purge`, `!lock`, `!unlock`, `!slowmode`
- Ticket features: `!ticket`, `!ticketpanel`, `!ticketclose`, `!ticketclaim`, `!ticketadd`, `!ticketremove`, `!ticketrename`
- Linux fun/snippets commands: `!tip`, `!snippet`, `!fact`, `!alias`, `!idea`
- Ping command with latency display and friendly mention/greeting replies
- More fun replies: `!joke`, `!meme`, `!morning`, `!night`
- Community extras: `!quote`, `!challenge`, `!poll`, `!statuscheck`
- Project/community extras: `!devlog`, `!buildday`, `!badge`
- Starboard reactions for highlighting community posts
- Anti-spam protection
- Command, moderation, and error logging
- GitHub activity polling for commits, releases, and issues
- Hybrid commands for both prefix and slash usage

## Folder Structure

- `main.py` — entrypoint
- `bot/bot.py` — Discord client, global event handling, and startup
- `bot/config.py` — JSON config loading and typed config helpers
- `bot/views.py` — interactive buttons and modals
- `bot/cogs/` — modular extensions for each feature area
- `config.example.json` — sample configuration
- `.env` — local environment variables, including the Discord token
- `requirements.txt` — Python dependencies

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy the sample config file and create your local `.env` file:

   ```bash
   cp config.example.json config.json
   touch .env
   ```

4. Fill in:
   - `TOKEN` in `.env`
   - Channel IDs and role IDs in `config.json`
   - GitHub repository details and project links in `config.json`

5. Enable the Discord bot intents in the Discord Developer Portal:
   - Message Content Intent
   - Server Members Intent
   - Presence Intent optional

6. Run the bot:

   ```bash
   python main.py
   ```

## Notes

- The bot uses a blue/cyan embed theme by default.
- GitHub updates are read from the public GitHub Events API; a GitHub token is optional but recommended.
- Slash command support works through `hybrid_command`.
- Use `!admin` or `/admin` as an administrator, server owner, or configured project owner to open the control panel.
- The panel includes controls for project text, status, links, IDs, prefix/theme, welcome settings, anti-spam, GitHub polling, and logging.
- The panel also includes quick channel controls for purging messages, locking, unlocking, slowmode, posting the ticket panel, exporting ticket transcripts, and closing the current ticket.
- The panel also includes ticket settings so staff can configure the support category, logging channel, and support role.
- Starboard settings can be edited from the admin panel and configured in `config.json`.
- Warning cases are saved with case numbers, and staff can review them with `!cases @member`.
- The bug and feature flows use Discord modals for a clean interactive experience.
- Tickets now include a type picker for support, bug reports, feature requests, and general help, plus in-channel controls for claim, unclaim, transcript, and close.
- Tickets are created inside a configured category, logged to an optional ticket log channel, and can be claimed, renamed, or closed by staff.
- `PyNaCl` is included so discord.py can load voice support cleanly, even though this bot does not use voice features.
