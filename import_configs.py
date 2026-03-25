#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


DEFAULT_CATALOGUE = Path(__file__).resolve().parent.parent / "configs"

SCHEMA = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS CLIENTS;
DROP TABLE IF EXISTS INBOUNDS;

CREATE TABLE INBOUNDS (
    HOST TEXT NOT NULL,
    DOMAIN TEXT NOT NULL,
    PORT INTEGER NOT NULL,
    PROTOCOL TEXT NOT NULL,
    INBOUNDTAG TEXT NOT NULL,
    NETWORK TEXT NOT NULL,
    SECURITY TEXT NOT NULL,
    DEST TEXT,
    SERVERNAME TEXT,
    PRIVATEKEY TEXT,
    SHORTID TEXT,
    PUBLICKEY TEXT,
    ENCRYPTION TEXT NOT NULL,
    HEADERTYPE TEXT NOT NULL,
    FINGERPRINT TEXT NOT NULL,
    COUNTRY TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (HOST, INBOUNDTAG)
);

CREATE TABLE CLIENTS (
    HOST TEXT NOT NULL,
    INBOUNDTAG TEXT NOT NULL,
    UUID TEXT NOT NULL,
    EMAIL TEXT NOT NULL,
    FLOW TEXT NOT NULL,
    PRIMARY KEY (HOST, INBOUNDTAG, UUID),
    FOREIGN KEY (HOST, INBOUNDTAG)
        REFERENCES INBOUNDS(HOST, INBOUNDTAG)
        ON DELETE CASCADE
);

CREATE INDEX IDX_CLIENTS_UUID ON CLIENTS(UUID);
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Import Xray VLESS Reality server configs into SQLite."
    )
    parser.add_argument("--catalogue", default=str(DEFAULT_CATALOGUE))
    parser.add_argument("--dbpath", default="subscriptions.db")
    parser.add_argument("--domain", default="fp.work.gd")
    parser.add_argument("--encryption", default="none")
    parser.add_argument("--headertype", default="none")
    parser.add_argument("--fingerprint", default="chrome")
    return parser.parse_args()


def read_optional(path: Path, default=""):
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return default


def load_config(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def choose_first(values):
    if not values:
        return ""
    if isinstance(values, list):
        return str(values[0]).strip()
    return str(values).strip()


def import_host(cursor, cfg_path: Path, args):
    host_dir = cfg_path.parent
    hostname = host_dir.name
    public_key = read_optional(host_dir / "key.pub")
    country = read_optional(host_dir / "country.txt")
    config = load_config(cfg_path)

    imported_inbounds = 0
    imported_clients = 0

    for inbound in config.get("inbounds", []):
        protocol = inbound.get("protocol")
        stream = inbound.get("streamSettings", {})
        security = stream.get("security")

        if protocol != "vless" or security != "reality":
            continue

        inbound_tag = inbound.get("tag") or f"untagged-{inbound.get('port', 443)}"
        reality = stream.get("realitySettings", {})

        cursor.execute(
            """
            INSERT INTO INBOUNDS (
                HOST, DOMAIN, PORT, PROTOCOL, INBOUNDTAG, NETWORK, SECURITY,
                DEST, SERVERNAME, PRIVATEKEY, SHORTID, PUBLICKEY,
                ENCRYPTION, HEADERTYPE, FINGERPRINT, COUNTRY
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                hostname,
                args.domain,
                int(inbound.get("port", 443)),
                protocol,
                inbound_tag,
                stream.get("network", "tcp"),
                security,
                reality.get("dest", ""),
                choose_first(reality.get("serverNames", [])),
                reality.get("privateKey", ""),
                choose_first(reality.get("shortIds", [])),
                public_key,
                args.encryption,
                args.headertype,
                args.fingerprint,
                country,
            ),
        )
        imported_inbounds += 1

        for client in inbound.get("settings", {}).get("clients", []):
            client_id = client.get("id")
            email = client.get("email")
            if not client_id or not email:
                continue

            cursor.execute(
                """
                INSERT INTO CLIENTS (HOST, INBOUNDTAG, UUID, EMAIL, FLOW)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    hostname,
                    inbound_tag,
                    client_id,
                    email,
                    client.get("flow", "xtls-rprx-vision"),
                ),
            )
            imported_clients += 1

    return imported_inbounds, imported_clients


def main():
    args = parse_args()
    base = Path(args.catalogue).expanduser().resolve()
    config_paths = sorted(base.glob("*/config.json"))

    if not config_paths:
        raise SystemExit(f"No config.json files found in {base}")

    total_inbounds = 0
    total_clients = 0

    with sqlite3.connect(args.dbpath) as conn:
        cursor = conn.cursor()
        cursor.executescript(SCHEMA)

        for cfg_path in config_paths:
            imported_inbounds, imported_clients = import_host(cursor, cfg_path, args)
            total_inbounds += imported_inbounds
            total_clients += imported_clients

    print(
        f"Imported {total_inbounds} reality inbounds and "
        f"{total_clients} client bindings from {len(config_paths)} hosts."
    )


if __name__ == "__main__":
    main()
