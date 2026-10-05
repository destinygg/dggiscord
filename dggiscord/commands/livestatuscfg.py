from helpers.log import logging
from helpers.database import con, cur
import discord.client as client
from disnake.ext import commands

logger = logging.getLogger(__name__)
logger.info("loading...")

@client.bot.command()
async def hubchannel(ctx, arg=None):
    # only let server admins determine this
    permissions = ctx.message.channel.permissions_for(ctx.message.author)
    if not permissions.administrator:
        return

    if arg == "get":
        cur.execute("SELECT hubchannel FROM hubchannels WHERE discord_server=?", (ctx.message.guild.id,))
        row = cur.fetchone()

        logger.info(f'hubchannel get response from db {row}')
        if row is None or row[0] is None:
            await ctx.reply('No hub channel is set. Use `hubchannel set` in the channel that should receive notifications.')
        else:
            await ctx.reply(f'Current hub channel is set to <#{row[0]}>')
    elif arg == "set":
        # update only the channel so the server's notify role is kept
        cur.execute("""
            INSERT INTO hubchannels (discord_server, hubchannel) VALUES (?, ?)
            ON CONFLICT(discord_server) DO UPDATE SET hubchannel = excluded.hubchannel
        """, (ctx.message.guild.id, ctx.message.channel.id))
        con.commit()
        await ctx.reply(f'Channel set to <#{ctx.message.channel.id}>. Stream and new video notifications will be posted here.')
    elif arg == "unset":
        cur.execute("UPDATE hubchannels SET hubchannel = NULL WHERE discord_server=?", (ctx.message.guild.id,))
        con.commit()
        await ctx.reply('Hub channel removed. Notifications will no longer be posted.')
    else:
        await ctx.reply('Error: Command args `set|get|unset`.')


@client.bot.command()
async def hubrole(ctx, arg=None, *, role=None):
    # only let server admins determine this
    permissions = ctx.message.channel.permissions_for(ctx.message.author)
    if not permissions.administrator:
        return

    if arg == "get":
        cur.execute("SELECT notifyrole FROM hubchannels WHERE discord_server=?", (ctx.message.guild.id,))
        row = cur.fetchone()

        logger.info(f'hubrole get response from db {row}')
        if row is None or row[0] is None:
            await ctx.reply('No notify role is set.')
        else:
            # describe the role by name so replying doesn't ping it
            notify_role = ctx.message.guild.get_role(row[0])
            name = f'**{notify_role.name}**' if notify_role else f'a deleted role ({row[0]})'
            await ctx.reply(f'Hub notifications mention {name}.')
    elif arg == "set":
        if role is None:
            await ctx.reply('Error: Specify a role by name, ID, or mention, e.g. `hubrole set Notifications`.')
            return

        try:
            notify_role = await commands.RoleConverter().convert(ctx, role)
        except commands.RoleNotFound:
            await ctx.reply(f'Error: No role named `{role}` was found.')
            return

        if notify_role.is_default():
            await ctx.reply('Error: @everyone can\'t be used as the notify role.')
            return

        cur.execute("""
            INSERT INTO hubchannels (discord_server, notifyrole) VALUES (?, ?)
            ON CONFLICT(discord_server) DO UPDATE SET notifyrole = excluded.notifyrole
        """, (ctx.message.guild.id, notify_role.id))
        con.commit()
        logger.info(f'hubrole set to {notify_role.id} for server {ctx.message.guild.id}')

        reply = f'Hub notifications will mention **{notify_role.name}**.'
        if not notify_role.mentionable and not ctx.message.guild.me.guild_permissions.mention_everyone:
            reply += ('\nThis role isn\'t mentionable and the bot doesn\'t have the *Mention @everyone, @here, and All Roles* '
                      'permission, so the mention won\'t notify anyone. Make the role mentionable or give the bot that permission.')
        await ctx.reply(reply)
    elif arg == "unset":
        cur.execute("UPDATE hubchannels SET notifyrole = NULL WHERE discord_server=?", (ctx.message.guild.id,))
        con.commit()
        await ctx.reply('Notify role removed. Hub notifications will no longer mention a role.')
    else:
        await ctx.reply('Error: Command args `set <role>|get|unset`.')
