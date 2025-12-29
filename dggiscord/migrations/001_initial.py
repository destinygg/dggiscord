"""
Initial database schema migration.

Creates the initial tables: flairmap and hubchannels.
"""
name = "Initial schema"


def upgrade(cur, con):
    """Create initial database schema."""
    # Create flairmap table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS flairmap (
            discord_server INTEGER,
            discord_role INTEGER,
            dgg_flair TEXT,
            last_updated TEXT,
            last_refresh TEXT,
            PRIMARY KEY(discord_role)
        )
    """)

    # Create hubchannels table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hubchannels (
            discord_server INTEGER PRIMARY KEY,
            hubchannel INTEGER
        )
    """)

    # Create index on hubchannels
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_hubchannels
        ON hubchannels (discord_server)
    """)

    con.commit()


def downgrade(cur, con):
    """Rollback initial database schema."""
    # Drop index
    cur.execute("DROP INDEX IF EXISTS idx_hubchannels")
    
    # Drop tables
    cur.execute("DROP TABLE IF EXISTS hubchannels")
    cur.execute("DROP TABLE IF EXISTS flairmap")
    
    con.commit()

