from helpers.config import cfg
from helpers.log import logging
from subsync.translator import flairs_to_roles
from subsync.sync import update_member, flair_map, role_map
import discord.client as client

logger = logging.getLogger(__name__)
logger.info("loading...")

# configure the cache, update the server members
@client.bot.event
async def on_guild_join(guild):
    logger.info("on_guild_join() NEW SERVER JOINED NAME:{0.name} ID:{0.id}".format(guild))

    # build the sqlite map
    await flairs_to_roles(guild)

    # build the maps once per server to reduce compute and db hit times
    fmap = flair_map(guild)
    rmap = role_map(guild)

    for member in guild.members:
        await update_member(member, fmap, rmap)
