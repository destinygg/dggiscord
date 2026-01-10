from helpers.log import logging
from helpers.database import con, cur
import discord.client as client
from commands.sync import user_is_privledge

logger = logging.getLogger(__name__)
logger.info("loading...")


def get_sync_settings(guild_id):
    """Get sync settings for a guild. Returns dict with sync_subscription and sync_username."""
    cur.execute("SELECT sync_subscription, sync_username FROM syncsettings WHERE discord_server=?", (guild_id,))
    row = cur.fetchone()
    if row is None:
        return {"sync_subscription": False, "sync_username": False}
    return {"sync_subscription": bool(row[0]), "sync_username": bool(row[1])}


def is_any_sync_enabled(guild_id):
    """Check if any sync option is enabled for a guild."""
    settings = get_sync_settings(guild_id)
    return settings["sync_subscription"] or settings["sync_username"]


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
        settings = get_sync_settings(guild_id)
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

    if action == "enable":
        if setting == "subscription":
            cur.execute("""
                INSERT INTO syncsettings (discord_server, sync_subscription, sync_username)
                VALUES (?, 1, 0)
                ON CONFLICT(discord_server) DO UPDATE SET sync_subscription = 1
            """, (guild_id,))
            con.commit()
            logger.info(f'sync-settings: subscription sync enabled for server {guild_id}')
            await ctx.reply("**Subscription sync** has been **enabled** for this server.")
        elif setting == "username":
            cur.execute("""
                INSERT INTO syncsettings (discord_server, sync_subscription, sync_username)
                VALUES (?, 0, 1)
                ON CONFLICT(discord_server) DO UPDATE SET sync_username = 1
            """, (guild_id,))
            con.commit()
            logger.info(f'sync-settings: username sync enabled for server {guild_id}')
            await ctx.reply("**Username sync** has been **enabled** for this server.")
        elif setting == "all":
            cur.execute("""
                INSERT INTO syncsettings (discord_server, sync_subscription, sync_username)
                VALUES (?, 1, 1)
                ON CONFLICT(discord_server) DO UPDATE SET sync_subscription = 1, sync_username = 1
            """, (guild_id,))
            con.commit()
            logger.info(f'sync-settings: all sync enabled for server {guild_id}')
            await ctx.reply("**Subscription and username sync** have been **enabled** for this server.")
        else:
            await ctx.reply("Invalid setting. Use `subscription`, `username`, or `all`.")
    elif action == "disable":
        if setting == "subscription":
            cur.execute("""
                INSERT INTO syncsettings (discord_server, sync_subscription, sync_username)
                VALUES (?, 0, 0)
                ON CONFLICT(discord_server) DO UPDATE SET sync_subscription = 0
            """, (guild_id,))
            con.commit()
            logger.info(f'sync-settings: subscription sync disabled for server {guild_id}')
            await ctx.reply("**Subscription sync** has been **disabled** for this server.")
        elif setting == "username":
            cur.execute("""
                INSERT INTO syncsettings (discord_server, sync_subscription, sync_username)
                VALUES (?, 0, 0)
                ON CONFLICT(discord_server) DO UPDATE SET sync_username = 0
            """, (guild_id,))
            con.commit()
            logger.info(f'sync-settings: username sync disabled for server {guild_id}')
            await ctx.reply("**Username sync** has been **disabled** for this server.")
        elif setting == "all":
            cur.execute("""
                INSERT INTO syncsettings (discord_server, sync_subscription, sync_username)
                VALUES (?, 0, 0)
                ON CONFLICT(discord_server) DO UPDATE SET sync_subscription = 0, sync_username = 0
            """, (guild_id,))
            con.commit()
            logger.info(f'sync-settings: all sync disabled for server {guild_id}')
            await ctx.reply("**Subscription and username sync** have been **disabled** for this server.")
        else:
            await ctx.reply("Invalid setting. Use `subscription`, `username`, or `all`.")
