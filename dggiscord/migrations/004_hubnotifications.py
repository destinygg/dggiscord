"""
Add state tables for hub channel notifications.

hubstate is a key/value store for the last observed live status, so a restart
doesn't re-announce a stream that's already been announced. hubseenvideos
records every video ID that has been seen, so a video that drops out of the
recent uploads list and comes back isn't announced twice. hublivemessages
holds the go-live announcement posted in each hub channel, so it can be edited
when another platform goes live.
"""
name = "Add hub notification state"


def upgrade(cur, con):
    """Create hubstate, hubseenvideos and hublivemessages tables."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hubstate (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS hubseenvideos (
            video_id TEXT PRIMARY KEY,
            seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS hublivemessages (
            channel_id INTEGER PRIMARY KEY,
            message_id INTEGER NOT NULL
        )
    """)

    con.commit()


def downgrade(cur, con):
    """Drop hubstate, hubseenvideos and hublivemessages tables."""
    cur.execute("DROP TABLE IF EXISTS hublivemessages")
    cur.execute("DROP TABLE IF EXISTS hubseenvideos")
    cur.execute("DROP TABLE IF EXISTS hubstate")

    con.commit()
