from helpers.config import cfg
from helpers.log import logging
from subsync.sync import update_member, flair_map, role_map, get_all_members_indexed
from subsync.translator import flairs_to_roles
import discord.client as client
import time

logger = logging.getLogger(__name__)
logger.info("loading...")

@client.tasks.loop(seconds=cfg['discord']['background_refresh_rate']*60)
async def background_update_roles():
    await client.bot.wait_until_ready()
    logger.info("background_update_roles() starting background role <=> flair sync")
    start = time.time()

    dgg_subscriber_index = await get_all_members_indexed()

    for guild in client.bot.guilds:
        # refresh the roles
        await flairs_to_roles(guild)

        logger.info(f'background role <=> flair sync running on {guild.id} ({guild.name})')


        # build the maps once per server to reduce compute and db hit times
        fmap = flair_map(guild)
        rmap = role_map(guild)

        for member in guild.members:
            await update_member(member, fmap, rmap, dgg_subscriber_index)

    exec_time = int(time.time() - start)
    logger.info("background_update_roles() background role <=> flair sync completed. Took {} seconds".format(exec_time))

background_update_roles.start()
