from helpers.config import cfg
from helpers.log import logging
import discord.client as client

logger = logging.getLogger(__name__)
logger.info("loading...")

@client.bot.command()
async def live(ctx):
    pass