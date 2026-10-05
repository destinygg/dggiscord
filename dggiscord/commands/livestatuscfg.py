from helpers.log import logging
from helpers.database import con, cur
import discord.client as client

logger = logging.getLogger(__name__)
logger.info("loading...")

@client.bot.command()
async def hubchannel(ctx, arg=None):
    # only let server admins determine this
    permissions = ctx.message.channel.permissions_for(ctx.message.author)
    if not permissions.administrator:
        return

    if arg == "get":
        cur.execute("SELECT * from hubchannels WHERE discord_server=?", (ctx.message.guild.id,))
        row = cur.fetchone()

        logger.info(f'hubchannel get response from db {row}')
        if row is None or row[1] is None:
            await ctx.reply('No hub channel is set. Use `hubchannel set` in the channel that should receive notifications.')
        else:
            await ctx.reply(f'Current hub channel is set to <#{row[1]}>')
    elif arg == "set":
        cur.execute("REPLACE INTO hubchannels VALUES(?,?)", (ctx.message.guild.id, ctx.message.channel.id))
        con.commit()
        await ctx.reply(f'Channel set to <#{ctx.message.channel.id}>. Stream and new video notifications will be posted here.')
    elif arg == "unset":
        cur.execute("DELETE FROM hubchannels WHERE discord_server=?", (ctx.message.guild.id,))
        con.commit()
        await ctx.reply('Hub channel removed. Notifications will no longer be posted.')
    else:
        await ctx.reply('Error: Command args `set|get|unset`.')
