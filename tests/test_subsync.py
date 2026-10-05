import unittest

import disnake

from discord.background import BackgroundSync
from subsync.sync import MemberSync
from subsync.translator import FlairTranslator
from tests.fakes import FakeApi, FakeGuild, FakeMember, migrated_store

NOW = "2026-10-04T18:00:00+00:00"


def flair(name, label=None, color="#ee1f1f"):
    return {"name": name, "label": label or name.capitalize(), "color": color}


def profile(*features, nick="Cake"):
    return {"nick": nick, "username": nick, "features": list(features), "subscription": None}


class MemberSyncTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = migrated_store(self)
        self.api = FakeApi()
        self.sync = MemberSync(self.store, self.api)

        self.guild = FakeGuild()
        self.sub_role = self.guild.add_role("Sub")
        self.mod_role = self.guild.add_role("Mod")
        self.other_role = self.guild.add_role("Other")
        self.store.add_flair_role(self.guild.id, self.sub_role.id, "flair13", NOW)
        self.store.add_flair_role(self.guild.id, self.mod_role.id, "moderator", NOW)

    async def test_adds_roles_for_profile_features(self):
        member = FakeMember(self.guild)
        self.api.profiles[member.id] = profile("flair13")
        await self.sync.update_member(member)
        self.assertEqual(member.role_ids(), {self.sub_role.id})

    async def test_removes_roles_for_lost_features(self):
        member = FakeMember(self.guild, roles=[self.sub_role, self.mod_role, self.other_role])
        self.api.profiles[member.id] = profile("moderator")
        await self.sync.update_member(member)
        self.assertEqual(member.role_ids(), {self.mod_role.id, self.other_role.id})

    async def test_unlinked_member_loses_synced_roles_only(self):
        member = FakeMember(self.guild, roles=[self.sub_role, self.other_role])
        await self.sync.update_member(member)
        self.assertEqual(member.role_ids(), {self.other_role.id})

    async def test_uses_the_index_instead_of_the_api(self):
        member = FakeMember(self.guild)
        self.api.profiles[member.id] = profile()
        await self.sync.update_member(member, dgg_index={member.id: profile("flair13")})
        self.assertEqual(member.role_ids(), {self.sub_role.id})

    async def test_member_missing_from_the_index_is_treated_as_unlinked(self):
        member = FakeMember(self.guild, roles=[self.sub_role])
        self.api.profiles[member.id] = profile("flair13")
        await self.sync.update_member(member, dgg_index={})
        self.assertEqual(member.role_ids(), set())

    async def test_mapping_for_an_uncached_role_is_skipped_not_deleted(self):
        self.guild.roles.remove(self.mod_role)
        self.assertEqual(self.sync.flair_map(self.guild), {self.sub_role.id: "flair13"})
        self.assertIsNotNone(self.store.flair_role(self.guild.id, "moderator"))

    async def test_username_sync_sets_nick_and_verified_role(self):
        member = FakeMember(self.guild, nick="old")
        await self.sync.update_member_username(member, {member.id: profile(nick="Cake")})
        self.assertEqual(member.nick, "Cake")
        self.assertEqual([role.name for role in member.roles], ["Dgg Verified"])

    async def test_username_sync_skips_members_above_the_bot(self):
        member = FakeMember(self.guild, nick="old", top_position=200)
        await self.sync.update_member_username(member, {member.id: profile(nick="Cake")})
        self.assertEqual(member.nick, "old")

    async def test_username_sync_skips_the_server_owner(self):
        member = FakeMember(self.guild, member_id=self.guild.owner_id, nick="old")
        await self.sync.update_member_username(member, {member.id: profile(nick="Cake")})
        self.assertEqual(member.nick, "old")

    async def test_member_index(self):
        self.api.all_profiles_response = {"status": "success", "data": [{"authId": "42", "status": "Active", "dggSub": None}]}
        self.assertEqual(list(await self.sync.get_all_members_indexed()), [42])

    async def test_member_index_failure(self):
        self.api.all_profiles_response = None
        self.assertIsNone(await self.sync.get_all_members_indexed())


class FlairTranslatorTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = migrated_store(self)
        self.api = FakeApi(flairs=[flair("flair13", "Tier 1"), flair("flair8", "Tier 4"), flair("admin")])
        self.translator = FlairTranslator(self.store, self.api, ["flair13", "flair8"], resync_properties=True)
        self.guild = FakeGuild()

    def mapped_role(self, flair_name):
        return self.guild.get_role(self.store.flair_role(self.guild.id, flair_name))

    async def test_creates_a_role_per_translated_flair(self):
        await self.translator.flairs_to_roles(self.guild)
        self.assertEqual(sorted(role.name for role in self.guild.roles), ["Tier 1", "Tier 4"])
        self.assertEqual(self.mapped_role("flair13").name, "Tier 1")
        self.assertEqual(str(self.mapped_role("flair13").color), "#ee1f1f")

    async def test_second_run_creates_nothing_new(self):
        await self.translator.flairs_to_roles(self.guild)
        roles = list(self.guild.roles)
        await self.translator.flairs_to_roles(self.guild)
        self.assertEqual(self.guild.roles, roles)

    async def test_reverts_edited_roles(self):
        await self.translator.flairs_to_roles(self.guild)
        role = self.mapped_role("flair13")
        role.name = "Renamed"
        role.color = disnake.Color(0)
        await self.translator.flairs_to_roles(self.guild)
        self.assertEqual((role.name, str(role.color)), ("Tier 1", "#ee1f1f"))

    async def test_leaves_edits_when_resync_is_off(self):
        self.translator.resync_properties = False
        await self.translator.flairs_to_roles(self.guild)
        role = self.mapped_role("flair13")
        role.name = "Renamed"
        await self.translator.flairs_to_roles(self.guild)
        self.assertEqual(role.name, "Renamed")

    async def test_recreates_a_deleted_role(self):
        await self.translator.flairs_to_roles(self.guild)
        old = self.mapped_role("flair13")
        self.guild.roles.remove(old)
        await self.translator.flairs_to_roles(self.guild)
        self.assertNotEqual(self.store.flair_role(self.guild.id, "flair13"), old.id)
        self.assertEqual(self.mapped_role("flair13").name, "Tier 1")

    async def test_uncached_role_is_not_recreated(self):
        await self.translator.flairs_to_roles(self.guild)
        role = self.mapped_role("flair13")
        self.guild.roles.remove(role)
        self.guild.uncached_roles.append(role)
        await self.translator.flairs_to_roles(self.guild)
        self.assertEqual(self.store.flair_role(self.guild.id, "flair13"), role.id)

    async def test_removes_role_and_mapping_for_a_dropped_flair(self):
        await self.translator.flairs_to_roles(self.guild)
        role = self.mapped_role("flair8")
        self.translator.translate = {"flair13"}
        await self.translator.flairs_to_roles(self.guild)
        self.assertTrue(role.deleted)
        self.assertIsNone(self.store.flair_role(self.guild.id, "flair8"))

    async def test_keeps_mapping_when_role_delete_fails(self):
        await self.translator.flairs_to_roles(self.guild)
        self.guild.fail_role_deletes = True
        self.translator.translate = {"flair13"}
        await self.translator.flairs_to_roles(self.guild)
        self.assertIsNotNone(self.store.flair_role(self.guild.id, "flair8"))

    async def test_api_failure_changes_nothing(self):
        await self.translator.flairs_to_roles(self.guild)
        self.api.flair_list = None
        await self.translator.flairs_to_roles(self.guild)
        self.assertEqual(len(self.store.flair_mappings(self.guild.id)), 2)


class BackgroundSyncTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = migrated_store(self)
        self.api = FakeApi(flairs=[flair("flair13", "Tier 1")])
        self.member_sync = MemberSync(self.store, self.api)
        self.translator = FlairTranslator(self.store, self.api, ["flair13"], resync_properties=True)
        self.cog = BackgroundSync(None, self.store, self.member_sync, self.translator, refresh_minutes=240)

        self.guild = FakeGuild()
        self.member = FakeMember(self.guild, nick="old")

    def index(self, *features, nick="Cake"):
        self.api.all_profiles_response = {"status": "success", "data": [
            {"authId": str(self.member.id), "status": "Active", "dggSub": None, "nick": nick, "features": list(features)},
        ]}

    async def test_interval_comes_from_config(self):
        self.assertEqual(self.cog.background_update_roles.minutes, 240)

    async def test_syncs_roles_and_names_where_enabled(self):
        self.store.set_sync_settings(self.guild.id, sync_subscription=True, sync_username=True)
        self.index("flair13")
        await self.cog.sync_guilds([self.guild])
        self.assertEqual(sorted(role.name for role in self.member.roles), ["Dgg Verified", "Tier 1"])
        self.assertEqual(self.member.nick, "Cake")

    async def test_username_only_does_not_create_flair_roles(self):
        self.store.set_sync_settings(self.guild.id, sync_username=True)
        self.index("flair13")
        await self.cog.sync_guilds([self.guild])
        self.assertEqual(self.store.flair_mappings(self.guild.id), [])
        self.assertEqual(self.member.nick, "Cake")

    async def test_skips_disabled_guilds(self):
        self.index("flair13")
        await self.cog.sync_guilds([self.guild])
        self.assertEqual((self.member.roles, self.member.nick), ([], "old"))

    async def test_skips_the_pass_when_the_index_fails(self):
        self.store.set_sync_settings(self.guild.id, sync_subscription=True, sync_username=True)
        self.api.all_profiles_response = None
        self.api.profiles[self.member.id] = {"nick": "Cake", "features": ["flair13"]}
        await self.cog.sync_guilds([self.guild])
        self.assertEqual((self.member.roles, self.member.nick), ([], "old"))


if __name__ == "__main__":
    unittest.main()
