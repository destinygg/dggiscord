from helpers.config import cfg
from helpers.log import logging
from helpers.database import cur
from subsync.sync import update_member, update_member_username, flair_map, role_map, get_all_members_indexed
from subsync.translator import flairs_to_roles
import discord.client as client
import time

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


@client.tasks.loop(seconds=cfg['discord']['background_refresh_rate']*60)
async def background_update_roles():
    await client.bot.wait_until_ready()
    logger.info("background_update_roles() starting background sync")
    start = time.time()

    dgg_subscriber_index = await get_all_members_indexed()

    for guild in client.bot.guilds:
        settings = get_sync_settings(guild.id)

        # Check if any sync is enabled for this guild
        if not settings["sync_subscription"] and not settings["sync_username"]:
            logger.debug(f'background sync skipped for {guild.id} ({guild.name}) - disabled')
            continue

        logger.info(f'background sync running on {guild.id} ({guild.name}) - sub:{settings["sync_subscription"]} user:{settings["sync_username"]}')

        # refresh the roles if subscription sync is enabled
        if settings["sync_subscription"]:
            await flairs_to_roles(guild)

        # build the maps once per server to reduce compute and db hit times
        fmap = flair_map(guild)
        rmap = role_map(guild)

        for member in guild.members:
            # Sync subscription roles if enabled
            if settings["sync_subscription"]:
                await update_member(member, fmap, rmap, dgg_subscriber_index)

            # Sync username if enabled
            if settings["sync_username"]:
                await update_member_username(member, dgg_subscriber_index)

    exec_time = int(time.time() - start)
    logger.info("background_update_roles() background sync completed. Took {} seconds".format(exec_time))

background_update_roles.start()
