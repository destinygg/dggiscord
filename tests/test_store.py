import os
import sqlite3
import tempfile
import unittest

from helpers.migrator import Migrator
from helpers.store import Store

GUILD = 1
OTHER_GUILD = 2
NOW = "2026-10-04T18:00:00+00:00"
LATER = "2026-10-04T19:00:00+00:00"


class StoreTest(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        Migrator(self.db_path).upgrade()
        self.con = sqlite3.connect(self.db_path)
        self.store = Store(self.con)

    def tearDown(self):
        self.con.close()
        os.remove(self.db_path)

    def flair_row(self, role_id):
        return self.con.execute("SELECT last_updated, last_refresh FROM flairmap WHERE discord_role=?", (role_id,)).fetchone()


class SyncSettingsTest(StoreTest):
    def test_unset_guild_has_everything_disabled(self):
        self.assertEqual(self.store.sync_settings(GUILD), {"sync_subscription": False, "sync_username": False})
        self.assertFalse(self.store.sync_enabled(GUILD))

    def test_enabling_one_option_leaves_the_other_disabled(self):
        self.store.set_sync_settings(GUILD, sync_subscription=True)
        self.assertEqual(self.store.sync_settings(GUILD), {"sync_subscription": True, "sync_username": False})
        self.assertTrue(self.store.sync_enabled(GUILD))

    def test_changing_one_option_keeps_the_other(self):
        self.store.set_sync_settings(GUILD, sync_subscription=True, sync_username=True)
        self.store.set_sync_settings(GUILD, sync_username=False)
        self.assertEqual(self.store.sync_settings(GUILD), {"sync_subscription": True, "sync_username": False})

    def test_disabling_everything(self):
        self.store.set_sync_settings(GUILD, sync_subscription=True, sync_username=True)
        self.store.set_sync_settings(GUILD, sync_subscription=False, sync_username=False)
        self.assertFalse(self.store.sync_enabled(GUILD))

    def test_settings_are_per_guild(self):
        self.store.set_sync_settings(GUILD, sync_username=True)
        self.assertFalse(self.store.sync_enabled(OTHER_GUILD))

    def test_setting_nothing_does_not_create_a_row(self):
        self.store.set_sync_settings(GUILD)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM syncsettings").fetchone()[0], 0)

    def test_writes_are_committed(self):
        self.store.set_sync_settings(GUILD, sync_subscription=True)
        other = sqlite3.connect(self.db_path)
        self.addCleanup(other.close)
        self.assertTrue(Store(other).sync_enabled(GUILD))


class FlairMappingTest(StoreTest):
    def test_add_and_look_up(self):
        self.store.add_flair_role(GUILD, 101, "flair13", NOW)
        self.assertEqual(self.store.flair_role(GUILD, "flair13"), 101)
        self.assertEqual(self.store.flair_mappings(GUILD), [(101, "flair13")])
        self.assertEqual(self.flair_row(101), (NOW, NOW))

    def test_unmapped_flair(self):
        self.assertIsNone(self.store.flair_role(GUILD, "flair13"))

    def test_mappings_are_per_guild(self):
        self.store.add_flair_role(GUILD, 101, "flair13", NOW)
        self.store.add_flair_role(OTHER_GUILD, 201, "flair13", NOW)
        self.assertEqual(self.store.flair_role(OTHER_GUILD, "flair13"), 201)
        self.assertEqual(self.store.flair_mappings(GUILD), [(101, "flair13")])

    def test_refresh_without_update_keeps_last_updated(self):
        self.store.add_flair_role(GUILD, 101, "flair13", NOW)
        self.store.mark_flair_refreshed(101, LATER)
        self.assertEqual(self.flair_row(101), (NOW, LATER))

    def test_refresh_with_update(self):
        self.store.add_flair_role(GUILD, 101, "flair13", NOW)
        self.store.mark_flair_refreshed(101, LATER, updated=True)
        self.assertEqual(self.flair_row(101), (LATER, LATER))

    def test_delete(self):
        self.store.add_flair_role(GUILD, 101, "flair13", NOW)
        self.store.add_flair_role(GUILD, 102, "flair8", NOW)
        self.store.delete_flair_role(101)
        self.assertEqual(self.store.flair_mappings(GUILD), [(102, "flair8")])


class HubSettingsTest(StoreTest):
    def test_unset_guild(self):
        self.assertIsNone(self.store.hub_channel(GUILD))
        self.assertIsNone(self.store.hub_notify_role(GUILD))

    def test_set_and_unset_channel(self):
        self.store.set_hub_channel(GUILD, 500)
        self.assertEqual(self.store.hub_channel(GUILD), 500)
        self.store.set_hub_channel(GUILD, None)
        self.assertIsNone(self.store.hub_channel(GUILD))

    def test_set_and_unset_notify_role(self):
        self.store.set_hub_notify_role(GUILD, 600)
        self.assertEqual(self.store.hub_notify_role(GUILD), 600)
        self.store.set_hub_notify_role(GUILD, None)
        self.assertIsNone(self.store.hub_notify_role(GUILD))

    def test_changing_the_channel_keeps_the_role(self):
        self.store.set_hub_channel(GUILD, 500)
        self.store.set_hub_notify_role(GUILD, 600)
        self.store.set_hub_channel(GUILD, 501)
        self.assertEqual(self.store.hub_notify_role(GUILD), 600)

    def test_changing_the_role_keeps_the_channel(self):
        self.store.set_hub_notify_role(GUILD, 600)
        self.store.set_hub_channel(GUILD, 500)
        self.store.set_hub_notify_role(GUILD, None)
        self.assertEqual(self.store.hub_channel(GUILD), 500)


if __name__ == "__main__":
    unittest.main()
