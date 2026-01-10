"""
Replace syncenabled with syncsettings table.

Creates a table to store per-server sync settings for subscription and username sync.
Migrates existing data from syncenabled table.
"""
name = "Replace syncenabled with syncsettings"


def upgrade(cur, con):
    """Create syncsettings table and migrate data from syncenabled."""
    # Create syncsettings table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS syncsettings (
            discord_server INTEGER PRIMARY KEY,
            sync_subscription INTEGER DEFAULT 0,
            sync_username INTEGER DEFAULT 0
        )
    """)

    # Migrate existing data from syncenabled
    # If sync was enabled, enable subscription sync (preserving existing behavior)
    cur.execute("""
        INSERT INTO syncsettings (discord_server, sync_subscription, sync_username)
        SELECT discord_server, enabled, 0
        FROM syncenabled
        WHERE enabled = 1
    """)

    # Drop old syncenabled table
    cur.execute("DROP INDEX IF EXISTS idx_syncenabled")
    cur.execute("DROP TABLE IF EXISTS syncenabled")

    con.commit()


def downgrade(cur, con):
    """Rollback to syncenabled table."""
    # Recreate syncenabled table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS syncenabled (
            discord_server INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_syncenabled
        ON syncenabled (discord_server)
    """)

    # Migrate data back - if either sync option was enabled, mark as enabled
    cur.execute("""
        INSERT INTO syncenabled (discord_server, enabled)
        SELECT discord_server, CASE WHEN sync_subscription = 1 OR sync_username = 1 THEN 1 ELSE 0 END
        FROM syncsettings
    """)

    # Drop syncsettings table
    cur.execute("DROP TABLE IF EXISTS syncsettings")

    con.commit()
