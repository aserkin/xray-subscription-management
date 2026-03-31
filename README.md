# Xray Subscription Builder

Utility scripts for working with VLESS Reality client subscriptions derived from Xray server configs.

## Scope

This project covers:

- validating existing Xray configs
- adding and deleting VLESS Reality clients in server configs
- importing server and client data into SQLite
- generating per-client subscription files
- appending optional bypass variants

Out of scope:

- provisioning or managing the Xray servers themselves
- deploying or hosting the generated subscription files

## Workflow

Typical flow:

1. Maintain server configs in `../configs/<host>/config.json`.
2. Validate them with `validate_configs.py`.
3. On the first import, run `import_configs.py` with `--url-prefix` so the subscription URL prefix is stored in `subscriptions.db`.
4. Generate subscription files under `subscriptions/`.
5. Optionally publish `subscriptions/` with your own hosting method.

`useradd.py` and `userdel.py` update the server configs first, then rebuild the local database and subscriptions automatically.

## Files

- `validate_configs.py`: validate config structure and required metadata.
- `import_configs.py`: rebuild `subscriptions.db` from the config catalogue.
- `generate_subscriptions.py`: generate `.txt` and `.b64` subscription files.
- `create_bypass.py`: append interactive bypass endpoint variants.
- `useradd.py`: add a client to every VLESS Reality inbound across the config catalogue.
- `userdel.py`: remove a client from every VLESS Reality inbound across the config catalogue.
- `showuser.py`: show the generated subscription reference for an existing user.
- `user_ops.py`: shared helpers for editing config files.
- `user_output.py`: shared helpers for subscription URL and QR output.
- `Makefile`: common validation and generation targets.
- `sync-subs.sh`: example sync helper for copying generated subscriptions to a web root.

## Expected Config Layout

The scripts expect host directories like:

```text
../configs/<host>/
├── config.json
├── key.pub
└── country.txt
```

- `config.json` is the Xray config for that host.
- `key.pub` is required for any host exposing a VLESS Reality inbound because it becomes the `pbk` parameter in generated client URLs.
- `country.txt` is optional and is used only as a label fragment in generated URLs.

Hosts without a VLESS Reality inbound are ignored by import and client-management operations.

## Generated Output

Subscriptions are written as:

```text
subscriptions/<uuid>/
├── <normalized-email>.txt
└── <normalized-email>.b64
```

- `.txt` contains one VLESS URL per line.
- `.b64` contains the same content base64-encoded.
- filenames are normalized from the client email label to avoid filesystem-hostile characters.

The generator removes stale files in active user directories and removes subscription directories for deleted users.

## Make Targets

- `make check`: syntax-check all Python scripts.
- `make validate`: validate the config catalogue.
- `make import`: rebuild `subscriptions.db`.
- `make generate`: generate subscriptions from the database.
- `make rebuild`: run `validate`, `import`, and `generate`.
- `make bypass`: run `validate`, `import`, and then append bypass variants interactively.
- `make sync`: mirror `subscriptions/` to `/var/www/html/xray/subscriptions/` by default.
- `make clean`: remove `subscriptions.db` and `subscriptions/`.

## Direct Script Usage

Default paths match the current repository layout:

```bash
./validate_configs.py
./import_configs.py --url-prefix https://your-host.example/xray/subscriptions
./generate_subscriptions.py
./create_bypass.py
```

Custom paths are supported:

```bash
./validate_configs.py --catalogue ../configs
./import_configs.py --catalogue ../configs --dbpath subscriptions.db --url-prefix https://your-host.example/xray/subscriptions
./generate_subscriptions.py --dbpath subscriptions.db --outdir subscriptions
./create_bypass.py --dbpath subscriptions.db --outdir subscriptions
```

Important:

- when `subscriptions.db` does not exist yet, `import_configs.py` must be called with `--url-prefix`
- the importer stores that prefix in the database metadata for later use
- later imports may omit `--url-prefix` and reuse the stored value
- if you already have an older `subscriptions.db`, rebuild it once with `--url-prefix` to populate the stored metadata

The sync destination can be overridden when needed:

```bash
make sync
make sync SYNC_DEST=/srv/www/xray/subscriptions/
```

## User Management

### Add a user

Example:

```bash
./useradd.py alice --url-prefix https://your-host.example/xray/subscriptions
```

Optional arguments:

- `--id <uuid>`: provide a specific UUID instead of generating one.
- `--flow <flow>`: override the default `xtls-rprx-vision`.
- `--url-prefix <url>`: optional override for the stored subscription URL prefix. The concrete deployment URL is intentionally not documented here.

`useradd.py`:

- adds the client to every VLESS Reality inbound found in `../configs`
- rebuilds `subscriptions.db`
- regenerates the subscription files
- prints:
  - client UUID
  - subscription path
  - full subscription URL
  - base64-encoded subscription URL
  - ANSI UTF-8 QR code for the subscription URL

Subscription path format:

```text
<uuid>/<normalized-email>.b64
```

### Delete a user

Delete by email:

```bash
./userdel.py --email alice
```

Delete by UUID:

```bash
./userdel.py --id 11111111-2222-3333-4444-555555555555
```

`userdel.py` removes the matching client from every VLESS Reality inbound, rebuilds `subscriptions.db`, and regenerates subscriptions so deleted users no longer keep stale output directories.

### Show a user

Show by email:

```bash
./showuser.py alice
```

`showuser.py` looks up the user in `subscriptions.db`, verifies the expected `.b64` file exists under `subscriptions/`, and prints the same information as `useradd.py`:

- client UUID
- subscription path
- full subscription URL
- base64-encoded subscription URL
- ANSI UTF-8 QR code for the subscription URL

## Validation Rules

`validate_configs.py` checks:

- JSON parsing and top-level `inbounds` structure
- required Reality fields
- missing or empty `key.pub` for Reality hosts
- missing or empty `country.txt` for Reality hosts
- duplicate client UUIDs inside one inbound
- UUID reuse with different email labels across hosts

Hosts without VLESS Reality inbounds are reported as informational and do not fail validation.

## Bypass Mode

`create_bypass.py` reads the imported inbound list and prompts once per original endpoint.

For each endpoint you can enter:

- a hostname
- an IPv4 address
- an IPv6 address
- nothing, to skip before any default exists

Behavior:

- only the endpoint host and port are replaced
- all other URL parameters remain unchanged
- bypass additions are applied for all users
- the first entered bypass host and port become defaults for later prompts
- pressing `Enter` on later prompts reuses the remembered defaults
- entering `-` on a later host prompt skips that specific endpoint

## Notes

- `subscriptions.db` and `subscriptions/` are generated artifacts and are ignored by Git.
- the tools use only the Python standard library, except `useradd.py` and `showuser.py` rely on the external `qrencode` command to print the ANSI UTF-8 QR code.
- `make sync` uses `rsync -av --delete --progress`, so files deleted locally are also removed from the destination.
- `sync-subs.sh` remains an example helper and is not required by the core workflow.
