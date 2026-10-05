import logging

from disnake.ext import commands

logger = logging.getLogger(__name__)
logger.info("loading...")


class MemberState(commands.Cog):
    def __init__(self, member_sync):
        self.member_sync = member_sync

    # auto assign roles to new joining members who already have the authentication in place
    @commands.Cog.listener()
    async def on_member_join(self, member):
        logger.info("on_member_join() new member ID:{} joined".format(member.id))
        await self.member_sync.update_member(member)
