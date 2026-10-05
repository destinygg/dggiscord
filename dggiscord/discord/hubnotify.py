from helpers.config import cfg
from helpers.log import logging
from helpers.database import con
from helpers.http import get_json
from hub.notifier import HubNotifier, load_settings
import discord.client as client

logger = logging.getLogger(__name__)
logger.info("loading...")

settings = load_settings(cfg)


async def send_to_channel(channel_id, content, embed):
    channel = client.bot.get_channel(channel_id)
    if channel is None:
        raise LookupError(f"channel {channel_id} not found")
    await channel.send(content=content, embed=embed)


notifier = HubNotifier(con, get_json, send_to_channel, settings)


@client.tasks.loop(seconds=settings['poll_interval'])
async def hub_notify():
    try:
        await notifier.poll()
    except Exception as e:
        logger.error(f"hub_notify() poll failed: {e}")


@hub_notify.before_loop
async def before_hub_notify():
    await client.bot.wait_until_ready()


hub_notify.start()
