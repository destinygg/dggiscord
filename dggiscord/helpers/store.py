"""
Database access for sync settings, flair mappings and hub channel settings.

Store wraps a sqlite3 connection with the migrations applied and has no config
or bot dependency, so it can be tested against a throwaway database. Every
write commits immediately.
"""

SYNC_COLUMNS = ("sync_subscription", "sync_username")


class Store:
    def __init__(self, con):
        self.con = con

    # --- sync settings ---

    def sync_settings(self, guild_id):
        """Return {"sync_subscription": bool, "sync_username": bool}; both False if never set."""
        row = self.con.execute("SELECT sync_subscription, sync_username FROM syncsettings WHERE discord_server=?", (guild_id,)).fetchone()
        if row is None:
            return {"sync_subscription": False, "sync_username": False}
        return {"sync_subscription": bool(row[0]), "sync_username": bool(row[1])}

    def sync_enabled(self, guild_id):
        """True if any sync option is enabled for the guild."""
        settings = self.sync_settings(guild_id)
        return settings["sync_subscription"] or settings["sync_username"]

    def set_sync_settings(self, guild_id, sync_subscription=None, sync_username=None):
        """Set the given sync options, leaving any passed as None unchanged (disabled if new)."""
        values = {"sync_subscription": sync_subscription, "sync_username": sync_username}
        changed = [column for column in SYNC_COLUMNS if values[column] is not None]
        if not changed:
            return

        # the column names come from SYNC_COLUMNS, never from input
        updates = ", ".join(f"{column} = excluded.{column}" for column in changed)
        self.con.execute(f"""
            INSERT INTO syncsettings (discord_server, sync_subscription, sync_username)
            VALUES (?, ?, ?)
            ON CONFLICT(discord_server) DO UPDATE SET {updates}
        """, (guild_id, int(bool(sync_subscription)), int(bool(sync_username))))
        self.con.commit()

    # --- flair to role mappings ---

    def flair_mappings(self, guild_id):
        """Return the guild's (role_id, flair_name) mappings."""
        return self.con.execute("SELECT discord_role, dgg_flair FROM flairmap WHERE discord_server=?", (guild_id,)).fetchall()

    def flair_role(self, guild_id, flair_name):
        """Return the role ID mapped to a flair in the guild, or None."""
        row = self.con.execute("SELECT discord_role FROM flairmap WHERE discord_server=? AND dgg_flair=?", (guild_id, flair_name)).fetchone()
        return None if row is None else row[0]

    def add_flair_role(self, guild_id, role_id, flair_name, now):
        self.con.execute(
            "INSERT INTO flairmap (discord_server, discord_role, dgg_flair, last_updated, last_refresh) VALUES (?,?,?,?,?)",
            (guild_id, role_id, flair_name, now, now),
        )
        self.con.commit()

    def mark_flair_refreshed(self, role_id, now, updated=False):
        """Record a refresh of a flair's role, and an update if its properties were reverted."""
        if updated:
            self.con.execute("UPDATE flairmap SET last_updated=?, last_refresh=? WHERE discord_role=?", (now, now, role_id))
        else:
            self.con.execute("UPDATE flairmap SET last_refresh=? WHERE discord_role=?", (now, role_id))
        self.con.commit()

    def delete_flair_role(self, role_id):
        self.con.execute("DELETE FROM flairmap WHERE discord_role=?", (role_id,))
        self.con.commit()

    # --- hub channel settings ---

    def hub_channel(self, guild_id):
        """Return the guild's hub channel ID, or None."""
        row = self.con.execute("SELECT hubchannel FROM hubchannels WHERE discord_server=?", (guild_id,)).fetchone()
        return None if row is None else row[0]

    def set_hub_channel(self, guild_id, channel_id):
        """Set or clear (None) the hub channel, keeping the notify role."""
        self.con.execute("""
            INSERT INTO hubchannels (discord_server, hubchannel) VALUES (?, ?)
            ON CONFLICT(discord_server) DO UPDATE SET hubchannel = excluded.hubchannel
        """, (guild_id, channel_id))
        self.con.commit()

    def hub_notify_role(self, guild_id):
        """Return the role ID hub posts mention, or None."""
        row = self.con.execute("SELECT notifyrole FROM hubchannels WHERE discord_server=?", (guild_id,)).fetchone()
        return None if row is None else row[0]

    def set_hub_notify_role(self, guild_id, role_id):
        """Set or clear (None) the notify role, keeping the hub channel."""
        self.con.execute("""
            INSERT INTO hubchannels (discord_server, notifyrole) VALUES (?, ?)
            ON CONFLICT(discord_server) DO UPDATE SET notifyrole = excluded.notifyrole
        """, (guild_id, role_id))
        self.con.commit()
