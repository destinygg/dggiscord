import unittest

from commands.debug import Debug
from commands.streaminfo import StreamInfo, UNAVAILABLE
from hub.notifier import DEFAULT_SETTINGS
from tests.fakes import FakeGuild, FakeInteraction, FakeMember

BOT_OWNER = 7


def ok(data):
    return {"success": True, "message": None, "data": data, "error": None}


def youtube_stream(live):
    return {
        "live": live,
        "viewers": 4576 if live else None,
        "status_text": "chillin'",
        "started_at": "2026-10-07T17:00:00+0000",
        "ended_at": None if live else "2026-10-07T19:00:00+0000",
        "id": "abc",
    }


class StreamInfoTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = dict(DEFAULT_SETTINGS)
        # url -> response; missing urls fail like get_json does
        self.responses = {}
        self.cog = StreamInfo(self.fetch_json, self.settings)
        self.guild = FakeGuild()
        self.author = FakeMember(self.guild)

    async def fetch_json(self, url):
        return self.responses.get(url)

    def respond(self, setting, data):
        self.responses[self.settings[setting]] = ok(data)

    async def run_command(self, command):
        inter = FakeInteraction(self.guild, self.author)
        await command.callback(self.cog, inter)
        self.assertTrue(inter.response.deferred)
        return inter

    async def test_live(self):
        self.respond("stream_endpoint", {"streams": {"youtube": youtube_stream(True), "kick": None}})
        inter = await self.run_command(self.cog.live)
        self.assertIn("Viewers", [field.name for field in inter.embeds[0].fields])

    async def test_hosting_when_offline(self):
        self.respond("stream_endpoint", {"streams": {"youtube": youtube_stream(False)}})
        self.respond("hosting_endpoint", {"platform": "kick", "displayName": "someone", "url": "https://kick.com/someone"})
        inter = await self.run_command(self.cog.live)
        self.assertEqual(inter.embeds[0].title, '"someone" is being hosted on destiny.gg')

    async def test_offline(self):
        self.respond("stream_endpoint", {"streams": {"youtube": youtube_stream(False)}})
        self.respond("hosting_endpoint", None)
        inter = await self.run_command(self.cog.live)
        self.assertEqual(inter.embeds[0].title, "Destiny is offline")

    async def test_offline_when_hosting_lookup_fails(self):
        self.respond("stream_endpoint", {"streams": {"youtube": youtube_stream(False)}})
        inter = await self.run_command(self.cog.live)
        self.assertEqual(inter.embeds[0].title, "Destiny is offline")

    async def test_live_unavailable(self):
        inter = await self.run_command(self.cog.live)
        self.assertEqual(inter.replies, [UNAVAILABLE])

    async def test_youtube(self):
        self.respond("videos_endpoint", [
            {"title": "older", "url": "https://yt.test/1", "publishDate": "2026-10-05T10:00:00+0000"},
            {"title": "newest", "url": "https://yt.test/2", "publishDate": "2026-10-07T11:00:00+0000"},
        ])
        inter = await self.run_command(self.cog.youtube)
        self.assertEqual(inter.embeds[0].title, "newest")

    async def test_youtube_unavailable(self):
        inter = await self.run_command(self.cog.youtube)
        self.assertEqual(inter.replies, [UNAVAILABLE])

    async def test_vods(self):
        self.respond("vods_endpoint", [{"title": "latest", "url": "https://kick.test/1"}, {"title": "older"}])
        inter = await self.run_command(self.cog.vods)
        self.assertEqual(inter.embeds[0].title, "latest")
        self.assertEqual([field.name for field in inter.embeds[0].fields], ["older"])

    async def test_no_vods(self):
        self.respond("vods_endpoint", [])
        inter = await self.run_command(self.cog.vods)
        self.assertEqual(inter.replies, ["There are no VODs to show."])


class DebugCommandTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.cog = Debug([BOT_OWNER], started_at=1_791_388_800, version="v2.2.0")
        self.guild = FakeGuild()

    async def debug(self, author):
        inter = FakeInteraction(self.guild, author, administrator=True)
        await self.cog.debug.callback(self.cog, inter)
        return inter

    async def test_shows_version_and_uptime_to_owner(self):
        inter = await self.debug(FakeMember(self.guild, member_id=BOT_OWNER))
        self.assertIn("`v2.2.0`", inter.replies[0])
        self.assertIn("<t:1791388800:f>", inter.replies[0])
        self.assertTrue(inter.sent[0][1], "the reply should be ephemeral")

    async def test_denies_server_admins(self):
        inter = await self.debug(FakeMember(self.guild))
        self.assertIn("Only the bot owner", inter.replies[0])
        self.assertTrue(inter.sent[0][1], "the error should be ephemeral")


if __name__ == "__main__":
    unittest.main()
