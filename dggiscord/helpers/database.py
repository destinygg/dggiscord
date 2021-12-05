from helpers.config import cfg
from helpers.log import logging
import sqlite3

logger = logging.getLogger(__name__)
logger.info("loading...")

try:
    con = sqlite3.connect(cfg['db'])
    cur = con.cursor()
    logger.info("sqlite database connection and cursor successfully initialized")
except Exception as e:
    logger.critical("sqlite database failed with error: {0}".format(e))
    exit()

# Check if the table exists, if not make the schema
cur.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='flairmap'")
if cur.fetchone()[0] == 0:
    logger.warn("table 'flairmap' does not exist in database, creating schema...")
    cur.execute("CREATE TABLE 'flairmap' ( `discord_server` INTEGER, `discord_role` INTEGER, `dgg_flair` TEXT, `last_updated` TEXT, `last_refresh` TEXT, PRIMARY KEY(`discord_role`) )")

# hubchannel configs
cur.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='hubchannels'")
if cur.fetchone()[0] == 0:
    logger.warn("table 'hubchannels' does not exist in database, creating schema...")
    cur.execute("CREATE TABLE 'hubchannels' ( `discord_server` INTEGER PRIMARY KEY, `hubchannel` INTEGER )")
    cur.execute("CREATE UNIQUE INDEX idx_hubchannels ON hubchannels (discord_server)")
