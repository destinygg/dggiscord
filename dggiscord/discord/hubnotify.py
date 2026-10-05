import logging

from disnake.ext import commands, tasks

from hub.notifier import HubNotifier

logger = logging.getLogger(__name__)
logger.info("loading...")


class HubNotify(commands.Cog):
    """Runs the HubNotifier poll loop, posting through the bot."""

    def __init__(self, bot, con, fetch_json, settings):
        """
        Args:
            bot: the disnake Bot
            con: sqlite3 connection with the hub tables migrated
            fetch_json: async function(url) -> parsed JSON or None on failure
            settings: dict as returned by hub.notifier.load_settings()
        """
        self.bot = bot
        self.notifier = HubNotifier(con, fetch_json, self.send_to_channel, self.edit_message, settings)
        self.hub_notify.change_interval(seconds=settings['poll_interval'])

    async def cog_load(self):
        self.hub_notify.start()

    def cog_unload(self):
        self.hub_notify.cancel()

    def get_channel(self, channel_id):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            raise LookupError(f"channel {channel_id} not found")
        return channel

    async def send_to_channel(self, channel_id, content, embed):
        message = await self.get_channel(channel_id).send(content=content, embed=embed)
        return message.id

    async def edit_message(self, channel_id, message_id, content, embed):
        await self.get_channel(channel_id).get_partial_message(message_id).edit(content=content, embed=embed)

    @tasks.loop(seconds=60)
    async def hub_notify(self):
        try:
            await self.notifier.poll()
        except Exception as e:
            logger.error(f"hub_notify() poll failed: {e}")

    @hub_notify.before_loop
    async def before_hub_notify(self):
        await self.bot.wait_until_ready()
