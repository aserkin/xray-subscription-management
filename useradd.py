#!/usr/bin/env python3

import argparse
import uuid

from generate_subscriptions import generate_all_subscriptions
from import_configs import rebuild_database
from user_ops import DEFAULT_CATALOGUE, collect_reality_configs, save_config
from user_output import build_subscription_details, print_subscription_details, resolve_url_prefix


def parse_args():
    parser = argparse.ArgumentParser(
        description="Add a VLESS Reality client to all existing Reality server configs."
    )
    parser.add_argument("email")
    parser.add_argument("--id", dest="client_id")
    parser.add_argument("--flow", default="xtls-rprx-vision")
    parser.add_argument("--catalogue", default=str(DEFAULT_CATALOGUE))
    parser.add_argument("--dbpath", default="subscriptions.db")
    parser.add_argument("--outdir", default="subscriptions")
    parser.add_argument("--url-prefix")
    parser.add_argument("--domain", default="fp.work.gd")
    parser.add_argument("--encryption", default="none")
    parser.add_argument("--headertype", default="none")
    parser.add_argument("--fingerprint", default="chrome")
    return parser.parse_args()


def main():
    args = parse_args()
    client_id = args.client_id or str(uuid.uuid4())
    entries = collect_reality_configs(args.catalogue)

    if not entries:
        raise SystemExit("No VLESS Reality server configs found.")

    changed_files = []
    updated_inbounds = 0

    for entry in entries:
        file_changed = False
        for inbound in entry["inbounds"]:
            clients = inbound.setdefault("settings", {}).setdefault("clients", [])

            match = None
            for client in clients:
                if client.get("id") == client_id and client.get("email") == args.email:
                    match = client
                    break
                if client.get("email") == args.email and client.get("id") != client_id:
                    raise SystemExit(
                        f"Email {args.email} already exists with a different id in {entry['host']}"
                    )
                if client.get("id") == client_id and client.get("email") != args.email:
                    raise SystemExit(
                        f"ID {client_id} already exists with a different email in {entry['host']}"
                    )

            if match:
                if match.get("flow") != args.flow:
                    match["flow"] = args.flow
                    file_changed = True
                updated_inbounds += 1
                continue

            clients.append(
                {
                    "id": client_id,
                    "email": args.email,
                    "flow": args.flow,
                }
            )
            file_changed = True
            updated_inbounds += 1

        if file_changed:
            save_config(entry["path"], entry["config"])
            changed_files.append(entry["path"])

    rebuild_database(
        args.catalogue,
        args.dbpath,
        domain=args.domain,
        encryption=args.encryption,
        headertype=args.headertype,
        fingerprint=args.fingerprint,
        url_prefix=args.url_prefix,
    )
    generate_all_subscriptions(args.dbpath, args.outdir)

    details = build_subscription_details(
        client_id,
        args.email,
        resolve_url_prefix(args.dbpath, args.url_prefix),
    )

    print(f"Added client to {updated_inbounds} reality inbound(s).")
    if changed_files:
        print("Updated config files:")
        for changed_file in changed_files:
            print(f"- {changed_file}")
    else:
        print("Client already existed everywhere. Subscriptions were regenerated.")

    print()
    print_subscription_details(details)


if __name__ == "__main__":
    main()
