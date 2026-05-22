.PHONY: test install install-api install-ui deb deb-api deb-ui uninstall shellcheck

VERSION := $(shell cat VERSION)

test:
	python3 -m py_compile src/pve-hw-collect.py src/pve-hw-apply.py
	python3 -m unittest discover -s tests -p 'test_*.py' -v

shellcheck:
	shellcheck install.sh install-api.sh install-ui.sh uninstall.sh uninstall-api.sh uninstall-ui.sh scripts/*.sh src/patch-nodes.sh

install-api:
	bash install-api.sh

install-ui:
	bash install-ui.sh

install:
	bash install.sh

uninstall:
	bash uninstall.sh

deb-api:
	bash scripts/build-deb-api.sh

deb-ui:
	bash scripts/build-deb-ui.sh

deb:
	bash scripts/build-deb.sh
