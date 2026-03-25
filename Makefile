PYTHON ?= python3
DB ?= subscriptions.db
OUTDIR ?= subscriptions
CATALOGUE ?= ../configs

.PHONY: help check validate import generate bypass rebuild clean

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make check     - syntax-check Python scripts' \
		'  make validate  - validate configs before import' \
		'  make import    - rebuild the SQLite database from configs' \
		'  make generate  - generate subscription files from the database' \
		'  make bypass    - generate subscriptions plus interactive bypass variants' \
		'  make rebuild   - run import and generate' \
		'  make clean     - remove generated database and subscriptions'

check:
	$(PYTHON) -m py_compile validate_configs.py import_configs.py generate_subscriptions.py create_bypass.py

validate:
	./validate_configs.py --catalogue "$(CATALOGUE)"

import:
	./import_configs.py --catalogue "$(CATALOGUE)" --dbpath "$(DB)"

generate:
	./generate_subscriptions.py --dbpath "$(DB)" --outdir "$(OUTDIR)"

bypass: validate import
	./create_bypass.py --dbpath "$(DB)" --outdir "$(OUTDIR)"

rebuild: validate import generate

clean:
	rm -rf "$(DB)" "$(OUTDIR)"
