import logging

import disnake
from disnake.ext import commands

logger = logging.getLogger(__name__)
logger.info("loading...")

ADMIN_ONLY = disnake.Permissions(administrator=True)
GUILD_ONLY = disnake.InteractionContextTypes(guild=True)
HUB_PERMISSIONS = [
    ("view_channel", "View Channel"),
    ("send_messages", "Send Messages"),
    ("embed_links", "Embed Links"),
]


async def is_admin(inter):
    # only let server admins determine this; default_member_permissions hides the commands
    # from everyone else, but a server can override that in its integration settings
    if inter.permissions.administrator:
        return True

    await inter.send('Error: Only server admins can use this command.', ephemeral=True)
    return False


class HubSettings(commands.Cog):
    def __init__(self, store):
        """
        Args:
            store: helpers.store.Store
        """
        self.store = store

    @commands.slash_command(default_member_permissions=ADMIN_ONLY, contexts=GUILD_ONLY)
    async def hubchannel(self, inter):
        """Set, show, or remove the channel that receives hub notifications."""

    @hubchannel.sub_command(name="get")
    async def hubchannel_get(self, inter):
        """Show the hub channel."""
        if not await is_admin(inter):
            return

        channel_id = self.store.hub_channel(inter.guild.id)

        logger.info(f'hubchannel get response from db {channel_id}')
        if channel_id is None:
            await inter.send('No hub channel is set. Use `/hubchannel set` to choose the channel that should receive notifications.')
        else:
            await inter.send(f'Current hub channel is set to <#{channel_id}>')

    @hubchannel.sub_command(name="set")
    async def hubchannel_set(
        self, inter, channel: disnake.TextChannel = commands.Param(description="The channel to post notifications in")
    ):
        """Choose the hub channel for stream and new video notifications."""
        if not await is_admin(inter):
            return

        # notifications are posted with embeds, so the bot needs all three
        permissions = channel.permissions_for(inter.guild.me)
        missing = [f'*{label}*' for name, label in HUB_PERMISSIONS if not getattr(permissions, name)]
        if missing:
            await inter.send(f'Error: The bot needs {", ".join(missing)} in <#{channel.id}> to post notifications there.', ephemeral=True)
            return

        self.store.set_hub_channel(inter.guild.id, channel.id)
        await inter.send(f'Channel set to <#{channel.id}>. Stream and new video notifications will be posted there.')

    @hubchannel.sub_command(name="unset")
    async def hubchannel_unset(self, inter):
        """Remove the hub channel and stop posting notifications."""
        if not await is_admin(inter):
            return

        self.store.set_hub_channel(inter.guild.id, None)
        await inter.send('Hub channel removed. Notifications will no longer be posted.')

    @commands.slash_command(default_member_permissions=ADMIN_ONLY, contexts=GUILD_ONLY)
    async def hubrole(self, inter):
        """Set, show, or remove the role mentioned in hub notifications."""

    @hubrole.sub_command(name="get")
    async def hubrole_get(self, inter):
        """Show the role mentioned in hub notifications."""
        if not await is_admin(inter):
            return

        role_id = self.store.hub_notify_role(inter.guild.id)

        logger.info(f'hubrole get response from db {role_id}')
        if role_id is None:
            await inter.send('No notify role is set.')
        else:
            # describe the role by name so replying doesn't ping it
            notify_role = inter.guild.get_role(role_id)
            name = f'**{notify_role.name}**' if notify_role else f'a deleted role ({role_id})'
            await inter.send(f'Hub notifications mention {name}.')

    @hubrole.sub_command(name="set")
    async def hubrole_set(
        self, inter, role: disnake.Role = commands.Param(description="The role to mention in hub notifications")
    ):
        """Mention a role in every hub notification."""
        if not await is_admin(inter):
            return

        if role.is_default():
            await inter.send('Error: @everyone can\'t be used as the notify role.', ephemeral=True)
            return

        self.store.set_hub_notify_role(inter.guild.id, role.id)
        logger.info(f'hubrole set to {role.id} for server {inter.guild.id}')

        reply = f'Hub notifications will mention **{role.name}**.'
        if not role.mentionable and not inter.guild.me.guild_permissions.mention_everyone:
            reply += ('\nThis role isn\'t mentionable and the bot doesn\'t have the *Mention @everyone, @here, and All Roles* '
                      'permission, so the mention won\'t notify anyone. Make the role mentionable or give the bot that permission.')
        await inter.send(reply)

    @hubrole.sub_command(name="unset")
    async def hubrole_unset(self, inter):
        """Stop mentioning a role in hub notifications."""
        if not await is_admin(inter):
            return

        self.store.set_hub_notify_role(inter.guild.id, None)
        await inter.send('Notify role removed. Hub notifications will no longer mention a role.')
