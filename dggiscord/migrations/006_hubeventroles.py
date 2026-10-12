"""
Split the hub notify role into one role per event.

A server can mention one role when the stream goes live and another when a new
video is posted. notifyrole becomes liverole, and videorole starts out as a
copy of it so existing servers keep mentioning the same role in both.
"""
name = "Split hub notify role by event"


def upgrade(cur, con):
    """Rename notifyrole to liverole and add videorole, copied from it."""
    cur.execute("ALTER TABLE hubchannels RENAME COLUMN notifyrole TO liverole")
    cur.execute("ALTER TABLE hubchannels ADD COLUMN videorole INTEGER")
    cur.execute("UPDATE hubchannels SET videorole = liverole")

    con.commit()


def downgrade(cur, con):
    """Drop videorole and rename liverole back to notifyrole."""
    cur.execute("ALTER TABLE hubchannels DROP COLUMN videorole")
    cur.execute("ALTER TABLE hubchannels RENAME COLUMN liverole TO notifyrole")

    con.commit()
