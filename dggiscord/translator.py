from config import cfg
from log import logging
from common import get_basic_json
from database import con, cur
from datetime import datetime, timezone
import client

logger = logging.getLogger(__name__)
logger.info("loading...")

""" https://cdn.destiny.gg/flairs/flairs.json
{
    label: "Admin",
    name: "admin",
    hidden: true,
    priority: 1,
    color: "#EE1F1F",
    image: [
        {
            url: "https://cdn.destiny.gg/2.7.21/flairs/admin.png",
            name: "admin.png",
            mime: "image/png",
            height: 16,
            width: 16
        }
    ]
},
"""

# get the json from dgg, and map the flair roles to a name and server ID, requires: Discord.Guild object
async def flairs_to_roles(guild):
    flair_json = await get_basic_json(cfg['dgg']['flair']['endpoint'])

    if flair_json is None:
        logger.error("flairs_to_roles() unable to create the map after failing to get {} via API call.".format(cfg['dgg']['flair']['endpoint']))
        return None

    # if the flair is one we want to translate to discord set in config.json
    for flair in flair_json:
        if flair['name'] in cfg['dgg']['flair']['translate']:
            # see if we have the flair and need to update, or need to create it
            flair_db = get_flair_if_exists(guild.id, flair)
            if flair_db is None:
                await create_new_flair_to_role(guild, flair)
            else:
                await refresh_flair_to_role(guild, flair)

# lookup the internal DB if we have roles already, or if we need to make the role
def get_flair_if_exists(guildid, flair):
    cur.execute("SELECT * from flairmap WHERE discord_server=? AND dgg_flair=?", (guildid, flair['name']))
    row = cur.fetchone()

    if row:
        return row
    else:
        return None

# make new roles - https://discordpy.readthedocs.io/en/latest/api.html?highlight=discord%20guild#discord.Guild.create_role
async def create_new_flair_to_role(guild, flair):
    # build the discord.Color object
    if flair['color'] == "":
        color_hex = int("0x000000", 16)
    else:
        color_hex = int(flair['color'].replace("#","0x"), 16)

    color = client.discord.Color(color_hex)

    # make the role
    newrole = await guild.create_role(name=flair['label'], color=color, hoist=True)

    # what time is it, right now (in UTC)
    now = datetime.now(timezone.utc).isoformat()

    # update the database
    cur.execute("INSERT INTO flairmap (discord_server, discord_role, dgg_flair, last_updated, last_refresh) VALUES (?,?,?,?,?)", (guild.id, newrole.id, flair['name'], now, now))
    con.commit()

    logger.info("create_new_flair_to_role() flair {0[name]} created as ID {1.id} on Discord {2.id}".format(flair, guild, newrole))

async def refresh_flair_to_role(guild, flair):
    # get the record
    cur.execute("SELECT * from flairmap WHERE discord_server=? AND dgg_flair=?", (guild.id, flair['name']))
    row = cur.fetchone()

    # what time is it, right now (in UTC)
    now = datetime.now(timezone.utc).isoformat()

    # get the role from the ID the db returned
    role = guild.get_role(row[1]) # 1 = discord_role
    if role is None:
        # if the role disappeared, just delete the record and re-add
        logger.warn("refresh_flair_to_role() flair {0[2]} is supposed to be in DB as ID {0[1]} but does not exist. Removing DB entry and re-adding".format(row))
        cur.execute("DELETE from flairmap WHERE discord_server=? AND dgg_flair=?", (guild.id, flair['name']))
        await create_new_flair_to_role(guild, flair)
    else:
        # we need to make sure the name and color are still matching
        if role.name != flair['label'] or str(role.color) != flair['color'].lower():
            logger.warn("refresh_flair_to_role() flair {0[2]} has been edited, reverting changes to reflect API truth".format(row))

            if flair['color'] == "":
                color_hex = int("0x000000", 16)
            else:
                color_hex = int(flair['color'].replace("#","0x"), 16)
            color = client.discord.Color(color_hex)

            udrole = await role.edit(name=flair['label'], color=color, hoist=True)

            # update the database
            cur.execute("UPDATE flairmap SET last_updated=? WHERE discord_role=?", (now, row[1]))

        logger.info("refresh_flair_to_role() flair {0[2]} with ID {0[1]} is ok, no changes required".format(row))
        cur.execute("UPDATE flairmap SET last_refresh=? WHERE discord_role=?", (now, row[1]))
        con.commit()
