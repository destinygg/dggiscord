import unittest

from commands.livestatuscfg import HubSettings
from commands.sync import SyncCommands
from commands.syncsettings import SyncSettings
from subsync.sync import MemberSync
from tests.fakes import FakeApi, FakeContext, FakeGuild, FakeMember, migrated_store

BOT_OWNER = 7
NOW = "2026-10-04T18:00:00+00:00"
LINKS = {
    "auth": "https://dgg.test/profile/authentication",
    "subscribe": "https://dgg.test/subscribe",
    "twitchint": "https://twitch.test/integration",
}


def profile(nick="Cake", features=(), subscription=None):
    return {"nick": nick, "username": nick, "features": list(features), "subscription": subscription}


class CommandTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = migrated_store(self)
        self.api = FakeApi()
        self.guild = FakeGuild()
        self.author = FakeMember(self.guild, nick="old")


class SyncCommandTest(CommandTest):
    def setUp(self):
        super().setUp()
        self.cog = SyncCommands(self.store, MemberSync(self.store, self.api), [BOT_OWNER], LINKS)

    async def sync(self, guild=None):
        ctx = FakeContext(guild or self.guild, self.author)
        await self.cog.sync.callback(self.cog, ctx)
        return ctx.replies[-1]

    async def test_disabled_server(self):
        self.assertIn("sync feature is currently disabled", await self.sync())

    async def test_unlinked_account(self):
        self.store.set_sync_settings(self.guild.id, sync_username=True)
        reply = await self.sync()
        self.assertIn("your profile was not found", reply)
        self.assertIn(LINKS["auth"], reply)

    async def test_username_sync(self):
        self.store.set_sync_settings(self.guild.id, sync_username=True)
        self.api.profiles[self.author.id] = profile("Cake")
        reply = await self.sync()
        self.assertIn("username synced to `Cake`", reply)
        self.assertEqual(self.author.nick, "Cake")

    async def test_no_subscription(self):
        self.store.set_sync_settings(self.guild.id, sync_subscription=True)
        self.api.profiles[self.author.id] = profile()
        self.assertIn(LINKS["subscribe"], await self.sync())

    async def test_twitch_subscription(self):
        self.store.set_sync_settings(self.guild.id, sync_subscription=True)
        self.api.profiles[self.author.id] = profile(subscription={"source": "twitch.tv"})
        self.assertIn(LINKS["twitchint"], await self.sync())

    async def test_dgg_subscription_gets_roles(self):
        sub_role = self.guild.add_role("Tier 1")
        self.store.add_flair_role(self.guild.id, sub_role.id, "flair13", NOW)
        self.store.set_sync_settings(self.guild.id, sync_subscription=True)
        self.api.profiles[self.author.id] = profile(features=["flair13"], subscription={
            "source": "destiny.gg", "tier": "1", "end": "2026-11-04T18:00:00+0000",
        })
        reply = await self.sync()
        self.assertIn("tier 1 subscription", reply)
        self.assertEqual(self.author.role_ids(), {sub_role.id})

    async def test_syncother_requires_privileges(self):
        self.store.set_sync_settings(self.guild.id, sync_username=True)
        target = FakeMember(self.guild, nick="old")
        self.api.profiles[target.id] = profile("Target")
        ctx = FakeContext(self.guild, self.author, mentions=[target])
        await self.cog.syncother.callback(self.cog, ctx)
        self.assertEqual((ctx.replies, target.nick), ([], "old"))

    async def test_syncother_by_bot_owner(self):
        self.store.set_sync_settings(self.guild.id, sync_username=True)
        owner = FakeMember(self.guild, member_id=BOT_OWNER)
        target = FakeMember(self.guild, nick="old")
        self.api.profiles[target.id] = profile("Target")
        ctx = FakeContext(self.guild, owner, mentions=[target])
        await self.cog.syncother.callback(self.cog, ctx)
        self.assertEqual(target.nick, "Target")
        self.assertIn("synced: username to `Target`", ctx.replies[-1])


class SyncSettingsCommandTest(CommandTest):
    def setUp(self):
        super().setUp()
        self.cog = SyncSettings(self.store, [BOT_OWNER])

    async def run_command(self, *args, administrator=True):
        ctx = FakeContext(self.guild, self.author, administrator=administrator)
        await self.cog.sync_settings.callback(self.cog, ctx, *args)
        return ctx.replies

    async def test_enable_and_disable(self):
        await self.run_command("enable", "all")
        await self.run_command("disable", "subscription")
        self.assertEqual(self.store.sync_settings(self.guild.id), {"sync_subscription": False, "sync_username": True})

    async def test_reports_settings(self):
        await self.run_command("enable", "username")
        self.assertIn("Username sync: **enabled**", (await self.run_command())[0])

    async def test_ignored_without_privileges(self):
        self.assertEqual(await self.run_command("enable", "all", administrator=False), [])
        self.assertFalse(self.store.sync_enabled(self.guild.id))


class HubSettingsCommandTest(CommandTest):
    def setUp(self):
        super().setUp()
        self.cog = HubSettings(self.store)

    async def hubchannel(self, arg, administrator=True):
        ctx = FakeContext(self.guild, self.author, administrator=administrator)
        await self.cog.hubchannel.callback(self.cog, ctx, arg)
        return ctx.replies

    async def test_set_get_unset(self):
        await self.hubchannel("set")
        self.assertIn("<#555>", (await self.hubchannel("get"))[0])
        await self.hubchannel("unset")
        self.assertIn("No hub channel is set", (await self.hubchannel("get"))[0])

    async def test_admin_only(self):
        self.assertEqual(await self.hubchannel("set", administrator=False), [])
        self.assertIsNone(self.store.hub_channel(self.guild.id))


if __name__ == "__main__":
    unittest.main()
