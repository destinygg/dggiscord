import json
import logging
import os
import sys
import argparse

logger = logging.getLogger(__name__)
logger.info("Loading {}...".format(__name__))

parser = argparse.ArgumentParser(description="dggiscord, a DGG utility.")
parser.add_argument("--config", type=str, default="cfg/config.json")
args = parser.parse_args()

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


# starts the bot from the config file:
def start_from_cfg(cfgfile):
    global cfg
    if verify_cfg(cfgfile) is False:
        logger.critical("Unable to start bot. verify_cfg() returned False.")
        sys.exit()

    with open(cfgfile, "r") as cfgReadFile:
        cfg = json.load(cfgReadFile)
        return True


start_from_cfg(args.config)
