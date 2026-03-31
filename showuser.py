#!/usr/bin/env python3

import argparse
import sqlite3
from pathlib import Path

from user_output import build_subscription_details, print_subscription_details, resolve_url_prefix


def parse_args():
    parser = argparse.ArgumentParser(
        description="Show the generated subscription reference for an existing user."
    )
    parser.add_argument("email")
    parser.add_argument("--dbpath", default="subscriptions.db")
    parser.add_argument("--outdir", default="subscriptions")
    parser.add_argument("--url-prefix")
    return parser.parse_args()


def main():
    args = parse_args()

    with sqlite3.connect(args.dbpath) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT UUID, EMAIL
            FROM CLIENTS
            WHERE EMAIL = ?
            """,
            (args.email,),
        )
        rows = cursor.fetchall()

    if not rows:
        raise SystemExit(f"No user found for email {args.email}")
    if len(rows) > 1:
        raise SystemExit(f"Multiple users found for email {args.email}")

    client_id, email = rows[0]
    details = build_subscription_details(
        client_id,
        email,
        resolve_url_prefix(args.dbpath, args.url_prefix),
    )
    expected_file = Path(args.outdir) / details["subscription_path"]
    if not expected_file.exists():
        raise SystemExit(
            f"User {email} exists in {args.dbpath}, but {expected_file} was not found. "
            "Regenerate subscriptions first."
        )

    print_subscription_details(details)


if __name__ == "__main__":
    main()
