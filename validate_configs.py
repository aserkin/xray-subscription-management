#!/usr/bin/env python3

import argparse
import json
from collections import defaultdict
from pathlib import Path


DEFAULT_CATALOGUE = Path(__file__).resolve().parent.parent / "configs"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate Xray config tree before importing subscriptions."
    )
    parser.add_argument("--catalogue", default=str(DEFAULT_CATALOGUE))
    return parser.parse_args()


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_client(client, host, inbound_tag, seen_uuid_emails, errors):
    client_id = client.get("id")
    email = client.get("email")

    if not client_id:
        errors.append(f"{host}:{inbound_tag}: client entry missing id")
        return

    if not email:
        errors.append(f"{host}:{inbound_tag}:{client_id}: client entry missing email")
        return

    seen_uuid_emails[client_id].add(email)


def validate_reality_inbound(host, inbound, host_dir, seen_uuid_emails, errors, warnings):
    inbound_tag = inbound.get("tag")
    if not inbound_tag:
        errors.append(f"{host}: reality inbound on port {inbound.get('port')} has no tag")
        inbound_tag = f"port-{inbound.get('port', 'unknown')}"

    key_path = host_dir / "key.pub"
    country_path = host_dir / "country.txt"

    if not key_path.exists():
        warnings.append(f"{host}: missing key.pub")
    elif not key_path.read_text(encoding="utf-8").strip():
        warnings.append(f"{host}: key.pub is empty")

    if not country_path.exists():
        warnings.append(f"{host}: missing country.txt")
    elif not country_path.read_text(encoding="utf-8").strip():
        warnings.append(f"{host}: country.txt is empty")

    stream = inbound.get("streamSettings", {})
    reality = stream.get("realitySettings", {})

    if not reality.get("privateKey"):
        errors.append(f"{host}:{inbound_tag}: missing realitySettings.privateKey")

    server_names = reality.get("serverNames", [])
    if not isinstance(server_names, list) or not server_names or not server_names[0]:
        errors.append(f"{host}:{inbound_tag}: missing realitySettings.serverNames[0]")

    short_ids = reality.get("shortIds", [])
    if not isinstance(short_ids, list) or not short_ids or not short_ids[0]:
        errors.append(f"{host}:{inbound_tag}: missing realitySettings.shortIds[0]")

    clients = inbound.get("settings", {}).get("clients", [])
    if not isinstance(clients, list) or not clients:
        errors.append(f"{host}:{inbound_tag}: no clients defined")
        return

    seen_local = set()
    for client in clients:
        client_id = client.get("id")
        if client_id in seen_local:
            errors.append(f"{host}:{inbound_tag}: duplicate client id {client_id}")
        elif client_id:
            seen_local.add(client_id)
        validate_client(client, host, inbound_tag, seen_uuid_emails, errors)


def main():
    args = parse_args()
    base = Path(args.catalogue).expanduser().resolve()
    config_paths = sorted(base.glob("*/config.json"))

    if not config_paths:
        raise SystemExit(f"No config.json files found in {base}")

    errors = []
    warnings = []
    infos = []
    seen_uuid_emails = defaultdict(set)
    reality_hosts = 0
    reality_inbounds = 0

    for cfg_path in config_paths:
        host_dir = cfg_path.parent
        host = host_dir.name

        try:
            config = load_json(cfg_path)
        except json.JSONDecodeError as exc:
            errors.append(f"{host}: invalid JSON in {cfg_path.name}: {exc}")
            continue

        inbounds = config.get("inbounds", [])
        if not isinstance(inbounds, list):
            errors.append(f"{host}: top-level inbounds is not a list")
            continue

        host_reality_inbounds = 0
        for inbound in inbounds:
            if inbound.get("protocol") != "vless":
                continue
            stream = inbound.get("streamSettings", {})
            if stream.get("security") != "reality":
                continue

            host_reality_inbounds += 1
            reality_inbounds += 1
            validate_reality_inbound(
                host, inbound, host_dir, seen_uuid_emails, errors, warnings
            )

        if host_reality_inbounds:
            reality_hosts += 1
        else:
            infos.append(f"{host}: no VLESS Reality inbound found")

    for client_id, emails in sorted(seen_uuid_emails.items()):
        if len(emails) > 1:
            errors.append(
                f"{client_id}: UUID is associated with multiple emails: {', '.join(sorted(emails))}"
            )

    for message in infos:
        print(f"INFO: {message}")
    for message in warnings:
        print(f"WARNING: {message}")
    for message in errors:
        print(f"ERROR: {message}")

    print(
        f"Checked {len(config_paths)} hosts, found {reality_inbounds} VLESS Reality "
        f"inbounds on {reality_hosts} hosts."
    )

    if errors:
        print(f"Validation failed with {len(errors)} error(s) and {len(warnings)} warning(s).")
        raise SystemExit(1)

    print(f"Validation passed with {len(warnings)} warning(s).")


if __name__ == "__main__":
    main()
