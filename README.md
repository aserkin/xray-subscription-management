# Xray Subscription Builder

Small utility set for building client subscription URLs from Xray VLESS Reality server configs.

## Files

- `import_configs.py`: reads Xray server configs from the `configs/*/config.json` layout and rebuilds `subscriptions.db`.
- `generate_subscriptions.py`: reads `subscriptions.db` and writes per-client plain-text and base64 subscription files under `subscriptions/`.

## Expected config layout

The importer expects host folders like this:

```text
../configs/<host>/
├── config.json
├── key.pub        # optional
└── country.txt    # optional
```

- `config.json` is the Xray server config.
- `key.pub` should contain the public Reality key for that host.
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
```

Generate client subscriptions:

```bash
./generate_subscriptions.py
```

## What Changed

- The importer now rebuilds the database on each run, so repeated imports do not duplicate rows.
- Clients are linked to the exact inbound they belong to, which prevents incorrect cross-joining when one host has multiple inbounds.
- Generated VLESS URLs now use proper query-string and fragment encoding.
- The importer defaults to `../configs`, which matches the current project layout.

## Notes

- `subscriptions.db` and the generated `subscriptions/` directory are ignored by Git because they contain generated and potentially sensitive data.
- This project currently uses only Python standard library modules.

## Recommended Next Improvements

- Add a small validation command that reports missing `key.pub`, empty `country.txt`, duplicate UUIDs, and malformed Xray configs before import.
- Add tests with a tiny fixture set covering multiple hosts and multiple VLESS Reality inbounds on one host.
- Consider normalizing generated filenames if `email` may contain spaces or filesystem-hostile characters.
