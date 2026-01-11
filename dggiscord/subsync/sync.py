from helpers.config import cfg
from helpers.log import logging
from helpers.http import get_dgg_profile, get_all_dgg_profiles
from helpers.database import con, cur
import discord.client as client
import disnake

logger = logging.getLogger(__name__)
logger.info("loading...")

""" https://www.destiny.gg/api/info/profile?privatekey=xxx&discordid=252869311545212928
{
    nick: "Cake",
    username: "Cake",
    userId: "30157",
    status: "Active",
    createdDate: "2014-01-05T01:55:37+0000",
    roles: [
        "USER",
        "ADMIN",
        "MODERATOR",
        "EMOTES",
        "FLAIRS"
    ],
    features: [
        "protected",
        "moderator",
        "flair5",
        "flair8"
    ],
    subscription: {
        tier: "4",
        source: "destiny.gg",
        type: "1-MONTH-SUB4",
        start: "2018-04-27T22:20:16+0000",
        end: "2019-08-28T22:20:16+0000"
    }
}
"""

# build a map of the server flair -> role mappings, requires: Discord.Guild
# filters out stale mappings where the Discord role no longer exists
def flair_map(server):
    flairmap = {}
    stale_roles = []
    cur.execute("SELECT * from flairmap WHERE discord_server=?", (server.id,))
    rows = cur.fetchall()

    for row in rows:
        role_id = row[1]
        flair_name = row[2]
        # Check if the role still exists in Discord
        if server.get_role(role_id) is not None:
            flairmap.update({role_id: flair_name})
        else:
            logger.warning(f"flair_map() role ID:{role_id} for flair '{flair_name}' no longer exists in guild {server.id}, excluding from map")
            stale_roles.append(role_id)

    # Clean up stale database entries
    if stale_roles:
        for role_id in stale_roles:
            cur.execute("DELETE FROM flairmap WHERE discord_role=?", (role_id,))
        con.commit()
        logger.info(f"flair_map() cleaned up {len(stale_roles)} stale flair mapping(s) from database")

    return flairmap

# build a map of the role ID -> provider flair, requires: Discord.Guild
def role_map(server):
    fmap = flair_map(server)
    rmap = {value: key for key, value in fmap.items()}
    return rmap

# get the user's account as it stands on DGG, requires: Discord.Member
async def get_profile(member):
    profile = await get_dgg_profile(member.id)
    return profile

# remove a role, requies: role(ID), Discord.Member
async def remove_role(role, member):
    role_obj = member.guild.get_role(role)
    if role_obj is None:
        logger.warning(f"remove_role() role ID:{role} no longer exists in guild {member.guild.id}, skipping")
        return False
    await member.remove_roles(role_obj)
    return True

# add a role, requies: role(ID), Discord.Member
async def add_role(role, member):
    role_obj = member.guild.get_role(role)
    if role_obj is None:
        logger.warning(f"add_role() role ID:{role} no longer exists in guild {member.guild.id}, skipping")
        return False
    await member.add_roles(role_obj)
    return True

# add the "Dgg Verified" role to a member if they don't already have it
async def add_verified_role(member):
    """Add the 'Dgg Verified' role to a member. Creates the role if it doesn't exist. Returns True if role was added, False otherwise."""
    verified_role = disnake.utils.get(member.guild.roles, name="Dgg Verified")

    # Create the role if it doesn't exist
    if verified_role is None:
        try:
            verified_role = await member.guild.create_role(
                name="Dgg Verified",
                color=disnake.Color.green(),
                reason="Auto-created by DGG sync bot for verified users"
            )
            logger.info(f"add_verified_role() created 'Dgg Verified' role in guild {member.guild.id}")
        except disnake.Forbidden:
            logger.warning(f"add_verified_role() forbidden to create role in guild {member.guild.id}")
            return False
        except disnake.HTTPException as e:
            logger.error(f"add_verified_role() failed to create role in guild {member.guild.id}: {e}")
            return False

    if already_has_role(verified_role.id, member):
        logger.debug(f"add_verified_role() member {member.id} already has 'Dgg Verified' role")
        return True

    try:
        await add_role(verified_role.id, member)
        logger.info(f"add_verified_role() added 'Dgg Verified' role to member {member.id} in guild {member.guild.id}")
        return True
    except disnake.Forbidden:
        logger.warning(f"add_verified_role() forbidden to add role to member {member.id} in guild {member.guild.id}")
        return False
    except disnake.HTTPException as e:
        logger.error(f"add_verified_role() failed to add role to member {member.id}: {e}")
        return False

# return true if the user already has the role, required: role(ID), Discord.Member
def already_has_role(roleid, member):
    for role in member.roles:
        if role.id == int(roleid):
            return True

    return False

