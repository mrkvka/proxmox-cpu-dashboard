# Changelog

## [3.3.0] — 2026-05-22

### P1 — product quality (complete)

- **`VERSION`** file — single source for install, collector, package
- **`/usr/share/pve-node-hw-api/`** — installed package tree with docs
- **`install.sh --api-only`** — API without UI / `index.html.tpl` changes
- **`.deb` package** `proxmox-node-hw-api` — `make deb` / `scripts/build-deb.sh`
- **UPGRADE.md**, **CONTRIBUTING.md**, **Makefile**
- Collector **`warnings[]`** when sensors/smartctl/cpufreq missing
- Install layout suitable for repeatable upgrades after `pve-manager` updates

## [3.2.0] — 2026-05-22

API-first cleanup: docs/API.md, CI, no HA/legacy in repo.

## [3.1.0] — 2026-05-22

P0: Hardware.pm, verify/uninstall scripts, CPU confirm dialog.

## [3.0.0] — 2026-05-22

Stable Hardware tab, live inventory, GiB metrics.

## [0.5.0]

Legacy HTTP API on port 8087.
