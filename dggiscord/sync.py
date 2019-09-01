from config import cfg
from log import logging
from common import get_profile_api
from database import con, cur
import client

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
def flair_map(server):
    flairmap = {}
    cur.execute("SELECT * from flairmap WHERE discord_server=?", (server.id,))
    rows = cur.fetchall()

    for row in rows:
        flairmap.update({row[1]:row[2]})

    return flairmap

# build a map of the role ID -> provider flair, requires: Discord.Guild
def role_map(server):
    fmap = flair_map(server)
    rmap = {value: key for key, value in fmap.items()}
    return rmap

# get the user's account as it stands on DGG, requires: Discord.Member
async def get_profile(member):
    profile = await get_profile_api(member.id)
    return profile

# remove a role, requies: role(ID), Discord.Member
async def remove_role(role, member):
    role_obj = member.guild.get_role(role)
    await member.remove_roles(role_obj)

# add a role, requies: role(ID), Discord.Member
async def add_role(role, member):
    role_obj = member.guild.get_role(role)
    await member.add_roles(role_obj)

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
async def update_member(member, fmap=None, rmap=None):
    if fmap is None:
        fmap = flair_map(member.guild)
    if rmap is None:
        rmap = role_map(member.guild)

    api = await get_profile(member)
    if api is not None:
        await add_user_roles(api, member, rmap)
    await remove_user_roles(api, member, fmap)
