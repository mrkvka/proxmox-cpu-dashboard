# Proxmox CPU Dashboard **v3.1.0**

Native hardware monitoring and CPU control for **Proxmox VE 9.x** via the official API (`:8006`, roles, CSRF). No sidecar on `:8087`.

**Stable tag:** [`v3.1.0`](https://github.com/mrkvka/proxmox-cpu-dashboard/releases) · **Branch:** `master`

## Compatibility

| Component | Supported | Notes |
|-----------|-----------|--------|
| Proxmox VE | **9.0 – 9.x** | Tested on 9.2.x; run `install.sh` again after `pve-manager` upgrades |
| CPU | Intel / AMD | cpufreq via sysfs; `schedutil` / `acpi-cpufreq` |
| Sensors | `lm-sensors` | Installed by `install.sh` if missing |
| Disks | `smartctl` optional | Without it: no SMART temp / lifetime GiB |
| Browsers | HTTPS UI on :8006 | Same-origin API (no mixed content) |
| PVE 8.x | Not supported | `Nodes.pm` layout differs |
| Home Assistant | Separate repo | [ha-proxmox-cpu-ctl](https://github.com/mrkvka/ha-proxmox-cpu-ctl) — use API token on :8006 |

## UI

| Location | Content |
|----------|---------|
| **Node → Summary** | Stock page (thermals from PVE as before) |
| **Node → Hardware** | Inventory table, live 1 s refresh, governor / MHz / CPUs, presets |

## API

Permissions: `Sys.Audit` (read), `Sys.Modify` (write). Implementation: `/usr/share/perl5/PVE/API2/Nodes/Hardware.pm`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/nodes/{node}/hw` | Full hardware JSON |
| GET | `/nodes/{node}/hwlive` | Live poll snapshot |
| POST | `/nodes/{node}/hwapply` | Profile or combined settings |
| POST | `/nodes/{node}/hwcpufreq` | Governor + max_freq (kHz) |
| POST | `/nodes/{node}/hwcpus` | Online logical CPUs |

See [SECURITY.md](SECURITY.md).

## Install

```bash
git clone https://github.com/mrkvka/proxmox-cpu-dashboard.git
cd proxmox-cpu-dashboard
git checkout v3.1.0   # or master
bash install.sh
bash scripts/verify-patch.sh
```

Browser: **Node → Hardware**, then **Ctrl+Shift+R**.

After every **`apt upgrade pve-manager`**:

```bash
cd proxmox-cpu-dashboard && git pull && bash install.sh
```

## Uninstall

```bash
bash uninstall.sh
```

Keeps `*.bak_*` backups; restores `Nodes.pm` and `index.html.tpl` when backups exist.

## Architecture

```
Browser (:8006) → pveproxy → Nodes.pm (hook) → Hardware.pm → pve-hw-collect.py / pve-hw-apply.py
```

Port **8006** is the normal Proxmox web/API port (not installed by this project).

## Audit

```bash
/usr/local/bin/pve-hw-collect.py --pretty | less
bash scripts/audit-hardware.sh
```

## Changelog

[CHANGELOG.md](CHANGELOG.md)

## License

MIT
