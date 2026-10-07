import logging
import time

import disnake
from disnake.ext import commands

from hub.status import format_duration

logger = logging.getLogger(__name__)
logger.info("loading...")

ADMIN_ONLY = disnake.Permissions(administrator=True)
GUILD_ONLY = disnake.InteractionContextTypes(guild=True)


class Debug(commands.Cog):
    def __init__(self, admins, started_at, version):
        """
        Args:
            admins: Discord IDs of the bot owners
            started_at: unix time the bot was started
            version: the build's version, e.g. a release tag
        """
        self.admins = admins
        self.started_at = started_at
        self.version = version

    # default_member_permissions hides the command from most members, but only bot owners can run it
    @commands.slash_command(default_member_permissions=ADMIN_ONLY, contexts=GUILD_ONLY)
    async def debug(self, inter):
        """Show the bot's version and uptime."""
        if inter.author.id not in self.admins:
            await inter.send("Error: Only the bot owner can use this command.", ephemeral=True)
            return

        uptime = format_duration(time.time() - self.started_at)
        await inter.send(
            f"Version: `{self.version}`\nUptime: {uptime} (started <t:{int(self.started_at)}:f>)",
            ephemeral=True,
        )
