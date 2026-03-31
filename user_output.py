#!/usr/bin/env python3

import base64
import sqlite3
import subprocess
from pathlib import Path

from generate_subscriptions import normalize_filename_component


def render_qr(text):
    try:
        completed = subprocess.run(
            ["qrencode", "-t", "ANSIUTF8", text],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit("qrencode is required for QR output but was not found in PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"qrencode failed: {exc.stderr.strip()}") from exc
    return completed.stdout.rstrip()


def build_subscription_details(client_id, email, url_prefix):
    if not url_prefix or not url_prefix.strip():
        raise SystemExit("--url-prefix is required")
    filename = f"{normalize_filename_component(email)}.b64"
    subscription_path = f"{client_id}/{filename}"
    subscription_url = f"{url_prefix.rstrip('/')}/{subscription_path}"
    encoded_url = base64.b64encode(subscription_url.encode("utf-8")).decode("ascii")
    qr_text = render_qr(subscription_url)
    return {
        "id": client_id,
        "email": email,
        "subscription_path": subscription_path,
        "subscription_url": subscription_url,
        "encoded_url": encoded_url,
        "qr_text": qr_text,
    }


def read_stored_url_prefix(dbpath):
    db_file = Path(dbpath)
    if not db_file.exists():
        return None

    with sqlite3.connect(dbpath) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'METADATA'
            """
        )
        if cursor.fetchone() is None:
            return None

        cursor.execute(
            "SELECT VALUE FROM METADATA WHERE KEY = 'subscription_url_prefix'"
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return row[0]


def resolve_url_prefix(dbpath, explicit_url_prefix=None):
    if explicit_url_prefix and explicit_url_prefix.strip():
        return explicit_url_prefix.strip()

    stored_url_prefix = read_stored_url_prefix(dbpath)
    if stored_url_prefix:
        return stored_url_prefix

    raise SystemExit(
        "--url-prefix was not provided and no stored subscription URL prefix was found in "
        f"{dbpath}. Re-run import_configs.py with --url-prefix first."
    )


def print_subscription_details(details):
    print(f"ID: {details['id']}")
    print(f"Email: {details['email']}")
    print(f"Subscription path: {details['subscription_path']}")
    print(f"Subscription URL: {details['subscription_url']}")
    print(f"Subscription URL (base64): {details['encoded_url']}")
    print("Subscription URL QR (ANSI UTF-8):")
    print(details["qr_text"])
