from config import cfg
from log import logging
from sync import update_member
import client

logger = logging.getLogger(__name__)
logger.info("loading...")

# auto assign roles to new joining members who already have the authentication in place
@client.bot.event
async def on_member_join(member):
    logger.info("on_member_join() new member ID:{} joined".format(member.id))
    await update_member(member)
