from helpers.config import cfg
from helpers.log import logging
from helpers.migrator import Migrator
from helpers.store import Store
import sqlite3

logger = logging.getLogger(__name__)
logger.info("loading...")

try:
    con = sqlite3.connect(cfg['db'])
    logger.info("sqlite database connection successfully initialized")
except Exception as e:
    logger.critical("sqlite database failed with error: {0}".format(e))
    exit()

# Run database migrations on startup
try:
    migrator = Migrator(cfg['db'])
    migrator.upgrade()
except Exception as e:
    logger.error(f"Failed to run database migrations: {e}")
    logger.warning("Continuing with existing database schema...")

store = Store(con)
