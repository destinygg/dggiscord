import logging
import sqlite3
import sys

from helpers.migrator import Migrator

logger = logging.getLogger(__name__)
logger.info("loading...")


def open_db(path):
    """Connect to the sqlite database, running any pending migrations first."""
    try:
        Migrator(path).upgrade()
    except Exception as e:
        logger.error(f"Failed to run database migrations: {e}")
        logger.warning("Continuing with existing database schema...")

    try:
        con = sqlite3.connect(path)
        logger.info("sqlite database connection successfully initialized")
        return con
    except Exception as e:
        logger.critical("sqlite database failed with error: {0}".format(e))
        sys.exit(1)
