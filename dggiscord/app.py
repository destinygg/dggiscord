import log
import config
import client
import database

import translator
import sync
import background

import commands

client.bot.run(config.cfg['discord']['token'])
