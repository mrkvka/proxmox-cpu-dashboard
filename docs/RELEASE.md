## Proxmox Node Hardware v3.5.3

First **public stable** release of the v3 line: native Proxmox API, optional Hardware tab, split Debian packages.

### Requirements

- **Proxmox VE 9.x** (`pve-manager` ≥ 8.0 in package metadata; tested on 9.2)
- Permissions: `Sys.Audit` (read), `Sys.Modify` (CPU profiles / frequency)

### Install

**From .deb (recommended):**

```bash
dpkg -i proxmox-node-hw-api_3.5.3_all.deb
dpkg -i proxmox-node-hw-ui_3.5.3_all.deb   # optional UI tab
```

**From git:**

```bash
git clone https://github.com/mrkvka/proxmox-cpu-dashboard.git
cd proxmox-cpu-dashboard
bash install-api.sh
bash install-ui.sh    # optional
```

Verify: `pvesh get /nodes/$(hostname -s)/hw --output-format json`

Browser: **Ctrl+Shift+R** after UI install.

### Highlights (3.4 → 3.5)

- **Native API** — `GET/POST /nodes/{node}/hw*` on port **8006** (no separate HTTP service)
- **Hardware tab** — node only (not VM/CT); minimal ExtJS plugin (`core` / `tab` / `plugin`)
- **System power** — `power.system_watts` (RAPL + hybrid + heuristic estimate)
- **Network inventory** — one section, subgroups per NIC (Ethernet, Wi‑Fi, bridge…)
- **CPU control** — governor, max freq, online CPUs, presets with safety confirm
- **Packages** — `proxmox-node-hw-api` + `proxmox-node-hw-ui`

### After `apt upgrade pve-manager`

```bash
bash install-api.sh
bash install-ui.sh   # if you use the tab
bash scripts/verify-patch.sh
```

See [UPGRADE.md](https://github.com/mrkvka/proxmox-cpu-dashboard/blob/master/UPGRADE.md).

### Known limitations

- UI installs script tags into `index.html.tpl` (see [PLUGIN.md](https://github.com/mrkvka/proxmox-cpu-dashboard/blob/master/docs/PLUGIN.md))
- Small hook in `Nodes.pm` — reinstall after major `pve-manager` upgrades
- Power readings are **estimates** unless RAPL/sensors are present; not a substitute for PDU/BMC
- Home Assistant integration lives in a [separate repo](https://github.com/mrkvka/ha-proxmox-cpu-ctl)

### Assets in this release

| File | Purpose |
|------|---------|
| `proxmox-node-hw-api_*_all.deb` | API + collector + Perl module |
| `proxmox-node-hw-ui_*_all.deb` | Hardware tab (requires same API version) |

Full changelog: [CHANGELOG.md](https://github.com/mrkvka/proxmox-cpu-dashboard/blob/master/CHANGELOG.md)
