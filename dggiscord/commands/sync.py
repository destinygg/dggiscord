from config import cfg
from log import logging
from sync import update_member, get_profile
from common import get_profile_api
import client
import time

logger = logging.getLogger(__name__)
logger.info("loading...")

# https://discordpy.readthedocs.io/en/latest/api.html?highlight=discord%20guild#discord.Permissions
def user_is_privledge(ctx):
    # allow bot owner
    if ctx.message.author.id in cfg['discord']['admins']:
        return True

    # allow server owner
    if ctx.message.author.id == ctx.message.guild.owner_id:
        return True

    # allow server admins
    permissions = ctx.message.channel.permissions_for(ctx.message.author)
    if permissions.administrator:
        return True
    elif permissions.manage_guild:
        return True
    elif permissions.manage_channels:
        return True
    elif permissions.manage_roles:
        return True
    else:
        return False

    return False

@client.bot.command()
async def syncother(ctx):
    if user_is_privledge(ctx) is False:
        return

    if ctx.message.mentions is None:
        await ctx.reply("{0.message.author.mention} mention the users you wish to sync. Multiple mentions/users supported.".format(ctx, cfg))
        return

    for member in ctx.message.mentions:
        profile = await get_profile(member)
        if profile is None:
            await ctx.reply("{0.mention} your profile was not found. Link your Discord account at <{1[dgg][links][auth]}> and try again.".format(member, cfg))
        else:
            await update_member(member)
            await ctx.reply("{0.mention} your profile is connected! Visit <{1[dgg][links][profile]}> or use !sync to manage your subscriptions.".format(member, cfg))

@client.bot.command(aliases=['sub','dgg','postcringelosesub'])
async def sync(ctx):
    await ctx.trigger_typing()

    profile = await get_profile(ctx.message.author)
    # DM / No Guild
    if ctx.message.guild is None:
        await ctx.reply("{0.message.author.mention} sync is only supported in within a server, sorry :(".format(ctx))
        return

    # no profile
    if profile is None:
        await ctx.reply("{0.message.author.mention} your profile was not found. Link your Discord account at <{1[dgg][links][auth]}> and try again.".format(ctx, cfg))
        return

    # no sub
    if profile['subscription'] is None:
        await ctx.reply("{0.message.author.mention} your profile is connected to `{1[nick]}`, but you do not have an (active) subscription :( Start one today at <{2[dgg][links][subscribe]}>".format(ctx, profile, cfg))
        return

    # twitch sub
    if profile['subscription']['source'] == "twitch.tv":
        await ctx.reply("{0.message.author.mention} your profile is connected to `{1[nick]}`, but you only have a Twitch sub. To use your Twitch sub learn how at <{2[dgg][links][twitchint]}>".format(ctx, profile, cfg))
        return

    # dgg sub
    if profile['subscription']['source'] == "destiny.gg":
        await update_member(ctx.message.author)

        expires = time.strptime(profile['subscription']['end'], "%Y-%m-%dT%H:%M:%S+0000")
        expires_formatted = time.strftime("%c", expires)

        await ctx.reply("{0.message.author.mention} your profile is connected to `{1[nick]}`, and your tier {1[subscription][tier]} subscription expires at {2} (UTC)".format(ctx, profile, expires_formatted))
