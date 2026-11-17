"""
One-off import of legacy JSON accounts (users/<name>.json) into the database.

Usage: uv run python -m server.migrate [users_dir]

Accounts that already exist in the database are skipped, so it is safe to re-run.
"""

import json
import re
import sys
from pathlib import Path

from sqlmodel import Session

from server import config
from server.db import Account, LedgerEntry, create_db, engine


def migrate(users_dir: Path) -> None:
    create_db()
    imported = skipped = invalid = 0

    for file in sorted(users_dir.glob("*.json")):
        username = file.stem
        if not re.fullmatch(config.USERNAME_PATTERN, username):
            print(f"Invalid username, skipping: {file.name}")
            invalid += 1
            continue

        try:
            data = json.loads(file.read_text())
            bal = min(max(int(data.get("bal", 0)), 0), config.MAX_BALANCE)
        except (OSError, ValueError, TypeError, AttributeError) as e:
            print(f"Unreadable file, skipping: {file.name} ({e})")
            invalid += 1
            continue

        with Session(engine) as session:
            if session.get(Account, username) is not None:
                skipped += 1
                continue

            discordid = data.get("discordid")
            session.add(
                Account(
                    username=username,
                    bal=bal,
                    discordid=None if discordid is None else str(discordid),
                    tags=[str(t) for t in data.get("tags") or []],
                )
            )
            session.add(
                LedgerEntry(username=username, kind="migrate", amount=bal, balance_after=bal)
            )
            session.commit()
            imported += 1

    print(f"Imported {imported}, skipped {skipped} existing, {invalid} invalid")


if __name__ == "__main__":
    migrate(Path(sys.argv[1]) if len(sys.argv) > 1 else config.SERVER_DIR / "users")
