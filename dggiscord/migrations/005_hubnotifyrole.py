"""
Add a notify role to hub channels.

When a server sets a notify role, it's mentioned in every hub notification.
"""
name = "Add hub notify role"


def upgrade(cur, con):
    """Add the notifyrole column to hubchannels."""
    cur.execute("ALTER TABLE hubchannels ADD COLUMN notifyrole INTEGER")

    con.commit()


def downgrade(cur, con):
    """Drop the notifyrole column from hubchannels."""
    cur.execute("ALTER TABLE hubchannels DROP COLUMN notifyrole")

    con.commit()
