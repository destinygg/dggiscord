import logging

import disnake as discord
from disnake.ext import commands, tasks

logger = logging.getLogger(__name__)
logger.info("loading...")


def create_bot():
    intents = discord.Intents.default()
    intents.members = True

    return commands.InteractionBot(intents=intents)


class Presence(commands.Cog):
    """Logs the login and rotates the bot's activity through the configured statuses."""

    def __init__(self, bot, nowplaying):
        self.bot = bot
        self.nowplaying = nowplaying
        self.nowplaying_next = 0

    async def cog_load(self):
        self.refresh_now_playing.start()

    def cog_unload(self):
        self.refresh_now_playing.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("Logged in as {0.user.name} ID:{0.user.id}".format(self.bot))

    # change it up every 60 * x mins
    @tasks.loop(seconds=3600)
    async def refresh_now_playing(self):
        nowplaying_length = len(self.nowplaying)

        # reset back to the first if our nowplaying_next is larger than the list
        if self.nowplaying_next >= nowplaying_length:
            self.nowplaying_next = 0

        nowplaying_name = self.nowplaying[self.nowplaying_next]

        logger.info(
            "Setting Discord Game presence to {0} ({1}/{2})".format(
                nowplaying_name, self.nowplaying_next, nowplaying_length
            )
        )
        await self.bot.change_presence(activity=discord.Game(nowplaying_name))

        self.nowplaying_next += 1

    @refresh_now_playing.before_loop
    async def before_refresh_now_playing(self):
        await self.bot.wait_until_ready()
