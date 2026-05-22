# Proxmox Node Hardware API

Hardware inventory and CPU control for **Proxmox VE 9.x** via the native PVE API (`:8006`).

**Version:** see [`VERSION`](VERSION) · **Docs:** [docs/API.md](docs/API.md) · **Upgrade:** [UPGRADE.md](UPGRADE.md)

## Install

**From git (on the Proxmox host):**

```bash
git clone https://github.com/mrkvka/proxmox-cpu-dashboard.git
cd proxmox-cpu-dashboard
bash install.sh              # API + Hardware tab UI
# bash install.sh --api-only   # API only, no ExtJS changes
bash scripts/verify-patch.sh
```

**From .deb:**

```bash
make deb
dpkg -i dist/proxmox-node-hw-api_*_all.deb
```

**API check:**

```bash
pvesh get /nodes/$(hostname -s)/hw
```

Optional UI: **Node → Hardware** → Ctrl+Shift+R.

## Product layout

| Path | Role |
|------|------|
| `/usr/share/pve-node-hw-api/` | Package files, docs, `VERSION` |
| `/usr/share/perl5/PVE/API2/Nodes/Hardware.pm` | API registration |
| `/usr/local/bin/pve-hw-collect.py` | Data collector |
| `/nodes/{node}/hw*` | HTTP API (see [docs/API.md](docs/API.md)) |

## Compatibility

| Component | Supported |
|-----------|-----------|
| Proxmox VE | 9.0 – 9.x |
| CPU | Intel / AMD |
| Sensors | `lm-sensors` |
| Disks | `smartctl` (recommended) |

## Development

```bash
make test
make shellcheck
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Uninstall

```bash
bash uninstall.sh
```

## Security

[SECURITY.md](SECURITY.md) · [CHANGELOG.md](CHANGELOG.md)

## License

MIT
