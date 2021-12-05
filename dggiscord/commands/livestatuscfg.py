from helpers.log import logging
from helpers.database import con, cur
import discord.client as client

logger = logging.getLogger(__name__)
logger.info("loading...")

@client.bot.command()
async def hubchannel(ctx, arg):
    # only let server admins determine this
    permissions = ctx.message.channel.permissions_for(ctx.message.author)
    if not permissions.administrator:
        return

    if arg == "get":
        cur.execute("SELECT * from hubchannels WHERE discord_server=?", (ctx.message.guild.id,))
        row = cur.fetchone()

        logger.info(f'hubchannel get response from db {row}')
        await ctx.reply(f'Current hub channel is set to <#{row[1]}>')
    elif arg == "set":
        cur.execute("REPLACE INTO hubchannels VALUES(?,?)", (ctx.message.guild.id, ctx.message.channel.id))
        con.commit()
        await ctx.reply(f'Channel set to <#{ctx.message.channel.id}>')
    else:
        await ctx.reply('Error: Command args `set|get`.')