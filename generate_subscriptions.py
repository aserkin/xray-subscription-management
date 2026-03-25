#!/usr/bin/env python3

import argparse
import base64
import sqlite3
from pathlib import Path
from urllib.parse import quote, unquote, urlencode


CLIENTS_QUERY = """
SELECT DISTINCT UUID, EMAIL
FROM CLIENTS
ORDER BY EMAIL, UUID
"""


CLIENT_RECORDS_QUERY = """
SELECT
    c.UUID AS uuid,
    c.EMAIL AS email,
    c.FLOW AS flow,
    i.HOST AS host,
    i.DOMAIN AS domain,
    i.PORT AS port,
    i.PROTOCOL AS protocol,
    i.NETWORK AS network,
    i.SECURITY AS security,
    i.SERVERNAME AS servername,
    i.SHORTID AS shortid,
    i.PUBLICKEY AS publickey,
    i.ENCRYPTION AS encryption,
    i.HEADERTYPE AS headertype,
    i.FINGERPRINT AS fingerprint,
    i.COUNTRY AS country,
    i.INBOUNDTAG AS inboundtag
FROM CLIENTS c
JOIN INBOUNDS i
  ON i.HOST = c.HOST
 AND i.INBOUNDTAG = c.INBOUNDTAG
WHERE c.UUID = ?
ORDER BY i.COUNTRY, i.HOST, i.INBOUNDTAG
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate per-client VLESS subscription files from SQLite."
    )
    parser.add_argument("--dbpath", default="subscriptions.db")
    parser.add_argument("--outdir", default="subscriptions")
    return parser.parse_args()


def format_endpoint_host(value):
    if ":" in value and not value.startswith("["):
        return f"[{value}]"
    return value


def build_url(record, endpoint_host=None, endpoint_port=None, label_host=None):
    params = {
        "security": record["security"],
        "encryption": record["encryption"],
        "headerType": record["headertype"],
        "fp": record["fingerprint"],
        "type": record["network"],
        "flow": record["flow"],
        "pbk": record["publickey"],
    }

    if record["servername"]:
        params["sni"] = record["servername"]
    if record["shortid"]:
        params["sid"] = record["shortid"]

    endpoint_host = endpoint_host or f'{record["host"]}.{record["domain"]}'
    endpoint_port = endpoint_port or record["port"]
    label_host = label_host or record["host"]
    endpoint = f"{format_endpoint_host(str(endpoint_host))}:{endpoint_port}"
    country = unquote(str(record["country"]))
    label = f"{country}-{label_host}-{record['email']}".strip("-")

    return (
        f'{record["protocol"]}://{record["uuid"]}@{endpoint}'
        f'?{urlencode(params, quote_via=quote, safe="")}'
        f'#{quote(label, safe="")}'
    )


def write_subscription_files(base_dir: Path, uuid: str, email: str, urls):
    user_dir = base_dir / uuid
    user_dir.mkdir(parents=True, exist_ok=True)

    content = "\n".join(urls)
    txt_path = user_dir / f"{email}.txt"
    b64_path = user_dir / f"{email}.b64"

    txt_path.write_text(content, encoding="utf-8")
    b64_path.write_text(base64.b64encode(content.encode("utf-8")).decode("ascii"))


def fetch_clients(cursor):
    cursor.execute(CLIENTS_QUERY)
    return cursor.fetchall()


def fetch_client_records(cursor, client_uuid):
    cursor.execute(CLIENT_RECORDS_QUERY, (client_uuid,))
    return cursor.fetchall()


def main():
    args = parse_args()
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(args.dbpath) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        clients = fetch_clients(cursor)

        for client in clients:
            rows = fetch_client_records(cursor, client["UUID"])
            urls = [build_url(row) for row in rows]
            write_subscription_files(out_dir, client["UUID"], client["EMAIL"], urls)

    print(f"Generated subscriptions for {len(clients)} clients in {out_dir}")


if __name__ == "__main__":
    main()
