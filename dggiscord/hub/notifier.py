"""
Posts stream go-live and new video announcements to each server's hub channel.

The notifier polls the website's public broadcast info endpoints and keeps the
last observed state in the database. It has no dependency on the bot client,
so it can be driven by a test with fake fetch/send functions.
"""
import json
import logging
import time
from datetime import datetime

import disnake

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS = {
    "stream_endpoint": "https://www.destiny.gg/api/info/stream",
    "videos_endpoint": "https://www.destiny.gg/api/info/videos",
    "bigscreen_link": "https://www.destiny.gg/bigscreen",
    # seconds between polls
    "poll_interval": 60,
    # minutes the stream must have been offline before going live is announced
    # again, so a dropped connection doesn't post a second notification
    "live_cooldown": 30,
    # hours; new videos published longer ago than this are recorded but not
    # posted, e.g. when the featured uploads source is switched
    "video_max_age": 24,
}

# display order and names for the platforms in /api/info/stream
PLATFORM_NAMES = {
    "twitch": "Twitch",
    "youtube": "YouTube",
    "kick": "Kick",
    "rumble": "Rumble",
    "facebook": "Facebook",
}

EMBED_COLOR = 0x1E90FF


def load_settings(cfg):
    """Merge the optional dgg.hub config block over the defaults."""
    settings = dict(DEFAULT_SETTINGS)
    settings.update(cfg.get("dgg", {}).get("hub", {}))
    return settings


def platform_url(platform, stream_id):
    """Build a watch link for a live platform, or None if there isn't one."""
    if not stream_id:
        return None
    if platform == "twitch":
        return f"https://www.twitch.tv/{stream_id}"
    if platform == "youtube":
        return f"https://www.youtube.com/watch?v={stream_id}"
    if platform == "kick":
        return f"https://kick.com/{stream_id}"
    if platform == "facebook":
        # the id is the permalink path, e.g. /107941938752517/videos/612064270574857
        return f"https://www.facebook.com{stream_id}"
    # rumble's id is an internal video ID, not something that can be linked
    return None


def live_streams(streams):
    """Return the live entries of an /api/info/stream map, in display order."""
    ordered = sorted(
        (streams or {}).items(),
        key=lambda item: list(PLATFORM_NAMES).index(item[0]) if item[0] in PLATFORM_NAMES else len(PLATFORM_NAMES),
    )
    return [(platform, s) for platform, s in ordered if s and s.get("live")]


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def build_live_message(live, bigscreen_link):
    """Build the (content, embed) announcing that the stream went live."""
    title = next((s["status_text"] for _, s in live if s.get("status_text")), None)
    game = next((s["game"] for _, s in live if s.get("game")), None)
    preview = next((s["preview"] for _, s in live if s.get("preview")), None)

    embed = disnake.Embed(
        title=title or "Destiny is live!",
        url=bigscreen_link,
        color=EMBED_COLOR,
    )
    embed.set_author(name="Destiny is live!")

    platforms = []
    for platform, s in live:
        name = PLATFORM_NAMES.get(platform, platform.capitalize())
        url = platform_url(platform, s.get("id"))
        platforms.append(f"[{name}]({url})" if url else name)
    platforms.append(f"[destiny.gg]({bigscreen_link})")
    embed.add_field(name="Watch on", value=" · ".join(platforms), inline=False)

    if game:
        embed.add_field(name="Category", value=game, inline=True)
    if preview:
        embed.set_image(url=preview)

    content = f"**Destiny is live!** {bigscreen_link}"
    return content, embed


def build_video_message(video):
    """Build the (content, embed) announcing a new video upload."""
    embed = disnake.Embed(
        title=video.get("title") or "New video",
        url=video.get("url") or None,
        color=EMBED_COLOR,
    )
    embed.set_author(name="New video")

    thumbnail = video.get("highThumbnailUrl") or video.get("mediumThumbnailUrl")
    if thumbnail:
        embed.set_image(url=thumbnail)

    published = parse_date(video.get("publishDate"))
    if published:
        embed.timestamp = published

    content = f"**New video:** {video.get('title', '')} {video.get('url', '')}".strip()
    return content, embed


