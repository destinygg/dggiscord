"""
Add state tables for hub channel notifications.

hubstate is a key/value store for the last observed live status, so a restart
doesn't re-announce a stream that's already been announced. hubseenvideos
records every video ID that has been seen, so a video that drops out of the
recent uploads list and comes back isn't announced twice.
"""
name = "Add hub notification state"


def upgrade(cur, con):
    """Create hubstate and hubseenvideos tables."""
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

    con.commit()


def downgrade(cur, con):
    """Drop hubstate and hubseenvideos tables."""
    cur.execute("DROP TABLE IF EXISTS hubseenvideos")
    cur.execute("DROP TABLE IF EXISTS hubstate")

    con.commit()
