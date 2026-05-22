# Proxmox Node Hardware API

Hardware inventory and CPU control for **Proxmox VE 9.x** through the **native PVE API** (`:8006`).

Optional **Node → Hardware** tab in the web UI. External tools (monitoring, automation) use the same JSON API.

**Docs:** [docs/API.md](docs/API.md) · **Tag:** [`v3.2.0`](https://github.com/mrkvka/proxmox-cpu-dashboard/releases)

## Compatibility

| Component | Supported |
|-----------|-----------|
| Proxmox VE | 9.0 – 9.x (re-run `install.sh` after `pve-manager` upgrades) |
| CPU | Intel / AMD (sysfs cpufreq) |
| Sensors | `lm-sensors` (installed if missing) |
| Disks | `smartctl` optional (SMART / lifetime GiB) |
| PVE 8.x | Not supported |

## Quick start

```bash
git clone https://github.com/mrkvka/proxmox-cpu-dashboard.git
cd proxmox-cpu-dashboard
bash install.sh
bash scripts/verify-patch.sh
```

```bash
pvesh get /nodes/$(hostname -s)/hw
pvesh get /nodes/$(hostname -s)/hwlive
```

Web UI: **Node → Hardware** → **Ctrl+Shift+R**.

## API summary

| Method | Path |
|--------|------|
| GET | `/nodes/{node}/hw` |
| GET | `/nodes/{node}/hwlive` |
| POST | `/nodes/{node}/hwapply` |
| POST | `/nodes/{node}/hwcpufreq` |
| POST | `/nodes/{node}/hwcpus` |

Details, auth, and examples: **[docs/API.md](docs/API.md)**.

## Architecture

```
Client (:8006) → pveproxy → Nodes.pm → Hardware.pm → collect.py / apply.py
```

Port **8006** is standard Proxmox — this project registers API routes and optional UI scripts.

## Uninstall

```bash
bash uninstall.sh
```

## Security

[SECURITY.md](SECURITY.md)

## Changelog

[CHANGELOG.md](CHANGELOG.md)

## License

MIT
