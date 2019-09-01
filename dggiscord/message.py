from config import cfg
from log import logging
import client

logger = logging.getLogger(__name__)
logger.info("loading...")

@client.bot.event
async def on_message(message):

    logging.debug(message.contents)

    await client.bot.process_commands(message)
