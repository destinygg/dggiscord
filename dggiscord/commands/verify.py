from helpers.config import cfg
from helpers.log import logging
from subsync.sync import get_profile
import discord.client as client
import disnake

logger = logging.getLogger(__name__)
logger.info("loading...")


def get_verified_role(guild):
    """Find the 'Dgg Verified' role in the guild."""
    for role in guild.roles:
        if role.name == "Dgg Verified":
            return role
    return None


def bot_has_permissions(ctx):
    """Check if the bot has the required permissions to verify users."""
    bot_member = ctx.guild.get_member(client.bot.user.id)
    if bot_member is None:
        return False

    permissions = ctx.channel.permissions_for(bot_member)
    guild_permissions = bot_member.guild_permissions

    # Need manage_nicknames and manage_roles
    return guild_permissions.manage_nicknames and guild_permissions.manage_roles


def can_modify_member(ctx, target_member):
    """Check if the bot can modify the target member's nickname and roles."""
    bot_member = ctx.guild.get_member(client.bot.user.id)
    if bot_member is None:
        return False

    # Can't modify the server owner's nickname
    if target_member.id == ctx.guild.owner_id:
        return False

    # Bot's highest role must be higher than target's highest role
    if bot_member.top_role <= target_member.top_role:
        return False

    return True


@client.bot.command()
async def verify(ctx):
    await ctx.trigger_typing()

    # DM / No Guild
    if ctx.message.guild is None:
        await ctx.reply("{0.message.author.mention} verify is only supported within a server.".format(ctx))
        return

    # Check bot permissions
    if not bot_has_permissions(ctx):
        logger.info(f"verify() bot lacks permissions in guild {ctx.guild.id}")
        return

    # Check if Verified role exists, create if not
    verified_role = get_verified_role(ctx.guild)
    if verified_role is None:
        logger.info(f"verify() 'Dgg Verified' role not found in guild {ctx.guild.id}, creating it")
        try:
            verified_role = await ctx.guild.create_role(name="Dgg Verified")
            logger.info(f"verify() created 'Dgg Verified' role in guild {ctx.guild.id}")
        except disnake.Forbidden:
            logger.warning(f"verify() forbidden to create role in guild {ctx.guild.id}")
            await ctx.reply("{0.message.author.mention} something went wrong, please try again later.".format(ctx))
            return
        except disnake.HTTPException as e:
            logger.error(f"verify() failed to create role in guild {ctx.guild.id}: {e}")
            await ctx.reply("{0.message.author.mention} something went wrong, please try again later.".format(ctx))
            return

    # Check if bot can modify this member
    member = ctx.message.author
    if not can_modify_member(ctx, member):
        logger.info(f"verify() cannot modify member {member.id} in guild {ctx.guild.id} (role hierarchy)")
        return

    # Get DGG profile
    profile = await get_profile(member)

    if profile is None:
        await ctx.reply("{0.message.author.mention} your profile was not found. Link your Discord account at <{1[dgg][links][auth]}> and try again.".format(ctx, cfg))
        return

    dgg_nick = profile.get('nick') or profile.get('username')
    if dgg_nick is None:
        await ctx.reply("{0.message.author.mention} could not retrieve your DGG username.".format(ctx))
        return

    # Update nickname
    try:
        await member.edit(nick=dgg_nick)
        logger.info(f"verify() set nickname for {member.id} to '{dgg_nick}' in guild {ctx.guild.id}")
    except disnake.Forbidden:
        logger.warning(f"verify() forbidden to change nickname for {member.id} in guild {ctx.guild.id}")
        return
    except disnake.HTTPException as e:
        logger.error(f"verify() failed to change nickname for {member.id}: {e}")
        return

    # Add Verified role
    try:
        await member.add_roles(verified_role)
        logger.info(f"verify() added 'Dgg Verified' role to {member.id} in guild {ctx.guild.id}")
    except disnake.Forbidden:
        logger.warning(f"verify() forbidden to add role to {member.id} in guild {ctx.guild.id}")
        return
    except disnake.HTTPException as e:
        logger.error(f"verify() failed to add role to {member.id}: {e}")
        return

    await ctx.reply("{0.message.author.mention} you are now verified as `{1}`.".format(ctx, dgg_nick))
