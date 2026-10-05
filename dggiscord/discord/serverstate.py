import logging

from disnake.ext import commands

logger = logging.getLogger(__name__)
logger.info("loading...")


class ServerState(commands.Cog):
    def __init__(self, translator):
        self.translator = translator

    # configure the cache, update the server members
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        logger.info("on_guild_join() NEW SERVER JOINED NAME:{0.name} ID:{0.id}".format(guild))

        # build the sqlite map
        await self.translator.flairs_to_roles(guild)
