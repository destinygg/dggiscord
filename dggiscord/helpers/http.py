"""
HTTP access to the destiny.gg APIs.

Neither get_json nor DggApi depends on the config, so both can be tested
directly; helpers.dgg builds the configured instances the bot uses.
"""
import logging

import aiohttp

logger = logging.getLogger(__name__)
logger.info(f"Loading {__name__}...")


async def get_json(url, params=None, verify_ssl=True):
    """
    GET a URL and return the parsed JSON, or None on any failure.

    Query parameters go in params rather than the URL so secrets in them,
    like the profile API key, aren't logged.
    """
    logger.info(f"http.get_json() attempting async URL {url}")
    try:
        connector = None if verify_ssl else aiohttp.TCPConnector(ssl=False)

        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url, params=params) as r:
                logger.info(f"http.get_json() returned HTTP/{r.status}")
                if r.status != 200:
                    logger.warning(f"http.get_json() unable to get JSON from endpoint. HTTP code not valid HTTP/{r.status}")
                    return None

                content_type = r.headers.get('Content-Type', '')
                if "application/json" not in content_type:
                    logger.warning(f"http.get_json() unable to get JSON from endpoint. Content-Type mismatched {content_type}")
                    return None

                return await r.json()
    except Exception as e:
        logger.error(f"http.get_json() threw an unknown exception: {e}")
        return None


class DggApi:
    def __init__(self, fetch_json, key, user_endpoint, allusers_endpoint, flair_endpoint):
        """
        Args:
            fetch_json: async function(url, params) -> parsed JSON or None on failure
            key: private key for the profile endpoints
            user_endpoint: single profile lookup by Discord ID
            allusers_endpoint: every account with a linked auth provider
            flair_endpoint: the public flairs.json
        """
        self.fetch_json = fetch_json
        self.key = key
        self.user_endpoint = user_endpoint
        self.allusers_endpoint = allusers_endpoint
        self.flair_endpoint = flair_endpoint

    @classmethod
    def from_config(cls, cfg, fetch_json):
        profile = cfg['dgg']['profile']
        return cls(fetch_json, profile['key'], profile['user_endpoint'], profile['allusers_endpoint'], cfg['dgg']['flair']['endpoint'])

    async def profile(self, discord_id):
        """The DGG profile linked to a Discord user, or None."""
        return await self.fetch_json(self.user_endpoint, {"privatekey": self.key, "discordid": str(discord_id)})

    async def all_profiles(self):
        """Every DGG account with Discord linked, as the raw API response, or None."""
        return await self.fetch_json(self.allusers_endpoint, {"privatekey": self.key, "auth": "discord"})

    async def flairs(self):
        """The list of flair definitions, or None."""
        return await self.fetch_json(self.flair_endpoint, None)
