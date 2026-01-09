from helpers.log import logging
from helpers.database import con, cur
import discord.client as client

logger = logging.getLogger(__name__)
logger.info("loading...")

@client.bot.command()
async def syncenabled(ctx, arg="get"):
    # only let server admins determine this
    permissions = ctx.message.channel.permissions_for(ctx.message.author)
    if not permissions.administrator:
        return

    if arg == "get":
        cur.execute("SELECT enabled FROM syncenabled WHERE discord_server=?", (ctx.message.guild.id,))
        row = cur.fetchone()

        if row is None:
            # Default to disabled if not set
            enabled = False
        else:
            enabled = bool(row[0])

        status = "enabled" if enabled else "disabled"
        logger.info(f'syncenabled get response from db {row}, status: {status}')
        await ctx.reply(f'Sync feature is currently **{status}** for this server')
    elif arg == "enable":
        cur.execute("REPLACE INTO syncenabled VALUES(?,?)", (ctx.message.guild.id, 1))
        con.commit()
        logger.info(f'syncenabled enabled for server {ctx.message.guild.id}')
        await ctx.reply('Sync feature has been **enabled** for this server')
    elif arg == "disable":
        cur.execute("REPLACE INTO syncenabled VALUES(?,?)", (ctx.message.guild.id, 0))
        con.commit()
        logger.info(f'syncenabled disabled for server {ctx.message.guild.id}')
        await ctx.reply('Sync feature has been **disabled** for this server')
    else:
        await ctx.reply('Error: Command args `get|enable|disable`.')
