import logging

import disnake
from disnake.ext import commands

from hub.notifier import _unwrap, build_video_message, live_streams
from hub.status import build_host_status, build_live_status, build_offline_status, build_vods_message, latest_video

logger = logging.getLogger(__name__)
logger.info("loading...")

GUILD_ONLY = disnake.InteractionContextTypes(guild=True)
UNAVAILABLE = "Couldn't get stream info from destiny.gg, try again later."


class StreamInfo(commands.Cog):
    """Commands that show the stream status, latest video and VODs from the website."""

    def __init__(self, fetch_json, settings):
        """
        Args:
            fetch_json: async function(url) -> parsed JSON or None on failure
            settings: dict as returned by hub.notifier.load_settings()
        """
        self.fetch_json = fetch_json
        self.settings = settings

    @commands.slash_command(contexts=GUILD_ONLY)
    async def live(self, inter):
        """Show whether Destiny is live, or what destiny.gg is hosting."""
        await inter.response.defer()
        bigscreen_link = self.settings["bigscreen_link"]

        streams = _unwrap(await self.fetch_json(self.settings["stream_endpoint"]), "streams")
        if not isinstance(streams, dict):
            await inter.send(UNAVAILABLE)
            return

        live = live_streams(streams)
        if live:
            await inter.send(embed=build_live_status(live, bigscreen_link))
            return

        # a failed hosting lookup shouldn't stop us from saying the stream is offline
        host = _unwrap(await self.fetch_json(self.settings["hosting_endpoint"]))
        if isinstance(host, dict):
            await inter.send(embed=build_host_status(host, bigscreen_link))
        else:
            await inter.send(embed=build_offline_status(streams, bigscreen_link))

    @commands.slash_command(contexts=GUILD_ONLY)
    async def youtube(self, inter):
        """Show Destiny's latest YouTube video."""
        await inter.response.defer()
        videos = _unwrap(await self.fetch_json(self.settings["videos_endpoint"]))
        if not isinstance(videos, list):
            await inter.send(UNAVAILABLE)
            return

        video = latest_video(videos)
        if video is None:
            await inter.send("There are no videos to show.")
            return
        _, embed = build_video_message(video)
        await inter.send(embed=embed)

    @commands.slash_command(contexts=GUILD_ONLY)
    async def vods(self, inter):
        """Show Destiny's latest stream VODs."""
        await inter.response.defer()
        vods = _unwrap(await self.fetch_json(self.settings["vods_endpoint"]))
        if not isinstance(vods, list):
            await inter.send(UNAVAILABLE)
            return

        embed = build_vods_message(vods, self.settings["bigscreen_link"])
        if embed is None:
            await inter.send("There are no VODs to show.")
            return
        await inter.send(embed=embed)
