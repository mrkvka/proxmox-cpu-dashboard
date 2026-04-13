# Proxmox CPU Dashboard

CPU frequency monitoring & control panel for Proxmox VE Summary page.

![screenshot](screenshot.png)

## Features

- **Temperature monitoring** - Color-coded CPU and NVMe temperatures (green/orange/red)
- **CPU frequency info** - Current governor, frequency range, per-core frequencies
- **Live controls** - Change CPU governor and max frequency from the web UI
- **Presets** - Quick buttons: Performance / Balanced / Powersave
- **Fan monitoring** - RPM display (if sensors are available)

## Requirements

- Proxmox VE 8.x or 9.x
- `lm-sensors` package (installed automatically)
- Root access to PVE host

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/proxmox-cpu-dashboard.git
cd proxmox-cpu-dashboard
bash install.sh
```

Then open Proxmox web UI, go to **Node -> Summary**, and press **Ctrl+Shift+R**.

## Uninstallation

```bash
bash uninstall.sh
```

All original files are restored from backups created during installation.

## How It Works

### Backend
- `pve-hwinfo.sh` - Collects sensor data + CPU frequency info as JSON
- `pve-cpufreq-set.sh` - Safely applies governor/frequency changes with validation
- `Nodes.pm` patch - Exposes hardware data via API + adds POST endpoint for CPU control

### Frontend
- `pve_node_summary.js` - ExtJS override that adds monitoring widgets and control panel to the node Summary page

## CPU Governor Modes

| Governor | Description |
|----------|-------------|
| `performance` | Always run at max frequency |
| `conservative` | Gradually increase frequency under load |
| `ondemand` | Quickly jump to max frequency under load |
| `powersave` | Always run at min frequency |
| `schedutil` | Kernel scheduler-driven frequency scaling |

## Notes

- Changes via the UI are applied immediately but **do not persist across reboots**
- For persistent settings, create a systemd service (see install script comments)
- PVE updates may overwrite `Nodes.pm` and `index.html.tpl` - re-run `install.sh` after updates
- Fan control is display-only (hardware-dependent, most mini-PCs manage fans via BIOS)

## Tested On

- Proxmox VE 9.1.1
- AMD Ryzen 7 4800H (mini-PC)
- Should work with any AMD/Intel CPU that supports cpufreq scaling

## License

MIT
