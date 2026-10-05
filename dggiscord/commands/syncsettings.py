from helpers.log import logging
from helpers.database import store
import discord.client as client
from commands.sync import user_is_privledge

logger = logging.getLogger(__name__)
logger.info("loading...")


@client.bot.command(name="sync-settings", aliases=["syncsettings"])
async def sync_settings(ctx, action=None, setting=None):
    """
    Manage sync settings for this server.

    Usage:
        !sync-settings                     - Show current settings
        !sync-settings enable subscription - Enable subscription sync
        !sync-settings enable username     - Enable username sync
        !sync-settings enable all          - Enable both syncs
        !sync-settings disable subscription - Disable subscription sync
        !sync-settings disable username     - Disable username sync
        !sync-settings disable all          - Disable both syncs
    """
    # only let privileged users manage settings
    if not user_is_privledge(ctx):
        return

    if ctx.message.guild is None:
        await ctx.reply("This command can only be used in a server.")
        return

    guild_id = ctx.message.guild.id

    if action is None:
        settings = store.sync_settings(guild_id)
        sub_status = "enabled" if settings["sync_subscription"] else "disabled"
        user_status = "enabled" if settings["sync_username"] else "disabled"

        await ctx.reply(
            f"**Sync Settings for this server:**\n"
            f"• Subscription sync: **{sub_status}**\n"
            f"• Username sync: **{user_status}**"
        )
        return

    action = action.lower()

    if action not in ("enable", "disable"):
        await ctx.reply(
            "**Usage:**\n"
            "• `!sync-settings` - Show current settings\n"
            "• `!sync-settings enable <subscription|username|all>`\n"
            "• `!sync-settings disable <subscription|username|all>`"
        )
        return

    if setting is None:
        await ctx.reply(f"Please specify what to {action}: `subscription`, `username`, or `all`")
        return

    setting = setting.lower()

    labels = {
        "subscription": ("**Subscription sync** has", ("sync_subscription",)),
        "username": ("**Username sync** has", ("sync_username",)),
        "all": ("**Subscription and username sync** have", ("sync_subscription", "sync_username")),
    }
    if setting not in labels:
        await ctx.reply("Invalid setting. Use `subscription`, `username`, or `all`.")
        return

    label, columns = labels[setting]
    enabled = action == "enable"
    store.set_sync_settings(guild_id, **{column: enabled for column in columns})
    logger.info(f'sync-settings: {setting} sync {action}d for server {guild_id}')
    await ctx.reply(f"{label} been **{action}d** for this server.")
