# Proxmox Node Hardware API

Hardware inventory and CPU control for **Proxmox VE 9.x** via the native PVE API (`:8006`).

Two installable components:

| Package | Purpose |
|---------|---------|
| **proxmox-node-hw-api** | `/nodes/{node}/hw*` JSON API — for scripts, monitoring, Home Assistant, etc. |
| **proxmox-node-hw-ui** | **Node → Hardware** tab in the web UI (requires API package) |

**Version:** [`VERSION`](VERSION) · **API docs:** [docs/API.md](docs/API.md) · [docs/PLUGIN.md](docs/PLUGIN.md)

## Install from git

**API only** (automation / external clients):

```bash
git clone https://github.com/mrkvka/proxmox-cpu-dashboard.git
cd proxmox-cpu-dashboard
bash install-api.sh
pvesh get /nodes/$(hostname -s)/hw
```

**API + UI** (full experience):

```bash
bash install-api.sh
bash install-ui.sh
# or: bash install.sh
```

**Ctrl+Shift+R** in the browser after UI install.

## Install from .deb

```bash
make deb-api    # or: make deb  (both packages)
make deb-ui
dpkg -i dist/proxmox-node-hw-api_*_all.deb
dpkg -i dist/proxmox-node-hw-ui_*_all.deb
```

`proxmox-node-hw-ui` depends on the same version of `proxmox-node-hw-api`.

## Uninstall

```bash
bash uninstall-ui.sh    # first, if UI was installed
bash uninstall-api.sh
# or: bash uninstall.sh
```

## Paths on the host

| Path | Package |
|------|---------|
| `/usr/share/pve-node-hw-api/` | API scripts, docs, `VERSION` |
| `/usr/share/pve-node-hw-ui/` | UI JS sources |
| `/usr/local/bin/pve-hw-collect.py` | Collector |

## After `apt upgrade pve-manager`

```bash
bash install-api.sh
bash install-ui.sh   # if you use the tab
```

See [UPGRADE.md](UPGRADE.md).

## Development

```bash
make test
make deb
```

[CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md) · [CHANGELOG.md](CHANGELOG.md)

## License

MIT
