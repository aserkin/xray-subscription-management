#!/usr/bin/env python3

import base64
import subprocess

from generate_subscriptions import normalize_filename_component


DEFAULT_URL_PREFIX = ""


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


def print_subscription_details(details):
    print(f"ID: {details['id']}")
    print(f"Email: {details['email']}")
    print(f"Subscription path: {details['subscription_path']}")
    print(f"Subscription URL: {details['subscription_url']}")
    print(f"Subscription URL (base64): {details['encoded_url']}")
    print("Subscription URL QR (ANSI UTF-8):")
    print(details["qr_text"])
