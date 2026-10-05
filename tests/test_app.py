import asyncio
import json
import os
import sqlite3
import tempfile
import unittest

from app import build_bot
from helpers.migrator import Migrator

EXAMPLE_CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.example.json")


class BuildBotTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        with open(EXAMPLE_CONFIG) as f:
            self.cfg = json.load(f)

        fd, path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        self.addCleanup(os.remove, path)
        Migrator(path).upgrade()
        self.con = sqlite3.connect(path)
        self.addCleanup(self.con.close)

        self.bot = build_bot(self.cfg, self.con)
        # let each cog's cog_load run and start its loops
        await asyncio.sleep(0)

    async def asyncTearDown(self):
        for name in list(self.bot.cogs):
            self.bot.remove_cog(name)
        await asyncio.sleep(0)

    def test_registers_every_command(self):
        self.assertEqual(
            sorted(command.name for command in self.bot.commands),
            ["hubchannel", "hubrole", "sync", "sync-settings", "syncother"],
        )

    def test_no_help_command(self):
        self.assertIsNone(self.bot.get_command("help"))

    def test_prefix_from_config(self):
        self.assertEqual(self.bot.command_prefix, self.cfg["discord"]["prefix"])

    def test_registers_event_listeners(self):
        listeners = {name for cog in self.bot.cogs.values() for name, _ in cog.get_listeners()}
        self.assertEqual(listeners, {"on_ready", "on_member_join", "on_guild_join"})

    def test_starts_loops_with_configured_intervals(self):
        background = self.bot.get_cog("BackgroundSync").background_update_roles
        hub = self.bot.get_cog("HubNotify").hub_notify
        presence = self.bot.get_cog("Presence").refresh_now_playing
        self.assertTrue(background.is_running() and hub.is_running() and presence.is_running())
        self.assertEqual(background.minutes, self.cfg["discord"]["background_refresh_rate"])
        self.assertEqual(hub.seconds, self.cfg["dgg"]["hub"]["poll_interval"])

    async def test_removing_cogs_stops_loops(self):
        hub = self.bot.get_cog("HubNotify").hub_notify
        self.bot.remove_cog("HubNotify")
        await asyncio.sleep(0)
        self.assertFalse(hub.is_running())


if __name__ == "__main__":
    unittest.main()
