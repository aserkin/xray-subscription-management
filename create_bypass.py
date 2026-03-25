#!/usr/bin/env python3

import argparse
import ipaddress
import sqlite3

from pathlib import Path
import re

from generate_subscriptions import build_url, fetch_client_records, fetch_clients, write_subscription_files


def parse_args():
    parser = argparse.ArgumentParser(
        description="Append bypass IP/port variants to generated subscriptions."
    )
    parser.add_argument("--dbpath", default="subscriptions.db")
    parser.add_argument("--outdir", default="subscriptions")
    return parser.parse_args()


HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.(?!-)[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*\.?$"
)


def normalize_bypass_host(value):
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        if HOSTNAME_RE.fullmatch(value):
            return value.rstrip(".")
        raise ValueError("invalid host")


def prompt_host(source_label, default_host=None):
    while True:
        if default_host:
            prompt = (
                f"Bypass host/IP for {source_label} "
                f"[{default_host}, '-' to skip]: "
            )
        else:
            prompt = f"Bypass host/IP for {source_label} (blank to skip): "

        value = input(prompt).strip()
        if not value:
            return default_host
        if default_host and value == "-":
            return None
        try:
            return normalize_bypass_host(value)
        except ValueError:
            print(
                "Invalid bypass host. Enter a DNS hostname, IPv4, IPv6 literal, "
                "press Enter to use the default, or '-' to skip."
            )


def prompt_port(source_label, default_port, remembered_port=None):
    effective_default = remembered_port if remembered_port is not None else default_port
    while True:
        value = input(f"Bypass TCP port for {source_label} [{effective_default}]: ").strip()
        if not value:
            return effective_default
        if value.isdigit() and 1 <= int(value) <= 65535:
            return int(value)
        print("Invalid TCP port. Enter an integer between 1 and 65535.")


def collect_bypass_map(rows):
    bypass_map = {}
    seen_sources = set()
    default_host = None
    default_port = None

    for row in rows:
        source_key = (row["host"], row["domain"], row["port"])
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)

        source_label = f'{row["host"]}.{row["domain"]}:{row["port"]}'
        bypass_host = prompt_host(source_label, default_host=default_host)
        if not bypass_host:
            continue

        bypass_port = prompt_port(
            source_label,
            row["port"],
            remembered_port=default_port,
        )
        bypass_map[source_key] = (bypass_host, bypass_port)
        if default_host is None:
            default_host = bypass_host
        if default_port is None:
            default_port = bypass_port

    return bypass_map


def fetch_inbounds(cursor):
    cursor.execute(
        """
        SELECT HOST AS host, DOMAIN AS domain, PORT AS port
        FROM INBOUNDS
        ORDER BY COUNTRY, HOST, INBOUNDTAG
        """
    )
    return cursor.fetchall()


def main():
    args = parse_args()
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(args.dbpath) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        clients = fetch_clients(cursor)

        if not clients:
            raise SystemExit("No clients found in the database. Run import first.")

        bypass_map = collect_bypass_map(fetch_inbounds(cursor))

        if not bypass_map:
            print("No bypass entries were provided. Subscription files were left unchanged.")
            return

        for client in clients:
            rows = fetch_client_records(cursor, client["UUID"])
            urls = [build_url(row) for row in rows]

            for row in rows:
                source_key = (row["host"], row["domain"], row["port"])
                if source_key not in bypass_map:
                    continue

                bypass_host, bypass_port = bypass_map[source_key]
                urls.append(
                    build_url(
                        row,
                        endpoint_host=bypass_host,
                        endpoint_port=bypass_port,
                        label_host=row["host"],
                    )
                )

            write_subscription_files(out_dir, client["UUID"], client["EMAIL"], urls)

    print(
        f"Generated subscriptions with bypass additions for {len(clients)} clients in {out_dir}"
    )


if __name__ == "__main__":
    main()
