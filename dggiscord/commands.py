from config import cfg
from log import logging
from sync import update_member, get_profile
import client

logger = logging.getLogger(__name__)
logger.info("loading...")

# https://discordpy.readthedocs.io/en/latest/api.html?highlight=discord%20guild#discord.Permissions
def user_is_privledge(ctx):
    # allow bot owner
    if ctx.message.author.id in cfg['discord']['admins']:
        return True

    # allow server owner
    if ctx.message.author.id == ctx.message.guild.owner.id:
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
async def sync(ctx):

    # get the users profile, see if their account is tied
    profile = await get_profile(ctx.message.author)
    if profile is None:
        await ctx.send("{0.message.author.mention} your profile was not found. Link your Discord account at <{1[dgg][links][auth]}> and try again.".format(ctx, cfg))
    else:
        await update_member(ctx.message.author)
        await ctx.send("{0.message.author.mention} your profile is connected! Visit <{1[dgg][links][profile]}> to manage your subscriptions.".format(ctx, cfg))

@client.bot.command()
async def syncother(ctx):
    if user_is_privledge(ctx) is False:
        return

    if ctx.message.mentions is None:
        await ctx.send("{0.message.author.mention} mention the users you wish to sync. Multiple mentions/users supported.".format(ctx, cfg))
        return

    for member in ctx.message.mentions:
        profile = await get_profile(member)
        if profile is None:
            await ctx.send("{0.mention} your profile was not found. Link your Discord account at <{1[dgg][links][auth]}> and try again.".format(member, cfg))
        else:
            await update_member(member)
            await ctx.send("{0.mention} your profile is connected! Visit <{1[dgg][links][profile]}> to manage your subscriptions.".format(member, cfg))
