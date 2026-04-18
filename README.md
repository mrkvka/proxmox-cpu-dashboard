# Proxmox CPU Dashboard

CPU frequency monitoring & control for Proxmox VE, with a **Home Assistant integration** for automations (UPS, temperature, schedules).

## Features

### Proxmox Summary UI
- Color-coded CPU/NVMe temperatures on the node Summary page
- Governor, current/min/max frequency, per-core frequencies
- Change governor and max frequency from the web UI
- Presets: Performance / Balanced / Powersave
- Fan speed (if sensors are exposed)

### Home Assistant integration
- Auto-discovered sensors: temps, frequency, governor, power (RAPL)
- `select.cpu_governor` — change governor from HA
- `number.cpu_max_frequency` — slider for max frequency (MHz)
- 3 preset buttons
- Works with automations: UPS on battery → switch to powersave, and more

## Architecture

```
┌───────────────────────┐     HTTP :8087     ┌─────────────────────┐
│  Proxmox VE host      │ ◀────────────────▶ │  Home Assistant     │
│  pve-cpufreq-api.py   │     GET  /status   │  proxmox_cpu_ctl    │
│  pve-hwinfo.sh        │     GET  /health   │  (custom component) │
│  pve-cpufreq-set.sh   │     POST /cpufreq  │                     │
│  + JS Summary patch   │                    │                     │
└───────────────────────┘                    └─────────────────────┘
```

---

## 1. Install on Proxmox

```bash
git clone https://github.com/mrkvka/proxmox-cpu-dashboard.git
cd proxmox-cpu-dashboard
bash install.sh
```

Then open Proxmox web UI → Node → Summary, press **Ctrl+Shift+R**.

The installer sets up:
- `/usr/local/bin/pve-hwinfo.sh` (data collection)
- `/usr/local/bin/pve-cpufreq-set.sh` (change governor/frequency)
- `/usr/local/bin/pve-cpufreq-api.py` + systemd service on port 8087
- Patches to `/usr/share/perl5/PVE/API2/Nodes.pm` (exposes thermal data)
- JS override at `/usr/share/pve-manager/js/pve_node_summary.js`

Backups of all original files are saved with `bak_<timestamp>` suffix.

---

## 2. Install Home Assistant integration

### Option A — HACS (Custom Repository)
1. In HACS → **Integrations** → three-dot menu → **Custom repositories**
2. Add: `https://github.com/mrkvka/proxmox-cpu-dashboard`, category **Integration**
3. Install **Proxmox CPU Dashboard**, restart HA

### Option B — manual
Copy `custom_components/proxmox_cpu_ctl/` to `/config/custom_components/` in HA and restart.

### Configure
**Settings → Devices & Services → + Add Integration → Proxmox CPU Dashboard**
- **Host**: IP of Proxmox (e.g. `192.168.1.200`)
- **Port**: `8087`
- **Scan interval**: `15`

A new device appears with ~12 entities.

---

## Entities created

| Entity | Type | Description |
|---|---|---|
| `sensor.proxmox_cpu_temperature` | sensor | CPU Tctl °C |
| `sensor.proxmox_nvme_composite_temperature` | sensor | NVMe composite °C |
| `sensor.proxmox_nvme_sensor_1_temperature` | sensor | NVMe sensor 1 °C |
| `sensor.proxmox_cpu_frequency` | sensor | current MHz |
| `sensor.proxmox_cpu_max_frequency` | sensor | scaling_max_freq MHz |
| `sensor.proxmox_cpu_governor` | sensor | current governor |
| `sensor.proxmox_cpu_power` | sensor | CPU power W (RAPL) |
| `select.proxmox_cpu_governor` | select | change governor |
| `number.proxmox_cpu_max_frequency` | number | slider, MHz |
| `button.proxmox_cpu_preset_performance` | button | Performance preset |
| `button.proxmox_cpu_preset_balanced` | button | Balanced preset |
| `button.proxmox_cpu_preset_powersave` | button | Powersave preset |

---

## Example automations

**UPS on battery → Powersave**
```yaml
alias: "UPS on battery → Powersave"
trigger:
  - platform: state
    entity_id: switch.your_smart_socket
    to: "unavailable"
    for: "00:00:30"
action:
  - service: button.press
    target:
      entity_id: button.proxmox_cpu_preset_powersave
```

**High temperature → throttle CPU**
```yaml
alias: "CPU too hot → Powersave"
trigger:
  - platform: numeric_state
    entity_id: sensor.proxmox_cpu_temperature
    above: 80
action:
  - service: button.press
    target:
      entity_id: button.proxmox_cpu_preset_powersave
```

**Night schedule**
```yaml
alias: "Nighttime: Balanced"
trigger:
  - platform: time
    at: "00:00:00"
action:
  - service: button.press
    target:
      entity_id: button.proxmox_cpu_preset_balanced
```

---

## CPU Governors

| Governor | Description |
|----------|-------------|
| `performance` | Always max frequency |
| `conservative` | Ramp up gradually under load |
| `ondemand` | Jump to max under load |
| `powersave` | Always min frequency |
| `schedutil` | Scheduler-driven |

---

## Uninstall

```bash
bash uninstall.sh          # on Proxmox
```

Remove HA integration from Settings → Devices & Services, then delete `custom_components/proxmox_cpu_ctl/`.

---

## Security

The API listens on **0.0.0.0:8087** without authentication. This is fine in a trusted LAN but **do not expose it to the internet**. Add a firewall rule if needed:
```bash
iptables -A INPUT -p tcp --dport 8087 ! -s 192.168.1.0/24 -j DROP
```

---

## License

MIT
