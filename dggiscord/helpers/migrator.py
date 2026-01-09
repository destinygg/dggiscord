"""
Database migration system for managing schema changes.
"""
import shutil
import sqlite3
import importlib.util
import logging
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent.parent / 'migrations'


def create_migration(name="migration"):
    """Create a new migration file from template."""
    existing = list(MIGRATIONS_DIR.glob('[0-9][0-9][0-9]_*.py'))
    next_version = max((int(f.stem.split('_')[0]) for f in existing), default=0) + 1
    filename = f"{next_version:03d}_{name}.py"
    shutil.copy(MIGRATIONS_DIR / "TEMPLATE.py", MIGRATIONS_DIR / filename)
    return filename


class Migrator:
    """Handles database migrations."""

    def __init__(self, db_path):
        self.db_path = db_path

    @contextmanager
    def _connection(self):
        """Database connection context manager."""
        con = sqlite3.connect(self.db_path)
        try:
            yield con
        finally:
            con.close()

    def _ensure_migrations_table(self, con):
        """Create the migrations tracking table if it doesn't exist."""
        con.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.commit()

    def _load_migration(self, version, file_path):
        """Load a migration module from file."""
        spec = importlib.util.spec_from_file_location(f"migration_{version}", file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _get_migration_files(self):
        """Get all migration files as (version, name, path) tuples."""
        migrations = []
        for file in sorted(MIGRATIONS_DIR.glob('[0-9]*.py')):
            version = file.stem.split('_')[0]
            module = self._load_migration(version, file)
            name = getattr(module, 'name', file.stem)
            migrations.append((version, name, file))
        return migrations

    def _get_applied_versions(self, con):
        """Get set of applied migration versions."""
        rows = con.execute("SELECT version FROM migrations").fetchall()
        return {row[0] for row in rows}

    def upgrade(self):
        """Run all pending migrations."""
        with self._connection() as con:
            self._ensure_migrations_table(con)
            applied = self._get_applied_versions(con)
            cur = con.cursor()

            for version, name, file_path in self._get_migration_files():
                if version in applied:
                    continue

                logger.info(f"Applying migration {version}: {name}")
                module = self._load_migration(version, file_path)
                module.upgrade(cur, con)
                cur.execute("INSERT INTO migrations (version, name) VALUES (?, ?)", (version, name))
                con.commit()

    def downgrade(self, target_version=None):
        """Downgrade migrations. If target_version is None, downgrades the last one."""
        with self._connection() as con:
            self._ensure_migrations_table(con)

            # Get applied versions in order
            rows = con.execute("SELECT version FROM migrations ORDER BY id").fetchall()
            applied_versions = [row[0] for row in rows]

            if not applied_versions:
                logger.info("No migrations to downgrade.")
                return

            # Determine which versions to downgrade
            if target_version is None:
                to_downgrade = [applied_versions[-1]]
            elif target_version in applied_versions:
                idx = applied_versions.index(target_version)
                to_downgrade = applied_versions[idx + 1:]
            else:
                raise ValueError(f"Version {target_version} not found in applied migrations")

            # Build version -> file mapping
            files = {v: f for v, _, f in self._get_migration_files()}
            cur = con.cursor()

            for version in reversed(to_downgrade):
                if version not in files:
                    logger.warning(f"Migration file for {version} not found, skipping")
                    continue

                logger.info(f"Downgrading migration {version}")
                module = self._load_migration(version, files[version])
                module.downgrade(cur, con)
                cur.execute("DELETE FROM migrations WHERE version = ?", (version,))
                con.commit()

    def get_status(self):
        """Get migration status as (applied, pending) tuples of (version, name)."""
        with self._connection() as con:
            self._ensure_migrations_table(con)
            applied = self._get_applied_versions(con)

        all_migrations = [(v, name) for v, name, _ in self._get_migration_files()]
        applied_list = [(v, name) for v, name in all_migrations if v in applied]
        pending_list = [(v, name) for v, name in all_migrations if v not in applied]

        return applied_list, pending_list
