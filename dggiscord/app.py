import argparse
import logging
import os
import time
from functools import partial

from helpers.config import load_config
from helpers.database import open_db
from helpers.http import DggApi, get_json
from helpers.store import Store
from hub.notifier import load_settings
from subsync.sync import MemberSync
from subsync.translator import FlairTranslator
from discord.client import create_bot, Presence
from discord.background import BackgroundSync
from discord.memberstate import MemberState
from discord.serverstate import ServerState
from discord.hubnotify import HubNotify
from commands.sync import SyncCommands
from commands.syncsettings import SyncSettings
from commands.livestatuscfg import HubSettings
from commands.streaminfo import StreamInfo
from commands.debug import Debug


def build_bot(cfg, con):
    """Create the bot with every cog wired to the config and database connection."""
    store = Store(con)

    # every request honors disable_ssl_verify, not just the profile endpoints it's configured under
    fetch_json = partial(get_json, verify_ssl=not cfg['dgg']['profile'].get('disable_ssl_verify', False))
    api = DggApi.from_config(cfg, fetch_json)

    member_sync = MemberSync(store, api)
    translator = FlairTranslator(store, api, cfg['dgg']['flair']['translate'], cfg['dgg']['flair']['resync_properties'])
    admins = cfg['discord']['admins']
    hub_settings = load_settings(cfg)

    bot = create_bot()
    bot.add_cog(Presence(bot, cfg['discord']['nowplaying']))
    bot.add_cog(BackgroundSync(bot, store, member_sync, translator, cfg['discord']['background_refresh_rate']))
    bot.add_cog(MemberState(member_sync))
    bot.add_cog(ServerState(translator))
    bot.add_cog(HubNotify(bot, con, fetch_json, hub_settings))
    bot.add_cog(SyncCommands(store, member_sync, admins, cfg['dgg']['links']))
    bot.add_cog(SyncSettings(store, admins))
    bot.add_cog(HubSettings(store))
    bot.add_cog(StreamInfo(fetch_json, hub_settings))
    # set from the release tag when the Docker image is built
    bot.add_cog(Debug(admins, time.time(), os.environ.get('DGGISCORD_VERSION', 'dev')))
    return bot


def main():
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="dggiscord, a DGG utility.")
    parser.add_argument("--config", type=str, default="cfg/config.json")
    args = parser.parse_args()

    cfg = load_config(args.config)
    bot = build_bot(cfg, open_db(cfg['db']))
    bot.run(cfg['discord']['token'])


if __name__ == "__main__":
    main()
