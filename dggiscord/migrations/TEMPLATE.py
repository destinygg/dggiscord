"""
Migration template.

To create a new migration:
1. Copy this file to a new file named: XXX_description.py
   where XXX is the next sequential number (e.g., 002_add_user_table.py)
2. Update the 'name' variable with a descriptive name
3. Implement the 'upgrade' function with your schema changes
4. Optionally implement a 'downgrade' function for rollback
"""
name = "Migration description"


def upgrade(cur, con):
    """
    Apply this migration.

    Args:
        cur: SQLite cursor
        con: SQLite connection
    """
    # Example: Add a new table
    # cur.execute("""
    #     CREATE TABLE IF NOT EXISTS new_table (
    #         id INTEGER PRIMARY KEY,
    #         name TEXT NOT NULL
    #     )
    # """)

    # Example: Add a column to existing table
    # cur.execute("""
    #     ALTER TABLE existing_table
    #     ADD COLUMN new_column TEXT
    # """)

    # Example: Create an index
    # cur.execute("""
    #     CREATE INDEX IF NOT EXISTS idx_name
    #     ON table_name (column_name)
    # """)

    con.commit()


def downgrade(cur, con):
    """
    Rollback this migration (optional).

    Args:
        cur: SQLite cursor
        con: SQLite connection
    """
    # Example: Drop a table
    # cur.execute("DROP TABLE IF EXISTS new_table")

    # Note: SQLite doesn't support DROP COLUMN directly
    # You would need to recreate the table without the column

    con.commit()

