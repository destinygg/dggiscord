"""
Add syncenabled table.

Creates a table to store per-server sync enabled/disabled state.
Defaults to disabled (0) for all servers.
"""
name = "Add syncenabled table"


def upgrade(cur, con):
    """Create syncenabled table."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS syncenabled (
            discord_server INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0
        )
    """)

    # Create index on syncenabled
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_syncenabled
        ON syncenabled (discord_server)
    """)

    con.commit()


def downgrade(cur, con):
    """Rollback syncenabled table."""
    cur.execute("DROP INDEX IF EXISTS idx_syncenabled")
    cur.execute("DROP TABLE IF EXISTS syncenabled")

    con.commit()
