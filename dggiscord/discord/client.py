from helpers.config import cfg
import logging
import disnake as discord
import asyncio
from disnake.ext import commands, tasks
from disnake import embeds

logger = logging.getLogger(__name__)
logger.info("loading...")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix=cfg["discord"]["prefix"],
    intents=intents
)


@bot.event
async def on_ready():
    logger.info("Logged in as {0.user.name} ID:{0.user.id}".format(bot))
    bot.remove_command("help")


# rotate through config list of now playing status
async def refresh_now_playing():
    nowplaying_next = 0
    await bot.wait_until_ready()
    while bot.is_ready():
        nowplaying_length = len(cfg["discord"]["nowplaying"])

        # reset back to the first if our nowplaying_next is larger than the list
        if nowplaying_next >= nowplaying_length:
            nowplaying_next = 0

        nowplaying_name = cfg["discord"]["nowplaying"][nowplaying_next]

        logger.info(
            "Setting Discord Game presence to {0} ({1}/{2})".format(
                nowplaying_name, nowplaying_next, nowplaying_length
            )
        )
        game = discord.Game(nowplaying_name)
        await bot.change_presence(activity=game)

        nowplaying_next += 1

        # change it up every 60 * x mins
        await asyncio.sleep(3600)


bot.loop.create_task(refresh_now_playing())
