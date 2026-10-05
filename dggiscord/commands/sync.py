import logging
import time

import disnake
from disnake.ext import commands

from subsync.sync import add_verified_role
from subsync.rules import target_nick, can_modify_member

logger = logging.getLogger(__name__)
logger.info("loading...")

GUILD_ONLY = disnake.InteractionContextTypes(guild=True)


# https://docs.disnake.dev/en/stable/api/permissions.html#disnake.Permissions
def user_is_privledge(inter, admins):
    # allow bot owner
    if inter.author.id in admins:
        return True

    # allow server owner
    if inter.author.id == inter.guild.owner_id:
        return True

    # allow server admins
    permissions = inter.permissions
    return permissions.administrator or permissions.manage_guild or permissions.manage_channels or permissions.manage_roles


async def deny_unprivileged(inter, admins):
    """Tell the user they can't run a privileged command. Returns True if they were denied."""
    if user_is_privledge(inter, admins):
        return False

    await inter.send("Only server owners and users with Manage Roles, Manage Channels, or Manage Server can use this command.", ephemeral=True)
    return True


async def sync_username(member, profile, guild):
    """Sync the member's Discord nickname to their DGG username. Returns success status and message."""
    dgg_nick = target_nick(profile)
    if dgg_nick is None:
        return False, "Could not retrieve your DGG username."

    # Check if we can modify this member
    if not can_modify_member(guild.me, member, guild.owner_id):
        logger.info(f"sync_username() cannot modify member {member.id} in guild {guild.id} (role hierarchy or owner)")
        return False, "Cannot update your nickname (you may be the server owner or have a higher role than the bot)."

    try:
        await member.edit(nick=dgg_nick)
        logger.info(f"sync_username() set nickname for {member.id} to '{dgg_nick}' in guild {guild.id}")
        # Add verified role after successful username sync
        await add_verified_role(member)
        return True, dgg_nick
    except disnake.Forbidden:
        logger.warning(f"sync_username() forbidden to change nickname for {member.id} in guild {guild.id}")
        return False, "Bot doesn't have permission to change your nickname."
    except disnake.HTTPException as e:
        logger.error(f"sync_username() failed to change nickname for {member.id}: {e}")
        return False, "Failed to update nickname due to an error."


class SyncCommands(commands.Cog):
    def __init__(self, store, member_sync, admins, links):
        """
        Args:
            store: helpers.store.Store
            member_sync: subsync.sync.MemberSync
            admins: user IDs of the bot's owners, who can run privileged commands anywhere
            links: the dgg.links config block
        """
        self.store = store
        self.member_sync = member_sync
        self.admins = admins
        self.links = links

    @commands.slash_command(contexts=GUILD_ONLY)
    async def syncother(
        self, inter, member: disnake.Member = commands.Param(description="The member to sync")
    ):
        """Sync another member's Dgg subscription and username."""
        if await deny_unprivileged(inter, self.admins):
            return

        # Check if sync is disabled for this server
        if not self.store.sync_enabled(inter.guild.id):
            await inter.send("Sync feature is currently disabled for this server.", ephemeral=True)
            return

        # looking up the profile and editing the member can outlast the 3 second response window
        await inter.response.defer()

        settings = self.store.sync_settings(inter.guild.id)

        profile = await self.member_sync.get_profile(member)
        if profile is None:
            await inter.send("{0.mention} your profile was not found. Link your Discord account at <{1[auth]}> and try again.".format(member, self.links))
            return

        results = []

        # Sync subscription if enabled
        if settings["sync_subscription"]:
            await self.member_sync.update_member(member)
            results.append("subscription roles")

        # Sync username if enabled
        if settings["sync_username"]:
            success, result = await sync_username(member, profile, inter.guild)
            if success:
                results.append(f"username to `{result}`")

        if results:
            await inter.send("{0.mention} synced: {1}".format(member, ", ".join(results)))
        else:
            await inter.send("{0.mention} your profile is connected, but no sync options are enabled for this server.".format(member))

    @commands.slash_command(contexts=GUILD_ONLY)
    async def sync(self, inter):
        """Sync your Dgg subscription and username."""
        # Check if sync is disabled for this server
        if not self.store.sync_enabled(inter.guild.id):
            await inter.send("Sync feature is currently disabled for this server.", ephemeral=True)
            return

        # looking up the profile and editing the member can outlast the 3 second response window
        await inter.response.defer()

        profile = await self.member_sync.get_profile(inter.author)

        # no profile
        if profile is None:
            await inter.send("Your profile was not found. Link your Discord account at <{0[auth]}> and try again.".format(self.links))
            return

        settings = self.store.sync_settings(inter.guild.id)
        results = []
        messages = []

        # Sync username if enabled
        if settings["sync_username"]:
            success, result = await sync_username(inter.author, profile, inter.guild)
            if success:
                results.append(f"username synced to `{result}`")
            else:
                messages.append(f"Username sync failed: {result}")

        # Sync subscription if enabled
        if settings["sync_subscription"]:
            # no sub
            if profile['subscription'] is None:
                messages.append("You do not have an (active) subscription. Start one today at <{0[subscribe]}>".format(self.links))
            # twitch sub
            elif profile['subscription']['source'] == "twitch.tv":
                messages.append("You only have a Twitch sub. To use your Twitch sub learn how at <{0[twitchint]}>".format(self.links))
            # dgg sub
            elif profile['subscription']['source'] == "destiny.gg":
                await self.member_sync.update_member(inter.author)

                expires = time.strptime(profile['subscription']['end'], "%Y-%m-%dT%H:%M:%S+0000")
                expires_formatted = time.strftime("%c", expires)

                results.append(f"tier {profile['subscription']['tier']} subscription (expires {expires_formatted} UTC)")

        # Build response
        nick = target_nick(profile) or 'Unknown'
        response_parts = [f"Your profile is connected to `{nick}`."]

        if results:
            response_parts.append("**Synced:** " + ", ".join(results) + ".")

        if messages:
            response_parts.append("\n".join(messages))

        await inter.send(" ".join(response_parts))
