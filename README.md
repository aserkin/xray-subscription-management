# Xray Subscription Builder

Small utility set for building client subscription URLs from Xray VLESS Reality server configs.

## Files

- `import_configs.py`: reads Xray server configs from the `configs/*/config.json` layout and rebuilds `subscriptions.db`.
- `generate_subscriptions.py`: reads `subscriptions.db` and writes per-client plain-text and base64 subscription files under `subscriptions/`.
- `create_bypass.py`: interactively appends bypass IP/port variants for all users.
- `validate_configs.py`: validates config structure and metadata before import.

## Expected config layout

The importer expects host folders like this:

```text
../configs/<host>/
├── config.json
├── key.pub        # required for VLESS Reality hosts
└── country.txt    # optional
```

- `config.json` is the Xray server config.
- `key.pub` must contain the public Reality key for any host that exposes a VLESS Reality inbound.
- `country.txt` is a free-form label used in generated subscription names.

## Usage

Rebuild the database from configs:

```bash
./import_configs.py
```

Custom input or output paths:

```bash
./import_configs.py --catalogue ../configs --dbpath subscriptions.db
./generate_subscriptions.py --dbpath subscriptions.db --outdir subscriptions
./create_bypass.py --dbpath subscriptions.db --outdir subscriptions
```

Generate client subscriptions:

```bash
./generate_subscriptions.py
```

Using `make`:

```bash
make check
make validate
make rebuild
make bypass
```

`make bypass` validates and imports configs, then asks once per server endpoint for a bypass hostname or IP address and TCP port. For each entered bypass, it rewrites every client subscription with the original URLs plus appended bypass variants that change only the endpoint host and port.

## What Changed

- The importer now rebuilds the database on each run, so repeated imports do not duplicate rows.
- Clients are linked to the exact inbound they belong to, which prevents incorrect cross-joining when one host has multiple inbounds.
- Generated VLESS URLs now use proper query-string and fragment encoding.
- The importer defaults to `../configs`, which matches the current project layout.

## Notes

- `subscriptions.db` and the generated `subscriptions/` directory are ignored by Git because they contain generated and potentially sensitive data.
- This project currently uses only Python standard library modules.
- `make rebuild` now runs validation first and stops on validation errors.

## Validation

`validate_configs.py` checks:

- JSON parsing and `inbounds` structure.
- Presence of Reality-specific fields needed by the importer.
- Missing or empty `key.pub` for hosts that expose VLESS Reality inbounds.
- Missing or empty `country.txt` for hosts that expose VLESS Reality inbounds.
- Duplicate client UUIDs within an inbound.
- UUIDs reused with different client email labels.

Hosts without VLESS Reality inbounds are reported as informational entries and do not fail validation.

## Recommended Next Improvements

- Add tests with a tiny fixture set covering multiple hosts and multiple VLESS Reality inbounds on one host.
- Consider normalizing generated filenames if `email` may contain spaces or filesystem-hostile characters.
