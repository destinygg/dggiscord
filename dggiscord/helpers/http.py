from helpers.log import logging
from helpers.config import cfg
import aiohttp

logger = logging.getLogger(__name__)
logger.info(f"Loading {__name__}...")

async def get_json(url):
    logger.info("http.get_json() attempting async URL {0}".format(url))
    try:
        disable_ssl = cfg['dgg']['profile'].get('disable_ssl_verify', False)
        connector = aiohttp.TCPConnector(ssl=False) if disable_ssl else None

        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url) as r:
                logger.info(f"http.get_json() returned HTTP/{r.status}")
                if r.status == 200:
                    if "application/json" in r.headers['Content-Type']:
                        ret = await r.json()
                        return ret
                    else:
                        logger.warn("http.get_json() unable to get JSON from endpoint. Content-Type mismatched {}".format(r.headers['Content-Type']))
                        return None
                else:
                    logger.warn(f"http.get_json() unable to get JSON from endpoint. HTTP code not valid HTTP/{r.status}")
                    return None
    except Exception as e:
        logger.error(f"http.get_json() threw an unknown exception: {e}")
        return None

async def get_dgg_profile(discordid):
    logger.info(f'get_dgg_profile() attempting async URL {cfg["dgg"]["profile"]["user_endpoint"]}')
    url = f'{cfg["dgg"]["profile"]["user_endpoint"]}?privatekey={cfg["dgg"]["profile"]["key"]}&discordid={discordid}'
    profile = await get_json(url)
    return profile

async def get_all_dgg_profiles():
    logger.info(f'get_all_dgg_profiles() attempting async URL {cfg["dgg"]["profile"]["allusers_endpoint"]}')
    url = f'{cfg["dgg"]["profile"]["allusers_endpoint"]}?privatekey={cfg["dgg"]["profile"]["key"]}&auth=discord'
    profiles = await get_json(url)
    return profiles