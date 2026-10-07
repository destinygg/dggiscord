import unittest

from hub.notifier import live_streams
from hub.status import (
    build_host_status,
    build_live_status,
    build_offline_status,
    build_vods_message,
    format_duration,
    latest_video,
)

BIGSCREEN = "https://www.destiny.gg/bigscreen"


def stream(live=True, viewers=100, started_at="2026-10-07T17:00:00+0000", ended_at=None, **kwargs):
    return {
        "live": live,
        "viewers": viewers,
        "started_at": started_at,
        "ended_at": ended_at,
        "status_text": kwargs.pop("status_text", "chillin'"),
        **kwargs,
    }


def vod(n, platform="kick"):
    return {
        "id": f"vod{n}",
        "platform": platform,
        "title": f"VOD {n}",
        "highThumbnailUrl": f"https://img.test/{n}.webp",
        "streamStartTime": "2026-10-07T17:01:19+0000",
        "url": f"https://kick.com/Destiny/videos/{n}",
        "embedUrl": f"/bigscreen#kick-vod/Destiny/vod{n}",
    }


class FormatDurationTest(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(format_duration(30), "1m")
        self.assertEqual(format_duration(3 * 3600 + 25 * 60), "3h 25m")
        self.assertEqual(format_duration(26 * 3600), "1d 2h")


class LiveStatusTest(unittest.TestCase):
    def test_totals_viewers_across_platforms(self):
        live = live_streams({
            "youtube": stream(viewers=4576, id="abc"),
            "kick": stream(viewers=2987, id="destiny", started_at="2026-10-07T16:00:00+0000"),
            "twitch": None,
        })
        fields = {field.name: field.value for field in build_live_status(live, BIGSCREEN).fields}
        self.assertEqual(fields["Viewers"], "**7,563** (YouTube 4,576 · Kick 2,987)")
        self.assertIn("https://kick.com/destiny", fields["Watch on"])
        # the earliest start, 2026-10-07T16:00:00Z
        self.assertEqual(fields["Started"], "<t:1791388800:R>")

    def test_without_viewer_counts(self):
        live = live_streams({"youtube": stream(viewers=None, started_at=None)})
        names = [field.name for field in build_live_status(live, BIGSCREEN).fields]
        self.assertNotIn("Viewers", names)
        self.assertNotIn("Started", names)


class HostStatusTest(unittest.TestCase):
    def test_links_to_hosted_stream(self):
        embed = build_host_status({
            "platform": "youtube",
            "displayName": "obamna",
            "url": "https://www.youtube.com/watch?v=tZ",
            "preview": None,
        }, BIGSCREEN)
        self.assertEqual(embed.title, '"obamna" is being hosted on destiny.gg')
        self.assertIn(f"[Bigscreen]({BIGSCREEN})", embed.description)
        self.assertIn("[YouTube](https://www.youtube.com/watch?v=tZ)", embed.description)
        self.assertIsNone(embed.image.url)


class OfflineStatusTest(unittest.TestCase):
    def test_describes_most_recent_stream(self):
        streams = {
            "youtube": stream(live=False, started_at="2026-10-06T17:00:00+0000", ended_at="2026-10-06T20:30:00+0000", status_text="old"),
            "kick": stream(live=False, started_at="2026-10-07T17:00:00+0000", ended_at="2026-10-07T19:00:00+0000", status_text="latest"),
        }
        embed = build_offline_status(streams, BIGSCREEN)
        self.assertEqual(embed.title, "Destiny is offline")
        self.assertIn("for 2h", embed.description)
        self.assertIn("> latest", embed.description)

    def test_without_end_time(self):
        embed = build_offline_status({"youtube": stream(live=False), "kick": None}, BIGSCREEN)
        self.assertEqual(embed.title, "Destiny is offline")
        self.assertIsNone(embed.description)


class VodsMessageTest(unittest.TestCase):
    def test_no_vods(self):
        self.assertIsNone(build_vods_message([], BIGSCREEN))

    def test_one_vod(self):
        embed = build_vods_message([vod(1)], BIGSCREEN)
        self.assertEqual(embed.title, "VOD 1")
        self.assertIn("[Kick](https://kick.com/Destiny/videos/1)", embed.description)
        self.assertIn("[Bigscreen](https://www.destiny.gg/bigscreen#kick-vod/Destiny/vod1)", embed.description)
        self.assertEqual(embed.fields, [])

    def test_lists_three_older_vods(self):
        embed = build_vods_message([vod(n) for n in range(1, 6)], BIGSCREEN)
        self.assertEqual(embed.title, "VOD 1")
        self.assertEqual([field.name for field in embed.fields], ["VOD 2", "VOD 3", "VOD 4"])


class LatestVideoTest(unittest.TestCase):
    def test_picks_newest_publish_date(self):
        videos = [
            {"id": "a", "publishDate": "2026-10-05T10:00:00+0000"},
            {"id": "b", "publishDate": "2026-10-07T11:00:00+0000"},
            {"id": "c", "publishDate": None},
        ]
        self.assertEqual(latest_video(videos)["id"], "b")

    def test_empty(self):
        self.assertIsNone(latest_video([]))


if __name__ == "__main__":
    unittest.main()
