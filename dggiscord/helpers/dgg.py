from functools import partial

from helpers.config import cfg
from helpers.http import DggApi, get_json

# every request honors disable_ssl_verify, not just the profile endpoints it's configured under
fetch_json = partial(get_json, verify_ssl=not cfg['dgg']['profile'].get('disable_ssl_verify', False))

api = DggApi.from_config(cfg, fetch_json)