class HubNotifier:
    def __init__(self, con, fetch_json, send, settings=None, clock=time.time):
        """
        Args:
            con: sqlite3 connection with the hub tables migrated
            fetch_json: async function(url) -> parsed JSON or None on failure
            send: async function(channel_id, content, embed); raises on failure
            settings: dict as returned by load_settings()
            clock: function returning the current unix time
        """
        self.con = con
        self.fetch_json = fetch_json
        self.send = send
        self.settings = settings or dict(DEFAULT_SETTINGS)
        self.clock = clock

    # --- persisted state ---

    def _get_state(self, key):
        row = self.con.execute("SELECT value FROM hubstate WHERE key=?", (key,)).fetchone()
        return None if row is None else row[0]

    def _set_state(self, key, value):
        self.con.execute("REPLACE INTO hubstate (key, value) VALUES (?, ?)", (key, value))

    def hub_channel_ids(self):
        rows = self.con.execute("SELECT hubchannel FROM hubchannels WHERE hubchannel IS NOT NULL").fetchall()
        return [row[0] for row in rows]

    # --- change detection ---

    def check_live(self, streams):
        """
        Record the current live status and return the live streams if the
        stream just went live and should be announced, else None.

        The first observation only seeds the state, so deploying or restarting
        the bot mid-stream doesn't announce a stream that's already running.
        """
        now = self.clock()
        live = live_streams(streams)

        previous = self._get_state("live_platforms")
        last_live_at = self._get_state("last_live_at")

        self._set_state("live_platforms", json.dumps([platform for platform, _ in live]))
        if live:
            self._set_state("last_live_at", str(now))
        self.con.commit()

        if previous is None or json.loads(previous) or not live:
            return None

        cooldown = self.settings["live_cooldown"] * 60
        if last_live_at is not None and now - float(last_live_at) < cooldown:
            logger.info("check_live() stream came back within the cooldown, not announcing")
            return None

        return live

    def check_videos(self, videos):
        """
        Record the given videos as seen and return the ones that are new and
        should be announced, oldest first.

        The first observation only seeds the seen list, so the current uploads
        aren't all posted when the feature is first deployed.
        """
        videos = [v for v in (videos or []) if v.get("id")]
        seen = {row[0] for row in self.con.execute("SELECT video_id FROM hubseenvideos")}
        initialized = self._get_state("videos_initialized") is not None

        new = [v for v in videos if v["id"] not in seen]
        self.con.executemany("INSERT OR IGNORE INTO hubseenvideos (video_id) VALUES (?)", [(v["id"],) for v in new])
        self._set_state("videos_initialized", "1")
        self.con.commit()

        if not initialized:
            return []

        max_age = self.settings["video_max_age"] * 3600
        now = self.clock()
        announce = []
        for video in new:
            published = parse_date(video.get("publishDate"))
            if published and now - published.timestamp() > max_age:
                logger.info(f'check_videos() not announcing {video["id"]}, published {published.isoformat()}')
                continue
            announce.append(video)

        # the API lists the most recent upload first
        announce.reverse()
        return announce

    # --- polling ---

    async def poll(self):
        """Fetch the current state and post anything new to every hub channel."""
        messages = []

        stream_info = await self.fetch_json(self.settings["stream_endpoint"])
        streams = _unwrap(stream_info, "streams")
        if streams is not None:
            live = self.check_live(streams)
            if live:
                messages.append(build_live_message(live, self.settings["bigscreen_link"]))
        else:
            logger.warning("poll() unable to get stream info, skipping live check")

        videos = _unwrap(await self.fetch_json(self.settings["videos_endpoint"]))
        if isinstance(videos, list):
            for video in self.check_videos(videos):
                messages.append(build_video_message(video))
        else:
            logger.warning("poll() unable to get videos, skipping video check")

        if not messages:
            return messages

        for channel_id in self.hub_channel_ids():
            for content, embed in messages:
                try:
                    await self.send(channel_id, content, embed)
                except Exception as e:
                    logger.error(f"poll() failed to post to hub channel {channel_id}: {e}")
                    break

        return messages


def _unwrap(response, key=None):
    """Pull the data out of a website JsonResponse ({success, data, ...})."""
    if not isinstance(response, dict) or not response.get("success"):
        return None
    data = response.get("data")
    if key is None:
        return data
    return data.get(key) if isinstance(data, dict) else None
