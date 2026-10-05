import logging

import disnake
from disnake.ext import commands

from commands.sync import deny_unprivileged

logger = logging.getLogger(__name__)
logger.info("loading...")

GUILD_ONLY = disnake.InteractionContextTypes(guild=True)

# setting choice -> (reply label, sync_settings columns it changes)
SETTINGS = {
    "subscription": ("**Subscription sync** has", ("sync_subscription",)),
    "username": ("**Username sync** has", ("sync_username",)),
    "all": ("**Subscription and username sync** have", ("sync_subscription", "sync_username")),
}


class SyncSettings(commands.Cog):
    def __init__(self, store, admins):
        """
        Args:
            store: helpers.store.Store
            admins: user IDs of the bot's owners, who can run privileged commands anywhere
        """
        self.store = store
        self.admins = admins

    @commands.slash_command(name="sync-settings", contexts=GUILD_ONLY)
    async def sync_settings(
        self,
        inter,
        action: str = commands.Param(None, choices=["enable", "disable"], description="Turn a sync on or off; leave out to show the current settings"),
        setting: str = commands.Param(None, choices=list(SETTINGS), description="Which sync to change"),
    ):
        """View or change this server's sync settings."""
        # only let privileged users manage settings
        if await deny_unprivileged(inter, self.admins):
            return

        guild_id = inter.guild.id

        if action is None:
            settings = self.store.sync_settings(guild_id)
            sub_status = "enabled" if settings["sync_subscription"] else "disabled"
            user_status = "enabled" if settings["sync_username"] else "disabled"

            await inter.send(
                f"**Sync Settings for this server:**\n"
                f"• Subscription sync: **{sub_status}**\n"
                f"• Username sync: **{user_status}**"
            )
            return

        if setting is None:
            await inter.send(f"Please specify what to {action}: `subscription`, `username`, or `all`", ephemeral=True)
            return

        label, columns = SETTINGS[setting]
        enabled = action == "enable"
        self.store.set_sync_settings(guild_id, **{column: enabled for column in columns})
        logger.info(f'sync-settings: {setting} sync {action}d for server {guild_id}')
        await inter.send(f"{label} been **{action}d** for this server.")
