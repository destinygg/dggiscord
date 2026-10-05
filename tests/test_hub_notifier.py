import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone

from helpers.migrator import Migrator
from hub.notifier import (
    DEFAULT_SETTINGS,
    HubNotifier,
    build_live_message,
    build_video_message,
    live_streams,
    load_settings,
    platform_url,
)

STREAM_URL = DEFAULT_SETTINGS["stream_endpoint"]
VIDEOS_URL = DEFAULT_SETTINGS["videos_endpoint"]

NOW = datetime(2026, 10, 4, 18, 0, tzinfo=timezone.utc).timestamp()


def iso(ts):
    # matches PHP's DATE_ISO8601 output, e.g. 2026-10-04T18:00:00+0000
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")


def stream(platform, live=True, **overrides):
    s = {
        "live": live,
        "game": None,
        "preview": None,
        "status_text": None,
        "started_at": iso(NOW),
        "ended_at": None,
        "duration": 0,
        "viewers": 1000 if live else None,
        "id": None,
        "chat_url": None,
        "platform": platform,
        "type": None,
    }
    s.update(overrides)
    return s


def streams_response(*live_entries):
    streams = {"twitch": None, "youtube": None, "facebook": None, "rumble": None, "kick": None}
    for s in live_entries:
        streams[s["platform"]] = s
    return {"success": True, "message": None, "data": {"streams": streams}, "error": None}


OFFLINE = streams_response(stream("twitch", live=False, id="destiny", status_text="last stream"))


def video(video_id, published=NOW, title=None):
    return {
        "id": video_id,
        "title": title or f"Video {video_id}",
        "mediumThumbnailUrl": f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",
        "highThumbnailUrl": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "streamViewers": None,
        "streamStartTime": None,
        "streamEndTime": None,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "embedUrl": f"/bigscreen#youtube/{video_id}",
        "thumbnailHref": "",
        "publishDate": iso(published) if published is not None else None,
    }


def videos_response(*videos):
    return {"success": True, "message": None, "data": list(videos), "error": None}


class FakeClock:
    def __init__(self, now=NOW):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, minutes):
        self.now += minutes * 60


class HubNotifierTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        Migrator(self.db_path).upgrade()
        self.con = sqlite3.connect(self.db_path)

        self.responses = {STREAM_URL: OFFLINE, VIDEOS_URL: videos_response()}
        self.sent = []
        self.failing_channels = set()
        self.clock = FakeClock()
        self.notifier = HubNotifier(self.con, self.fetch_json, self.send, dict(DEFAULT_SETTINGS), self.clock)

    def tearDown(self):
        self.con.close()
        os.remove(self.db_path)

    async def fetch_json(self, url):
        return self.responses.get(url)

    async def send(self, channel_id, content, embed):
        if channel_id in self.failing_channels:
            raise RuntimeError("Missing Permissions")
        self.sent.append((channel_id, content, embed))

    def set_hub_channel(self, server_id, channel_id):
        self.con.execute("REPLACE INTO hubchannels VALUES (?, ?)", (server_id, channel_id))
        self.con.commit()

    def go_live(self, **overrides):
        self.responses[STREAM_URL] = streams_response(stream("twitch", id="destiny", **overrides))

    def go_offline(self):
        self.responses[STREAM_URL] = OFFLINE

    # --- going live ---

    async def test_first_poll_does_not_announce_a_stream_already_live(self):
        self.set_hub_channel(1, 100)
        self.go_live()

        await self.notifier.poll()

        self.assertEqual(self.sent, [])

    async def test_going_live_is_posted_to_every_hub_channel(self):
        self.set_hub_channel(1, 100)
        self.set_hub_channel(2, 200)
        await self.notifier.poll()

        self.go_live(status_text="Debating the internet")
        self.clock.advance(1)
        await self.notifier.poll()

        self.assertEqual([channel for channel, _, _ in self.sent], [100, 200])
        _, content, embed = self.sent[0]
        self.assertIn("Destiny is live!", content)
        self.assertEqual(embed.title, "Debating the internet")

    async def test_staying_live_is_only_posted_once(self):
        self.set_hub_channel(1, 100)
        await self.notifier.poll()

        self.go_live()
        for _ in range(5):
            self.clock.advance(1)
            await self.notifier.poll()

        self.assertEqual(len(self.sent), 1)

    async def test_another_platform_joining_mid_stream_is_not_posted(self):
        self.set_hub_channel(1, 100)
        await self.notifier.poll()

        self.go_live()
        await self.notifier.poll()
        self.responses[STREAM_URL] = streams_response(
            stream("twitch", id="destiny"),
            stream("youtube", id="abc123"),
        )
        await self.notifier.poll()

        self.assertEqual(len(self.sent), 1)

    async def test_reconnecting_within_the_cooldown_is_not_posted_again(self):
        self.set_hub_channel(1, 100)
        await self.notifier.poll()
        self.go_live()
        await self.notifier.poll()

        self.go_offline()
        self.clock.advance(2)
        await self.notifier.poll()
        self.go_live()
        self.clock.advance(2)
        await self.notifier.poll()

        self.assertEqual(len(self.sent), 1)

    async def test_going_live_again_after_the_cooldown_is_posted(self):
        self.set_hub_channel(1, 100)
        await self.notifier.poll()
        self.go_live()
        await self.notifier.poll()

        self.go_offline()
        self.clock.advance(DEFAULT_SETTINGS["live_cooldown"] + 1)
        await self.notifier.poll()
        self.go_live()
        await self.notifier.poll()

        self.assertEqual(len(self.sent), 2)

    async def test_live_state_survives_a_restart(self):
        self.set_hub_channel(1, 100)
        await self.notifier.poll()
        self.go_live()
        await self.notifier.poll()

        restarted = HubNotifier(self.con, self.fetch_json, self.send, dict(DEFAULT_SETTINGS), self.clock)
        await restarted.poll()

        self.assertEqual(len(self.sent), 1)

    # --- new videos ---

    async def test_first_poll_does_not_announce_existing_videos(self):
        self.set_hub_channel(1, 100)
        self.responses[VIDEOS_URL] = videos_response(video("a"), video("b"))

        await self.notifier.poll()

        self.assertEqual(self.sent, [])

    async def test_new_video_is_posted(self):
        self.set_hub_channel(1, 100)
        self.responses[VIDEOS_URL] = videos_response(video("a", published=NOW - 86400 * 3))
        await self.notifier.poll()

        self.responses[VIDEOS_URL] = videos_response(video("b", title="New upload"), video("a", published=NOW - 86400 * 3))
        await self.notifier.poll()

        self.assertEqual(len(self.sent), 1)
        channel, content, embed = self.sent[0]
        self.assertEqual(channel, 100)
        self.assertIn("New upload", content)
        self.assertIn("https://www.youtube.com/watch?v=b", content)
        self.assertEqual(embed.url, "https://www.youtube.com/watch?v=b")

    async def test_multiple_new_videos_are_posted_oldest_first(self):
        self.set_hub_channel(1, 100)
        await self.notifier.poll()

        self.responses[VIDEOS_URL] = videos_response(video("newer"), video("older", published=NOW - 3600))
        await self.notifier.poll()

        self.assertEqual([embed.title for _, _, embed in self.sent], ["Video older", "Video newer"])

    async def test_video_that_returns_to_the_list_is_not_posted_again(self):
        self.set_hub_channel(1, 100)
        await self.notifier.poll()

        self.responses[VIDEOS_URL] = videos_response(video("a"))
        await self.notifier.poll()
        self.responses[VIDEOS_URL] = videos_response(video("b"))
        await self.notifier.poll()
        self.responses[VIDEOS_URL] = videos_response(video("a"), video("b"))
        await self.notifier.poll()

        self.assertEqual([embed.title for _, _, embed in self.sent], ["Video a", "Video b"])

    async def test_old_video_new_to_the_list_is_not_posted(self):
        self.set_hub_channel(1, 100)
        await self.notifier.poll()

        stale = NOW - (DEFAULT_SETTINGS["video_max_age"] + 1) * 3600
        self.responses[VIDEOS_URL] = videos_response(video("old", published=stale))
        await self.notifier.poll()

        self.assertEqual(self.sent, [])

    async def test_video_without_publish_date_is_posted(self):
        # Vimeo uploads don't carry a publish date
        self.set_hub_channel(1, 100)
        await self.notifier.poll()

        self.responses[VIDEOS_URL] = videos_response(video("vimeo1", published=None))
        await self.notifier.poll()

        self.assertEqual(len(self.sent), 1)
        self.assertIsNone(self.sent[0][2].timestamp)

    # --- failures and channel handling ---

    async def test_failed_fetch_leaves_state_alone(self):
        self.set_hub_channel(1, 100)
        await self.notifier.poll()

        self.responses[STREAM_URL] = None
        self.responses[VIDEOS_URL] = {"success": False, "message": None, "data": None, "error": "oops"}
        await self.notifier.poll()

        self.go_live()
        self.responses[VIDEOS_URL] = videos_response(video("a"))
        await self.notifier.poll()

        self.assertEqual(len(self.sent), 2)

    async def test_failing_channel_does_not_block_other_channels(self):
        self.set_hub_channel(1, 100)
        self.set_hub_channel(2, 200)
        self.failing_channels.add(100)
        await self.notifier.poll()

        self.go_live()
        await self.notifier.poll()

        self.assertEqual([channel for channel, _, _ in self.sent], [200])

    async def test_events_without_hub_channels_are_not_posted_later(self):
        await self.notifier.poll()
        self.go_live()
        self.responses[VIDEOS_URL] = videos_response(video("a"))
        await self.notifier.poll()

        self.set_hub_channel(1, 100)
        await self.notifier.poll()

        self.assertEqual(self.sent, [])


