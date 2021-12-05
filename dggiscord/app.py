import helpers.log
import helpers.config as config
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
