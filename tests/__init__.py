import os
import sys

# the bot's modules import each other as top-level packages (helpers, hub, ...)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dggiscord"))
