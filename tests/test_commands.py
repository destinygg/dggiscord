import unittest

import disnake

from commands.livestatuscfg import HubSettings
from commands.sync import SyncCommands
from commands.syncsettings import SyncSettings
from subsync.sync import MemberSync
from tests.fakes import FakeApi, FakeChannel, FakeGuild, FakeInteraction, FakeRole, FakeMember, migrated_store

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

    async def sync(self):
        inter = FakeInteraction(self.guild, self.author)
        await self.cog.sync.callback(self.cog, inter)
        return inter.replies[-1]

    async def syncother(self, author, target):
        inter = FakeInteraction(self.guild, author)
        await self.cog.syncother.callback(self.cog, inter, target)
        return inter

    async def test_disabled_server(self):
        self.assertIn("Sync feature is currently disabled", await self.sync())

    async def test_defers_before_looking_up_profile(self):
        self.store.set_sync_settings(self.guild.id, sync_username=True)
        inter = FakeInteraction(self.guild, self.author)
        await self.cog.sync.callback(self.cog, inter)
        self.assertTrue(inter.response.deferred)

    async def test_unlinked_account(self):
        self.store.set_sync_settings(self.guild.id, sync_username=True)
        reply = await self.sync()
        self.assertIn("Your profile was not found", reply)
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
        inter = await self.syncother(self.author, target)
        self.assertEqual(target.nick, "old")
        self.assertEqual(len(inter.sent), 1)
        self.assertTrue(inter.sent[0][1], "the denial should be ephemeral")

    async def test_syncother_by_bot_owner(self):
        self.store.set_sync_settings(self.guild.id, sync_username=True)
        owner = FakeMember(self.guild, member_id=BOT_OWNER)
        target = FakeMember(self.guild, nick="old")
        self.api.profiles[target.id] = profile("Target")
        inter = await self.syncother(owner, target)
        self.assertEqual(target.nick, "Target")
        self.assertIn("synced: username to `Target`", inter.replies[-1])


class SyncSettingsCommandTest(CommandTest):
    def setUp(self):
        super().setUp()
        self.cog = SyncSettings(self.store, [BOT_OWNER])

    async def run_command(self, action=None, setting=None, administrator=True):
        inter = FakeInteraction(self.guild, self.author, administrator=administrator)
        await self.cog.sync_settings.callback(self.cog, inter, action, setting)
        return inter.replies

    async def test_enable_and_disable(self):
        await self.run_command("enable", "all")
        await self.run_command("disable", "subscription")
        self.assertEqual(self.store.sync_settings(self.guild.id), {"sync_subscription": False, "sync_username": True})

    async def test_reports_settings(self):
        await self.run_command("enable", "username")
        self.assertIn("Username sync: **enabled**", (await self.run_command())[0])

    async def test_ignored_without_privileges(self):
        self.assertIn("Only server owners", (await self.run_command("enable", "all", administrator=False))[0])
        self.assertFalse(self.store.sync_enabled(self.guild.id))


class HubSettingsCommandTest(CommandTest):
    def setUp(self):
        super().setUp()
        self.cog = HubSettings(self.store)

    async def run_command(self, command, *args, administrator=True):
        inter = FakeInteraction(self.guild, self.author, administrator=administrator)
        await command.callback(self.cog, inter, *args)
        return inter.replies

    async def hubchannel(self, subcommand, *args, administrator=True):
        command = getattr(self.cog, f"hubchannel_{subcommand}")
        return await self.run_command(command, *args, administrator=administrator)

    async def test_set_get_unset(self):
        channel = FakeChannel(self.guild)
        await self.hubchannel("set", channel)
        self.assertIn(f"<#{channel.id}>", (await self.hubchannel("get"))[0])
        await self.hubchannel("unset")
        self.assertIn("No hub channel is set", (await self.hubchannel("get"))[0])

    async def test_set_requires_bot_permissions(self):
        channel = FakeChannel(self.guild, permissions=disnake.Permissions(view_channel=True, send_messages=True))
        inter = FakeInteraction(self.guild, self.author, administrator=True)
        await self.cog.hubchannel_set.callback(self.cog, inter, channel)
        self.assertIn("*Embed Links*", inter.replies[0])
        self.assertNotIn("*Send Messages*", inter.replies[0])
        self.assertTrue(inter.sent[0][1], "the error should be ephemeral")
        self.assertIsNone(self.store.hub_channel(self.guild.id))

    async def test_admin_only(self):
        channel = FakeChannel(self.guild)
        self.assertIn("Only server admins", (await self.hubchannel("set", channel, administrator=False))[0])
        self.assertIsNone(self.store.hub_channel(self.guild.id))

    async def test_hubrole_set_get_unset(self):
        role = self.guild.add_role("Notifications")
        await self.run_command(self.cog.hubrole_set, role)
        self.assertIn("**Notifications**", (await self.run_command(self.cog.hubrole_get))[0])
        await self.run_command(self.cog.hubrole_unset)
        self.assertIn("No notify role is set", (await self.run_command(self.cog.hubrole_get))[0])

    async def test_hubrole_rejects_everyone(self):
        everyone = FakeRole(self.guild, "@everyone", role_id=self.guild.id)
        self.assertIn("@everyone can't be used", (await self.run_command(self.cog.hubrole_set, everyone))[0])
        self.assertIsNone(self.store.hub_notify_role(self.guild.id))


if __name__ == "__main__":
    unittest.main()
