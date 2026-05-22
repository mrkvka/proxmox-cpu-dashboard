.PHONY: test install deb verify shellcheck

VERSION := $(shell cat VERSION)

test:
	python3 -m py_compile src/pve-hw-collect.py src/pve-hw-apply.py
	python3 -m unittest discover -s tests -p 'test_*.py' -v

shellcheck:
	shellcheck install.sh uninstall.sh scripts/*.sh src/patch-nodes.sh

verify:
	@echo "Run on a Proxmox VE host: bash scripts/verify-patch.sh"

install:
	bash install.sh

deb:
	bash scripts/build-deb.sh
