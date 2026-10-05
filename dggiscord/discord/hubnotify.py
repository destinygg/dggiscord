from helpers.config import cfg
from helpers.log import logging
from helpers.database import con
from helpers.http import get_json
from hub.notifier import HubNotifier, load_settings
import discord.client as client

logger = logging.getLogger(__name__)
logger.info("loading...")

settings = load_settings(cfg)


def get_channel(channel_id):
    channel = client.bot.get_channel(channel_id)
    if channel is None:
        raise LookupError(f"channel {channel_id} not found")
    return channel


async def send_to_channel(channel_id, content, embed):
    message = await get_channel(channel_id).send(content=content, embed=embed)
    return message.id


async def edit_message(channel_id, message_id, content, embed):
    await get_channel(channel_id).get_partial_message(message_id).edit(content=content, embed=embed)


notifier = HubNotifier(con, get_json, send_to_channel, edit_message, settings)


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
