from helpers.config import cfg
from helpers.log import logging
from helpers.database import cur
from subsync.sync import update_member, get_profile
import discord.client as client
import disnake
import time

logger = logging.getLogger(__name__)
logger.info("loading...")


def get_sync_settings(guild_id):
    """Get sync settings for a guild. Returns dict with sync_subscription and sync_username."""
    cur.execute("SELECT sync_subscription, sync_username FROM syncsettings WHERE discord_server=?", (guild_id,))
    row = cur.fetchone()
    if row is None:
        return {"sync_subscription": False, "sync_username": False}
    return {"sync_subscription": bool(row[0]), "sync_username": bool(row[1])}


def is_any_sync_enabled(guild_id):
    """Check if any sync option is enabled for a guild."""
    settings = get_sync_settings(guild_id)
    return settings["sync_subscription"] or settings["sync_username"]


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


def can_modify_member(guild, target_member):
    """Check if the bot can modify the target member's nickname."""
    bot_member = guild.get_member(client.bot.user.id)
    if bot_member is None:
        return False

    # Can't modify the server owner's nickname
    if target_member.id == guild.owner_id:
        return False

    # Bot's highest role must be higher than target's highest role
    if bot_member.top_role <= target_member.top_role:
        return False

    return True


async def sync_username(member, profile, guild):
    """Sync the member's Discord nickname to their DGG username. Returns success status and message."""
    dgg_nick = profile.get('nick') or profile.get('username')
    if dgg_nick is None:
        return False, "Could not retrieve your DGG username."

    # Check if we can modify this member
    if not can_modify_member(guild, member):
        logger.info(f"sync_username() cannot modify member {member.id} in guild {guild.id} (role hierarchy or owner)")
        return False, "Cannot update your nickname (you may be the server owner or have a higher role than the bot)."

    try:
        await member.edit(nick=dgg_nick)
        logger.info(f"sync_username() set nickname for {member.id} to '{dgg_nick}' in guild {guild.id}")
        return True, dgg_nick
    except disnake.Forbidden:
        logger.warning(f"sync_username() forbidden to change nickname for {member.id} in guild {guild.id}")
        return False, "Bot doesn't have permission to change your nickname."
    except disnake.HTTPException as e:
        logger.error(f"sync_username() failed to change nickname for {member.id}: {e}")
        return False, "Failed to update nickname due to an error."


@client.bot.command()
async def syncother(ctx):
    if user_is_privledge(ctx) is False:
        return

    # Check if sync is disabled for this server
    if not is_any_sync_enabled(ctx.message.guild.id):
        await ctx.reply("Sync feature is currently disabled for this server.")
        return

    if ctx.message.mentions is None:
        await ctx.reply("{0.message.author.mention} mention the users you wish to sync. Multiple mentions/users supported.".format(ctx, cfg))
        return

    settings = get_sync_settings(ctx.message.guild.id)

    for member in ctx.message.mentions:
        profile = await get_profile(member)
        if profile is None:
            await ctx.reply("{0.mention} your profile was not found. Link your Discord account at <{1[dgg][links][auth]}> and try again.".format(member, cfg))
        else:
            results = []

            # Sync subscription if enabled
            if settings["sync_subscription"]:
                await update_member(member)
                results.append("subscription roles")

            # Sync username if enabled
            if settings["sync_username"]:
                success, result = await sync_username(member, profile, ctx.message.guild)
                if success:
                    results.append(f"username to `{result}`")

            if results:
                await ctx.reply("{0.mention} synced: {1}".format(member, ", ".join(results)))
            else:
                await ctx.reply("{0.mention} your profile is connected, but no sync options are enabled for this server.".format(member))


@client.bot.command(aliases=['sub','dgg','postcringelosesub'])
async def sync(ctx):
    await ctx.trigger_typing()

    # DM / No Guild
    if ctx.message.guild is None:
        await ctx.reply("{0.message.author.mention} sync is only supported within a server, sorry :(".format(ctx))
        return

    # Check if sync is disabled for this server
    if not is_any_sync_enabled(ctx.message.guild.id):
        await ctx.reply("{0.message.author.mention} sync feature is currently disabled for this server.".format(ctx))
        return

    profile = await get_profile(ctx.message.author)

    # no profile
    if profile is None:
        await ctx.reply("{0.message.author.mention} your profile was not found. Link your Discord account at <{1[dgg][links][auth]}> and try again.".format(ctx, cfg))
        return

    settings = get_sync_settings(ctx.message.guild.id)
    results = []
    messages = []

    # Sync username if enabled
    if settings["sync_username"]:
        success, result = await sync_username(ctx.message.author, profile, ctx.message.guild)
        if success:
            results.append(f"username synced to `{result}`")
        else:
            messages.append(f"Username sync failed: {result}")

    # Sync subscription if enabled
    if settings["sync_subscription"]:
        # no sub
        if profile['subscription'] is None:
            messages.append("You do not have an (active) subscription. Start one today at <{0[dgg][links][subscribe]}>".format(cfg))
        # twitch sub
        elif profile['subscription']['source'] == "twitch.tv":
            messages.append("You only have a Twitch sub. To use your Twitch sub learn how at <{0[dgg][links][twitchint]}>".format(cfg))
        # dgg sub
        elif profile['subscription']['source'] == "destiny.gg":
            await update_member(ctx.message.author)

            expires = time.strptime(profile['subscription']['end'], "%Y-%m-%dT%H:%M:%S+0000")
            expires_formatted = time.strftime("%c", expires)

            results.append(f"tier {profile['subscription']['tier']} subscription (expires {expires_formatted} UTC)")

    # Build response
    nick = profile.get('nick') or profile.get('username') or 'Unknown'
    response_parts = [f"{ctx.message.author.mention} your profile is connected to `{nick}`."]

    if results:
        response_parts.append("**Synced:** " + ", ".join(results) + ".")

    if messages:
        response_parts.append("\n".join(messages))

    await ctx.reply(" ".join(response_parts))