class MessageTest(unittest.TestCase):
    def test_live_streams_only_includes_live_platforms_in_display_order(self):
        streams = streams_response(
            stream("kick", id="destiny"),
            stream("youtube", id="abc123"),
            stream("twitch", live=False, id="destiny"),
        )["data"]["streams"]

        self.assertEqual([platform for platform, _ in live_streams(streams)], ["youtube", "kick"])

    def test_platform_url(self):
        self.assertEqual(platform_url("twitch", "destiny"), "https://www.twitch.tv/destiny")
        self.assertEqual(platform_url("youtube", "abc123"), "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(platform_url("kick", "destiny"), "https://kick.com/destiny")
        self.assertEqual(
            platform_url("facebook", "/107941938752517/videos/612064270574857"),
            "https://www.facebook.com/107941938752517/videos/612064270574857",
        )
        self.assertIsNone(platform_url("rumble", "v4abcd"))
        self.assertIsNone(platform_url("youtube", None))

    def test_live_message(self):
        live = [
            ("twitch", stream("twitch", id="destiny", status_text="Title", game="Just Chatting", preview="https://img/preview.jpg")),
            ("rumble", stream("rumble", id="v4abcd")),
        ]

        content, embed = build_live_message(live, "https://www.destiny.gg/bigscreen")

        self.assertEqual(content, "**Destiny is live!** https://www.destiny.gg/bigscreen")
        self.assertEqual(embed.title, "Title")
        self.assertEqual(embed.url, "https://www.destiny.gg/bigscreen")
        self.assertEqual(embed.image.url, "https://img/preview.jpg")
        fields = {field.name: field.value for field in embed.fields}
        self.assertEqual(
            fields["Watch on"],
            "[Twitch](https://www.twitch.tv/destiny) · Rumble · [destiny.gg](https://www.destiny.gg/bigscreen)",
        )
        self.assertEqual(fields["Category"], "Just Chatting")

    def test_live_message_without_details(self):
        content, embed = build_live_message([("kick", stream("kick", id="destiny"))], "https://www.destiny.gg/bigscreen")

        self.assertEqual(embed.title, "Destiny is live!")
        self.assertNotIn("Category", [field.name for field in embed.fields])
        self.assertIsNone(embed.image.url)

    def test_video_message(self):
        content, embed = build_video_message(video("abc", title="My video"))

        self.assertEqual(content, "**New video:** My video https://www.youtube.com/watch?v=abc")
        self.assertEqual(embed.title, "My video")
        self.assertEqual(embed.image.url, "https://i.ytimg.com/vi/abc/hqdefault.jpg")
        self.assertEqual(embed.timestamp.timestamp(), NOW)

    def test_load_settings_overrides_defaults(self):
        settings = load_settings({"dgg": {"hub": {"poll_interval": 120}}})

        self.assertEqual(settings["poll_interval"], 120)
        self.assertEqual(settings["stream_endpoint"], DEFAULT_SETTINGS["stream_endpoint"])
        self.assertEqual(load_settings({}), DEFAULT_SETTINGS)


class HubMigrationTest(unittest.TestCase):
    def test_upgrade_and_downgrade(self):
        fd, db_path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        try:
            migrator = Migrator(db_path)
            migrator.upgrade()
            migrator.downgrade()

            con = sqlite3.connect(db_path)
            tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            con.close()
            self.assertNotIn("hubstate", tables)
            self.assertNotIn("hubseenvideos", tables)
            self.assertIn("hubchannels", tables)
        finally:
            os.remove(db_path)


if __name__ == "__main__":
    unittest.main()
