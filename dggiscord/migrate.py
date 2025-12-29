#!/usr/bin/env python3
"""Database migration script."""
import argparse
import sys
import helpers.config as config
from helpers.migrator import Migrator, create_migration
from helpers.log import logging

logger = logging.getLogger(__name__)


def cmd_status(args, migrator):
    applied, pending = migrator.get_status()
    print(f"=== Migration Status ({len(applied)}/{len(applied) + len(pending)}) ===")

    for version, name in applied:
        print(f"  ✓ {version} - {name}")
    for version, name in pending:
        print(f"  ○ {version} - {name}")

    if not pending:
        print("Database is up to date!")


def cmd_upgrade(args, migrator):
    print("Running database migrations...")
    migrator.upgrade()
    print("✓ Migrations completed!")


def cmd_downgrade(args, migrator):
    version = args.version
    print(f"Downgrading to {version or 'previous version'}...")
    migrator.downgrade(version)
    print("✓ Downgrade completed!")


def cmd_create(args):
    filename = create_migration()
    print(f"✓ Created migration: {filename}")


def main():
    parser = argparse.ArgumentParser(description="Database migration tool")
    parser.add_argument("--config", type=str, default="cfg/config.json",
                        help="Path to config file")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    status_parser = subparsers.add_parser("status", help="Show migration status")
    status_parser.set_defaults(func=cmd_status)

    upgrade_parser = subparsers.add_parser("upgrade", help="Run pending migrations")
    upgrade_parser.set_defaults(func=cmd_upgrade)

    downgrade_parser = subparsers.add_parser("downgrade", help="Revert migrations")
    downgrade_parser.add_argument("version", nargs="?", default=None,
                                  help="Target version to downgrade to (default: previous)")
    downgrade_parser.set_defaults(func=cmd_downgrade)

    create_parser = subparsers.add_parser("create", help="Create a new migration file")
    create_parser.set_defaults(func=cmd_create)

    args = parser.parse_args()

    # Default to status if no command given
    if args.command is None:
        args.func = cmd_status

    try:
        if args.command == "create":
            args.func(args)
        else:
            config.load_config(args.config)
            migrator = Migrator(config.cfg['db'])
            args.func(args, migrator)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
