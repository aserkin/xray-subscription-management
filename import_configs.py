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
DROP TABLE IF EXISTS METADATA;

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

CREATE TABLE METADATA (
    KEY TEXT PRIMARY KEY,
    VALUE TEXT NOT NULL
);
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
    parser.add_argument("--url-prefix")
    return parser.parse_args()


def read_optional(path: Path, default=""):
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return default


def load_config(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_required(path: Path, description: str):
    value = read_optional(path)
    if not value:
        raise ValueError(f"Missing required {description}: {path}")
    return value


def choose_first(values):
    if not values:
        return ""
    if isinstance(values, list):
        return str(values[0]).strip()
    return str(values).strip()


def read_existing_url_prefix(dbpath):
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


def resolve_url_prefix(dbpath, url_prefix):
    if url_prefix and url_prefix.strip():
        return url_prefix.strip()

    existing_prefix = read_existing_url_prefix(dbpath)
    if existing_prefix:
        return existing_prefix

    raise SystemExit(
        "--url-prefix is required when importing into a new database. "
        "This value is stored in subscriptions.db for later user operations."
    )


def import_host(cursor, cfg_path: Path, args):
    host_dir = cfg_path.parent
    hostname = host_dir.name
    config = load_config(cfg_path)
    country = read_optional(host_dir / "country.txt")

    reality_inbounds = [
        inbound
        for inbound in config.get("inbounds", [])
        if inbound.get("protocol") == "vless"
        and inbound.get("streamSettings", {}).get("security") == "reality"
    ]
    public_key = ""
    if reality_inbounds:
        public_key = read_required(host_dir / "key.pub", "public key")

    imported_inbounds = 0
    imported_clients = 0

    for inbound in reality_inbounds:
        protocol = inbound.get("protocol")
        stream = inbound.get("streamSettings", {})
        security = stream.get("security")
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


def rebuild_database(
    catalogue,
    dbpath,
    domain="fp.work.gd",
    encryption="none",
    headertype="none",
    fingerprint="chrome",
    url_prefix=None,
):
    base = Path(catalogue).expanduser().resolve()
    config_paths = sorted(base.glob("*/config.json"))

    if not config_paths:
        raise SystemExit(f"No config.json files found in {base}")

    resolved_url_prefix = resolve_url_prefix(dbpath, url_prefix)

    namespace = argparse.Namespace(
        catalogue=str(base),
        dbpath=dbpath,
        domain=domain,
        encryption=encryption,
        headertype=headertype,
        fingerprint=fingerprint,
        url_prefix=resolved_url_prefix,
    )

    total_inbounds = 0
    total_clients = 0

    with sqlite3.connect(dbpath) as conn:
        cursor = conn.cursor()
        cursor.executescript(SCHEMA)
        cursor.execute(
            """
            INSERT INTO METADATA (KEY, VALUE)
            VALUES ('subscription_url_prefix', ?)
            """,
            (resolved_url_prefix,),
        )

        for cfg_path in config_paths:
            imported_inbounds, imported_clients = import_host(cursor, cfg_path, namespace)
            total_inbounds += imported_inbounds
            total_clients += imported_clients

    return len(config_paths), total_inbounds, total_clients


def main():
    args = parse_args()
    host_count, total_inbounds, total_clients = rebuild_database(
        args.catalogue,
        args.dbpath,
        domain=args.domain,
        encryption=args.encryption,
        headertype=args.headertype,
        fingerprint=args.fingerprint,
        url_prefix=args.url_prefix,
    )

    print(
        f"Imported {total_inbounds} reality inbounds and "
        f"{total_clients} client bindings from {host_count} hosts."
    )


if __name__ == "__main__":
    main()
