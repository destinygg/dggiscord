import log
import config
import client
import database

import translator
import sync
import background
import memberstate
import serverstate

import commands

client.bot.run(config.cfg['discord']['token'])
