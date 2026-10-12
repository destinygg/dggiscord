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

# the hub events a notify role can be set for, with how replies name them
HUB_EVENTS = {
    "live": "Go-live",
    "video": "New video",
}
EVENT_CHOICES = {
    "Both": "all",
    "Going live": "live",
    "New videos": "video",
}


def selected_events(event):
    """Return the hub events an event option ("all", "live" or "video") covers, or None if it isn't one."""
    if event == "all":
        return list(HUB_EVENTS)
    return [event] if event in HUB_EVENTS else None


async def deny_unknown_event(inter, events):
    # Discord only sends the listed choices, but check rather than fail on a lookup
    if events is not None:
        return False

    await inter.send('Error: The event must be one of: Both, Going live, New videos.', ephemeral=True)
    return True


def describe_events(events):
    return " and ".join(HUB_EVENTS[e] if i == 0 else HUB_EVENTS[e].lower() for i, e in enumerate(events))


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
        """Set, show, or remove the roles mentioned in hub notifications."""

    @hubrole.sub_command(name="get")
    async def hubrole_get(self, inter):
        """Show the roles mentioned in hub notifications."""
        if not await is_admin(inter):
            return

        role_ids = {event: self.store.hub_role(inter.guild.id, event) for event in HUB_EVENTS}

        logger.info(f'hubrole get response from db {role_ids}')
        if not any(role_ids.values()):
            await inter.send('No notify role is set.')
            return

        lines = []
        for event, label in HUB_EVENTS.items():
            role_id = role_ids[event]
            if role_id is None:
                name = 'no role'
            else:
                # describe the role by name so replying doesn't ping it
                notify_role = inter.guild.get_role(role_id)
                name = f'**{notify_role.name}**' if notify_role else f'a deleted role ({role_id})'
            lines.append(f'{label} notifications mention {name}.')
        await inter.send('\n'.join(lines))

    @hubrole.sub_command(name="set")
    async def hubrole_set(
        self,
        inter,
        role: disnake.Role = commands.Param(description="The role to mention in hub notifications"),
        event: str = commands.Param("all", choices=EVENT_CHOICES, description="Which notifications mention the role; defaults to both"),
    ):
        """Mention a role in go-live notifications, new video notifications, or both."""
        if not await is_admin(inter):
            return

        if role.is_default():
            await inter.send('Error: @everyone can\'t be used as the notify role.', ephemeral=True)
            return

        events = selected_events(event)
        if await deny_unknown_event(inter, events):
            return

        for e in events:
            self.store.set_hub_role(inter.guild.id, e, role.id)
        logger.info(f'hubrole set to {role.id} for {events} in server {inter.guild.id}')

        reply = f'{describe_events(events)} notifications will mention **{role.name}**.'
        if not role.mentionable and not inter.guild.me.guild_permissions.mention_everyone:
            reply += ('\nThis role isn\'t mentionable and the bot doesn\'t have the *Mention @everyone, @here, and All Roles* '
                      'permission, so the mention won\'t notify anyone. Make the role mentionable or give the bot that permission.')
        await inter.send(reply)

    @hubrole.sub_command(name="unset")
    async def hubrole_unset(
        self,
        inter,
        event: str = commands.Param("all", choices=EVENT_CHOICES, description="Which notifications stop mentioning a role; defaults to both"),
    ):
        """Stop mentioning a role in go-live notifications, new video notifications, or both."""
        if not await is_admin(inter):
            return

        events = selected_events(event)
        if await deny_unknown_event(inter, events):
            return

        for e in events:
            self.store.set_hub_role(inter.guild.id, e, None)
        await inter.send(f'Notify role removed. {describe_events(events)} notifications will no longer mention a role.')
