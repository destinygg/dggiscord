import json
import logging
import os
import sys

logger = logging.getLogger(__name__)
logger.info("Loading {}...".format(__name__))

cfg = {}  # type: dict

# verifies that the config exists, and is valid JSON
def verify_cfg(cfgfile):
    if os.path.isfile(cfgfile) is False:
        logger.critical(f"Unable to find {cfgfile}. Working Dir: {os.getcwd()}")
        return False

    with open(cfgfile, "r") as cfgReadFile:
        try:
            json.load(cfgReadFile)
            return True
        except Exception as e:
            logger.critical("Unable to parse config.json: reason {}".format(e))
            return False

    return False


# loads and validates the config file
def load_config(cfgfile):
    global cfg
    if verify_cfg(cfgfile) is False:
        logger.critical("Unable to load config. verify_cfg() returned False.")
        sys.exit()

    with open(cfgfile, "r") as cfgReadFile:
        cfg.update(json.load(cfgReadFile))
        return True


