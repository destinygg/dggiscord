import argparse

import helpers.log
import helpers.config as config

# Parse args and load config before importing modules that depend on it
parser = argparse.ArgumentParser(description="dggiscord, a DGG utility.")
parser.add_argument("--config", type=str, default="cfg/config.json")
args = parser.parse_args()
config.start_from_cfg(args.config)

import helpers.database
import discord.client as client

import subsync.translator
import subsync.sync
import discord.background
import discord.memberstate
import discord.serverstate

import commands.sync
import commands.livestatuscfg

client.bot.run(config.cfg['discord']['token'])
