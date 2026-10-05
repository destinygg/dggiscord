from helpers.config import cfg
from helpers.log import logging
from helpers.database import store
from subsync.sync import update_member, update_member_username, flair_map, role_map, get_all_members_indexed
from subsync.translator import flairs_to_roles
import discord.client as client
import time

logger = logging.getLogger(__name__)
logger.info("loading...")


@client.tasks.loop(seconds=cfg['discord']['background_refresh_rate']*60)
async def background_update_roles():
    await client.bot.wait_until_ready()
    logger.info("background_update_roles() starting background sync")
    start = time.time()

    dgg_subscriber_index = await get_all_members_indexed()
    if dgg_subscriber_index is None:
        # without the index, update_member() would query the API once per member
        logger.error("background_update_roles() skipping this pass, unable to get the member index")
        return

    for guild in client.bot.guilds:
        settings = store.sync_settings(guild.id)

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
