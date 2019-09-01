from config import cfg
from log import logging
import aiohttp

logger = logging.getLogger(__name__)
logger.info("loading...")

async def get_basic_json(url):
    logger.info("get_basic_json() attempting async URL {0}".format(url))
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                logger.info("get_basic_json() returned HTTP/{}".format(r.status))
                if r.status == 200:
                    if "application/json" in r.headers['Content-Type']:
                        ret = await r.json()
                        return ret
                    else:
                        logger.warn("get_basic_json() unable to get JSON from endpoint. Content-Type mismatched {}".format(r.headers['Content-Type']))
                        return None
                else:
                    logger.warn("get_basic_json() unable to get JSON from endpoint. HTTP code not valid HTTP/{}".format(r.status))
                    return None
    except Exception as e:
        logger.error("get_basic_json() threw an unknown exception: {0}".format(e))
        return None

async def get_profile_api(discordid):
    logger.debug("get_basic_json() attempting async URL {0}".format(cfg['dgg']['profile']['endpoint']))
    url = "{0[dgg][profile][endpoint]}?privatekey={0[dgg][profile][key]}&discordid={1}".format(cfg, discordid)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                logger.debug("get_basic_json() returned HTTP/{}".format(r.status))
                if r.status == 200:
                    if "application/json" in r.headers['Content-Type']:
                        ret = await r.json()
                        return ret
                    else:
                        logger.warn("get_basic_json() unable to get JSON from endpoint. Content-Type mismatched {}".format(r.headers['Content-Type']))
                        return None
                else:
                    logger.debug("get_basic_json() unable to get JSON from endpoint. HTTP code not valid HTTP/{}".format(r.status))
                    return None
    except Exception as e:
        logger.error("get_basic_json() threw an unknown exception: {0}".format(e))
        return None
