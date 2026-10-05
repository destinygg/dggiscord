import logging
import time

from disnake.ext import commands, tasks

logger = logging.getLogger(__name__)
logger.info("loading...")


class BackgroundSync(commands.Cog):
    """Periodically syncs every member of every server with sync enabled."""

    def __init__(self, bot, store, member_sync, translator, refresh_minutes):
        """
        Args:
            bot: the disnake Bot
            store: helpers.store.Store
            member_sync: subsync.sync.MemberSync
            translator: subsync.translator.FlairTranslator
            refresh_minutes: minutes between syncs
        """
        self.bot = bot
        self.store = store
        self.member_sync = member_sync
        self.translator = translator
        self.background_update_roles.change_interval(minutes=refresh_minutes)

    async def cog_load(self):
        self.background_update_roles.start()

    def cog_unload(self):
        self.background_update_roles.cancel()

    @tasks.loop(minutes=240)
    async def background_update_roles(self):
        await self.sync_guilds(self.bot.guilds)

    @background_update_roles.before_loop
    async def before_background_update_roles(self):
        await self.bot.wait_until_ready()

    async def sync_guilds(self, guilds):
        logger.info("background_update_roles() starting background sync")
        start = time.time()

        dgg_subscriber_index = await self.member_sync.get_all_members_indexed()
        if dgg_subscriber_index is None:
            # without the index, update_member() would query the API once per member
            logger.error("background_update_roles() skipping this pass, unable to get the member index")
            return

        for guild in guilds:
            settings = self.store.sync_settings(guild.id)

            # Check if any sync is enabled for this guild
            if not settings["sync_subscription"] and not settings["sync_username"]:
                logger.debug(f'background sync skipped for {guild.id} ({guild.name}) - disabled')
                continue

            logger.info(f'background sync running on {guild.id} ({guild.name}) - sub:{settings["sync_subscription"]} user:{settings["sync_username"]}')

            # refresh the roles if subscription sync is enabled
            if settings["sync_subscription"]:
                await self.translator.flairs_to_roles(guild)

            # build the maps once per server to reduce compute and db hit times
            fmap = self.member_sync.flair_map(guild)
            rmap = self.member_sync.role_map(guild)

            for member in guild.members:
                # Sync subscription roles if enabled
                if settings["sync_subscription"]:
                    await self.member_sync.update_member(member, fmap, rmap, dgg_subscriber_index)

                # Sync username if enabled
                if settings["sync_username"]:
                    await self.member_sync.update_member_username(member, dgg_subscriber_index)

        exec_time = int(time.time() - start)
        logger.info("background_update_roles() background sync completed. Took {} seconds".format(exec_time))