# checks the roles applied vs what the API has, requires get_profile(), Discord.Member, flair_map()
async def remove_user_roles(profile, member, flairmap):
    # build a list of the discord role IDs
    rolelist = []
    for role in member.roles:
        rolelist.append(role.id)

    # intersect against the flairmap keys
    inter = list(set(rolelist) & set(flairmap.keys()))

    # if we intersect, check if we can have the role
    if inter:
        for role in inter:
            # handle users who have roles but not a liked account:
            if profile is None:
                logger.info("remove_user_roles() removing role ID:{0} to member ID:{1.id} server ID:{1.guild.id} (NO SYNC)".format(role, member))
                await remove_role(role, member)
                continue

            # if the user does not have a valid lookup, remove the role
            flair = flairmap[role] # I am sure this blind lookup will never be a problem in the future
            if flair in profile['features']:
                logger.debug("remove_user_roles() role is not up for removal on member ID:{0.id} server ID:{0.guild.id}".format(member))
            else:
                logger.info("remove_user_roles() removing role ID:{0} to member ID:{1.id} server ID:{1.guild.id}".format(role, member))
                await remove_role(role, member)

# checks and assigns the role to a user if the user does not already have the role, requires: profile(json), Discord.Member, role_map()
async def add_user_roles(profile, member, rolemap):
    for feature in profile['features']:
        if feature in rolemap:
            if not already_has_role(rolemap[feature], member):
                logger.info("add_user_roles() applying role ID:{0} to member ID:{1.id} on server ID:{1.guild.id}".format(rolemap[feature], member))
                await add_role(rolemap[feature], member)

# the 1 line abstraction to call to update a user throughout the bot, requires: Discord.Member, optional: flair_map() and role_map()
async def update_member(member, fmap=None, rmap=None, dgg_index=None):
    if fmap is None:
        fmap = flair_map(member.guild)
    if rmap is None:
        rmap = role_map(member.guild)

    # poll DGG for the user if we don't have the subscriber index
    if dgg_index is None:
        logger.info(f'update_member() looking up {member.id} directly against API')
        api = await get_profile(member)
    else:
    # return api result if in index, if not signal None and move on
        try:
            api = dgg_index[member.id]
            logger.info(f'update_member() {member.id} found in subscriber index')
        except KeyError:
            api = None

    if api is not None:
        await add_user_roles(api, member, rmap)
    await remove_user_roles(api, member, fmap)

# get all accounts with discord from dgg, index the data and return a k/v store by Discord ID
async def get_all_members_indexed():
    members = await get_all_dgg_profiles()

    if members['status'] != "success":
        logger.error(f'get_all_members_indexed() API responded with unparsable result {members}')
        return
    else:
        logger.info(f'get_all_members_indexed() got API result with {len(members["data"])} accounts')

    index = {}

    for member in members['data']:
        # only index active accounts
        if member['status'] != "Active":
            continue

        # cast to an int, because disnake considers User.ID uint64 against Discord recommendation lol!
        snowflake = int(member['authId'])
        index[snowflake] = member

        # pack the dict to match /api/info/profile response if dggSub exists
        if member['dggSub'] is not None:
            index[snowflake]['subscription'] = index[snowflake]['dggSub']

    logger.info(f'get_all_members_indexed() Index completed with {len(index)} accounts')

    return index


def can_modify_member_nickname(guild, target_member):
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


# update member's username to match DGG profile, requires: Discord.Member, optional: dgg_index
async def update_member_username(member, dgg_index=None):
    # Get profile from index or API
    if dgg_index is None:
        logger.info(f'update_member_username() looking up {member.id} directly against API')
        api = await get_profile(member)
    else:
        try:
            api = dgg_index[member.id]
            logger.debug(f'update_member_username() {member.id} found in index')
        except KeyError:
            api = None

    if api is None:
        return

    dgg_nick = api.get('nick') or api.get('username')
    if dgg_nick is None:
        return

    # Check if we can modify this member
    if not can_modify_member_nickname(member.guild, member):
        logger.debug(f"update_member_username() cannot modify member {member.id} in guild {member.guild.id}")
        return

    # Skip if nickname already matches
    if member.nick == dgg_nick:
        logger.debug(f"update_member_username() {member.id} nickname already matches '{dgg_nick}'")
        return

    try:
        await member.edit(nick=dgg_nick)
        logger.info(f"update_member_username() set nickname for {member.id} to '{dgg_nick}' in guild {member.guild.id}")
        await add_verified_role(member)
    except disnake.Forbidden:
        logger.warning(f"update_member_username() forbidden to change nickname for {member.id} in guild {member.guild.id}")
    except disnake.HTTPException as e:
        logger.error(f"update_member_username() failed to change nickname for {member.id}: {e}")