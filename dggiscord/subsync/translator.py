from helpers.config import cfg
from helpers.log import logging
from helpers.http import get_json
from helpers.database import con, cur
from datetime import datetime, timezone
import discord.client as client

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
    flair_json = await get_json(cfg['dgg']['flair']['endpoint'])

    if flair_json is None:
        logger.error("flairs_to_roles() unable to create the map after failing to get {} via API call.".format(cfg['dgg']['flair']['endpoint']))
        return None

    # Build a set of valid flair names from the API that we want to translate
    api_flair_names = {flair['name'] for flair in flair_json}
    translate_flairs = set(cfg['dgg']['flair']['translate'])
    valid_flairs = api_flair_names & translate_flairs  # Intersection of API flairs and config flairs

    # if the flair is one we want to translate to discord set in config.json
    for flair in flair_json:
        if flair['name'] in translate_flairs:
            # see if we have the flair and need to update, or need to create it
            flair_db = get_flair_if_exists(guild.id, flair)
            if flair_db is None:
                await create_new_flair_to_role(guild, flair)
            else:
                await refresh_flair_to_role(guild, flair)

    # Clean up stale flairs that are no longer in the API or no longer in the translate config
    await cleanup_stale_flairs(guild, valid_flairs)

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
        if cfg['dgg']['flair']['resync_properties']:
            logger.info("refresh_flair_to_role() property refresh enabled, attempting sync")

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
            else:
                logger.info("refresh_flair_to_role() flair {0[2]} with ID {0[1]} is ok, no changes required".format(row))
        else:
            logger.info("refresh_flair_to_role() property refresh disabled, skipping sync")

        logger.info("refresh_flair_to_role() refresh completed")
        cur.execute("UPDATE flairmap SET last_refresh=? WHERE discord_role=?", (now, row[1]))
        con.commit()

# remove stale flair mappings from the database when the flair no longer exists in DGG or config
async def cleanup_stale_flairs(guild, valid_flairs):
    """Remove flair mappings from database for flairs that no longer exist in DGG API or translate config.

    Args:
        guild: Discord.Guild object
        valid_flairs: Set of flair names that are currently valid (exist in API and config)
    """
    # Get all flairs currently in the database for this guild
    cur.execute("SELECT discord_role, dgg_flair FROM flairmap WHERE discord_server=?", (guild.id,))
    rows = cur.fetchall()

    stale_entries = []
    for row in rows:
        role_id = row[0]
        flair_name = row[1]

        if flair_name not in valid_flairs:
            stale_entries.append((role_id, flair_name))
            logger.warning(f"cleanup_stale_flairs() flair '{flair_name}' no longer exists in DGG API or translate config, marking for cleanup")

    if not stale_entries:
        logger.debug("cleanup_stale_flairs() no stale flairs found")
        return

    for role_id, flair_name in stale_entries:
        # Check if the Discord role still exists
        role = guild.get_role(role_id)

        # Delete the database entry
        cur.execute("DELETE FROM flairmap WHERE discord_role=?", (role_id,))
        logger.info(f"cleanup_stale_flairs() removed database entry for flair '{flair_name}' (role ID: {role_id})")

        # Optionally delete the Discord role if it still exists
        if role is not None:
            try:
                await role.delete(reason=f"Flair '{flair_name}' no longer exists in DGG")
                logger.info(f"cleanup_stale_flairs() deleted Discord role '{role.name}' (ID: {role_id}) for stale flair '{flair_name}'")
            except Exception as e:
                logger.error(f"cleanup_stale_flairs() failed to delete Discord role {role_id}: {e}")

    con.commit()
    logger.info(f"cleanup_stale_flairs() cleaned up {len(stale_entries)} stale flair(s)")
