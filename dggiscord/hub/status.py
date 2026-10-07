"""
Builds the embeds for the /live, /youtube and /vods commands.

Like the notifier's builders, these are pure functions of the website's
broadcast info, so they can be tested without a bot.
"""
from urllib.parse import urljoin

import disnake

from hub.notifier import EMBED_COLOR, PLATFORM_NAMES, build_live_message, parse_date, platform_url

OFFLINE_COLOR = 0xFF0000

# how many older VODs /vods lists under the latest one
MORE_VODS = 3


def platform_name(platform):
    return PLATFORM_NAMES.get(platform, (platform or "").capitalize())


def timestamp(value, style="f"):
    """Format an ISO date as a Discord timestamp, or None if it can't be parsed."""
    date = parse_date(value)
    return f"<t:{int(date.timestamp())}:{style}>" if date else None


def format_duration(seconds):
    """Format a number of seconds as e.g. "3h 25m", or "1m" for anything shorter."""
    minutes = max(int(seconds) // 60, 1)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts = [f"{days}d" if days else "", f"{hours}h" if hours else "", f"{minutes}m" if minutes else ""]
    return " ".join(part for part in parts if part)


def build_live_status(live, bigscreen_link):
    """Build the /live embed for a live stream, from the live_streams() entries."""
    _, embed = build_live_message(live, bigscreen_link)

    viewers = [(platform, s["viewers"]) for platform, s in live if isinstance(s.get("viewers"), int)]
    if viewers:
        total = sum(count for _, count in viewers)
        counts = " · ".join(f"{platform_name(platform)} {count:,}" for platform, count in viewers)
        embed.add_field(name="Viewers", value=f"**{total:,}** ({counts})", inline=True)

    starts = [date for date in (parse_date(s.get("started_at")) for _, s in live) if date]
    if starts:
        embed.add_field(name="Started", value=f"<t:{int(min(starts).timestamp())}:R>", inline=True)

    return embed


def build_host_status(host, bigscreen_link):
    """Build the /live embed for when destiny.gg is hosting another stream."""
    name = host.get("displayName") or "Another stream"
    watch = [f"[Bigscreen]({bigscreen_link})"]
    if host.get("url"):
        watch.append(f"[{platform_name(host.get('platform')) or 'Stream'}]({host['url']})")

    embed = disnake.Embed(
        title=f'"{name}" is being hosted on destiny.gg',
        url=bigscreen_link,
        description="Watch on " + " or ".join(watch),
        color=EMBED_COLOR,
    )
    embed.set_author(name="Destiny is offline")
    if host.get("preview"):
        embed.set_image(url=host["preview"])
    return embed


def build_offline_status(streams, bigscreen_link):
    """Build the /live embed for when the stream is offline, from an /api/info/stream map."""
    embed = disnake.Embed(title="Destiny is offline", url=bigscreen_link, color=OFFLINE_COLOR)

    # describe the platform that ended most recently
    ended = [s for s in (streams or {}).values() if s and parse_date(s.get("ended_at"))]
    if ended:
        last = max(ended, key=lambda s: parse_date(s["ended_at"]))
        description = f"Last live {timestamp(last['ended_at'], 'R')}"
        started = parse_date(last.get("started_at"))
        if started:
            description += f" for {format_duration((parse_date(last['ended_at']) - started).total_seconds())}"
        if last.get("status_text"):
            description += f"\n> {last['status_text']}"
        embed.description = description

    return embed


def latest_video(videos):
    """Return the most recently published video, or None if there are none."""
    if not videos:
        return None
    dated = [video for video in videos if parse_date(video.get("publishDate"))]
    if not dated:
        return videos[0]
    return max(dated, key=lambda video: parse_date(video["publishDate"]))


def vod_links(vod, bigscreen_link):
    """Describe a VOD as its start time and watch links."""
    links = []
    if vod.get("url"):
        links.append(f"[{platform_name(vod.get('platform')) or 'Watch'}]({vod['url']})")
    if vod.get("embedUrl"):
        links.append(f"[Bigscreen]({urljoin(bigscreen_link, vod['embedUrl'])})")

    started = timestamp(vod.get("streamStartTime"))
    parts = [f"Started {started}"] if started else []
    if links:
        parts.append("Watch on " + ", ".join(links))
    return " · ".join(parts) or "No links available"


def build_vods_message(vods, bigscreen_link):
    """Build the /vods embed for the latest VOD and a few before it, or None if there are none."""
    if not vods:
        return None

    # the API lists the most recent stream first
    latest, older = vods[0], vods[1:1 + MORE_VODS]
    embed = disnake.Embed(
        title=latest.get("title") or "Latest VOD",
        url=latest.get("url") or None,
        description=vod_links(latest, bigscreen_link),
        color=EMBED_COLOR,
    )
    embed.set_author(name="Latest VOD")

    thumbnail = latest.get("highThumbnailUrl") or latest.get("mediumThumbnailUrl")
    if thumbnail:
        embed.set_image(url=thumbnail)

    for vod in older:
        embed.add_field(name=vod.get("title") or "Untitled", value=vod_links(vod, bigscreen_link), inline=False)
    return embed
