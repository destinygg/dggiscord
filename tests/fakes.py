"""
Minimal stand-ins for the disnake objects and services the bot's cogs use.

They implement only the attributes and calls the code under test touches, and
record what was changed so tests can assert on it.
"""
import os
import sqlite3
import tempfile
from itertools import count

import disnake

from helpers.migrator import Migrator
from helpers.store import Store

_ids = count(10_000)


class FakeRole:
    def __init__(self, guild, name, role_id=None, color=None, position=1):
        self.guild = guild
        self.id = role_id if role_id is not None else next(_ids)
        self.name = name
        self.color = color if color is not None else disnake.Color(0)
        self.position = position
        self.deleted = False

    # Member.top_role comparisons, as on disnake.Role
    def __lt__(self, other):
        return self.position < other.position

    def __le__(self, other):
        return self.position <= other.position

    def __gt__(self, other):
        return self.position > other.position

    def __ge__(self, other):
        return self.position >= other.position

    async def edit(self, name=None, color=None, hoist=None):
        if name is not None:
            self.name = name
        if color is not None:
            self.color = color

    async def delete(self, reason=None):
        if self.guild.fail_role_deletes:
            raise disnake.HTTPException(FakeResponse(500), "delete failed")
        self.deleted = True
        self.guild.roles.remove(self)


class FakeResponse:
    def __init__(self, status):
        self.status = status
        self.reason = "fake"


class FakeMember:
    def __init__(self, guild, member_id=None, roles=(), nick=None, top_position=0):
        self.guild = guild
        self.id = member_id if member_id is not None else next(_ids)
        self.roles = list(roles)
        self.nick = nick
        self.top_role = FakeRole(guild, "top", position=top_position)
        self.mention = f"<@{self.id}>"
        guild.members.append(self)

    async def add_roles(self, *roles):
        self.roles.extend(roles)

    async def remove_roles(self, *roles):
        for role in roles:
            self.roles.remove(role)

    async def edit(self, nick=None):
        self.nick = nick

    def role_ids(self):
        return {role.id for role in self.roles}


class FakeGuild:
    def __init__(self, guild_id=None, name="Test Server", owner_id=1, bot_position=100):
        self.id = guild_id if guild_id is not None else next(_ids)
        self.name = name
        self.owner_id = owner_id
        self.roles = []
        self.members = []
        self.fail_role_deletes = False
        # roles that exist on Discord but are missing from the client's cache
        self.uncached_roles = []
        self.me = FakeMember(self, top_position=bot_position)

    def add_role(self, name, role_id=None, color=None):
        role = FakeRole(self, name, role_id, color)
        self.roles.append(role)
        return role

    def get_role(self, role_id):
        return next((role for role in self.roles if role.id == role_id), None)

    async def fetch_roles(self):
        return self.roles + self.uncached_roles

    async def create_role(self, name, color=None, hoist=False, reason=None):
        return self.add_role(name, color=color)


class FakeApi:
    def __init__(self, profiles=None, flairs=None, all_profiles=None):
        self.profiles = profiles or {}
        self.flair_list = flairs
        self.all_profiles_response = all_profiles
        self.flair_endpoint = "https://cdn.dgg.test/flairs/flairs.json"

    async def profile(self, discord_id):
        return self.profiles.get(discord_id)

    async def all_profiles(self):
        return self.all_profiles_response

    async def flairs(self):
        return self.flair_list


class FakeContext:
    def __init__(self, guild, author, mentions=(), administrator=False):
        self.replies = []
        channel_permissions = disnake.Permissions(administrator=administrator)
        self.message = type("FakeMessage", (), {})()
        self.message.guild = guild
        self.message.author = author
        self.message.mentions = list(mentions)
        self.message.channel = type("FakeChannel", (), {"id": 555, "permissions_for": lambda _, member: channel_permissions})()

    async def reply(self, content):
        self.replies.append(content)

    async def trigger_typing(self):
        pass


def migrated_store(test):
    """Create a Store on a throwaway migrated database, cleaned up with the test."""
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    test.addCleanup(os.remove, path)
    Migrator(path).upgrade()
    con = sqlite3.connect(path)
    test.addCleanup(con.close)
    return Store(con)
