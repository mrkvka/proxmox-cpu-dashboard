# Proxmox CPU Dashboard

CPU frequency monitoring & control for Proxmox VE, with a **Home Assistant integration** for automations (UPS, temperature, schedules).

## Features

### Proxmox Summary UI
- Color-coded CPU/NVMe temperatures on the node Summary page
- Governor, current/min/max frequency, per-core frequencies
- Change governor and max frequency from the web UI
- Presets: Performance / Balanced / Powersave / Emergency / Restore via API profiles
- Fan speed (if sensors are exposed)

### Home Assistant integration
- Auto-discovered sensors: temps, frequency, governor, power (RAPL)
- `select.cpu_governor` — change governor from HA
- `number.cpu_max_frequency` — slider for max frequency (MHz)
- Preset buttons backed by `/api/v1/profiles`
- Works with automations: UPS on battery → switch to powersave, and more

## Architecture

```
┌──────────────────────────────┐       HTTP :8087       ┌─────────────────────┐
│ Proxmox VE host              │  ◀──────────────────▶  │ Home Assistant      │
│                              │                         │ proxmox_cpu_ctl     │
│ pve-cpufreq-api.py           │                         │                     │
│   - reads lm-sensors JSON    │                         │ Sensors             │
│   - reads /sys CPU cpufreq   │                         │ Selects             │
│   - reads /sys powercap RAPL │                         │ Numbers             │
│   - writes safe sysfs values │                         │ Buttons             │
│                              │                         │ Automations         │
│ Proxmox Summary JS           │                         │                     │
│   - displays API state       │                         │                     │
│   - sends control actions    │                         │                     │
└──────────────────────────────┘                         └─────────────────────┘
```

The important design rule is: **the Python API is the source of truth**.
The dashboard should not own CPU logic. It only renders current state and calls
API actions. Home Assistant uses the same API, so Proxmox UI and HA cannot drift
into different behavior.

### Runtime pieces

| File | Role |
|---|---|
| `src/pve-cpufreq-api.py` | Main API server. Collects hardware state and applies validated changes. |
| `src/pve-hwinfo.sh` | Compatibility helper used by the Proxmox `Nodes.pm` patch. |
| `src/pve_node_summary.js` | Proxmox Summary UI override. Displays thermal/frequency/fan/control panels. |
| `src/pve-cpufreq-set.sh` | Legacy helper for governor/frequency changes. Kept for compatibility. |
| `src/pve-cpus-set.sh` | Legacy helper for online CPU count changes. Kept for compatibility. |
| `src/pve-cpufreq-api.service` | systemd service for the API. |

---

## API Contract

The service listens on `0.0.0.0:8087` by default.
Current API version: `0.5.0`.

### Compatibility endpoints

These are stable for the current HA integration and older dashboard code:

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness and API version. |
| `GET` | `/status` | HA-friendly compact status shape. |
| `POST` | `/cpufreq` | Legacy governor/max-frequency mutation. |
| `POST` | `/cpus` | Legacy online CPU count mutation. |

`GET /status` returns:

```json
{
  "temps": {
    "cpu_tctl": 62.4,
    "nvme_composite": 45.0
  },
  "cpufreq": {
    "current_khz": 1700000,
    "min_khz": 400000,
    "max_khz": 1700000,
    "hw_min_khz": 400000,
    "hw_max_khz": 2900000,
    "governor": "conservative",
    "available_governors": ["performance", "schedutil", "powersave"],
    "available_frequencies": []
  },
  "cpus": {
    "online": 8,
    "total": 16,
    "offline": 8
  },
  "power_w": 18.2,
  "per_core_mhz": [1700, 1700, 1400]
}
```

### Versioned endpoints

New integrations should use `/api/v1/...`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/status` | Full state: system, CPU, sensors, power, profiles, capabilities. |
| `GET` | `/api/v1/capabilities` | What this host can read/write. |
| `GET` | `/api/v1/sensors` | Normalized temperatures, fans, voltages, plus raw `sensors -jA`. |
| `GET` | `/api/v1/cpufreq` | Aggregate cpufreq state and allowed values. |
| `GET` | `/api/v1/cpus` | Logical CPU online/offline state and per-CPU metadata. |
| `GET` | `/api/v1/power` | RAPL powercap energy/watts readings. |
| `GET` | `/api/v1/profiles` | Resolved presets for this CPU and its supported governors. |
| `POST` | `/api/v1/apply` | Apply one or more validated settings. |
| `POST` | `/api/v1/cpufreq` | Apply governor/min/max frequency. |
| `POST` | `/api/v1/cpus` | Apply online logical CPU count. |
| `POST` | `/api/v1/profiles/<name>/apply` | Apply one resolved profile. |

### Mutations

All mutation endpoints accept JSON or `application/x-www-form-urlencoded`.
Frequencies are stored as kHz in sysfs. For convenience, values below `10000`
are treated as MHz and converted to kHz.

Apply a governor and max frequency:

```bash
curl -X POST http://proxmox:8087/api/v1/apply \
  -H 'Content-Type: application/json' \
  -d '{"governor":"powersave","max_freq_khz":1400000}'
```

Keep only 4 logical CPUs online:

```bash
curl -X POST http://proxmox:8087/api/v1/cpus \
  -H 'Content-Type: application/json' \
  -d '{"online_cpus":4}'
```

Apply a profile:

```bash
curl -X POST http://proxmox:8087/api/v1/profiles/powersave/apply
```

Dry-run without writing sysfs:

```bash
curl -X POST http://proxmox:8087/api/v1/apply \
  -H 'Content-Type: application/json' \
  -d '{"profile":"emergency","dry_run":true}'
```

### Profiles

Profiles are resolved dynamically from the current CPU hardware limits and
available governors:

| Profile | Behavior |
|---|---|
| `performance` | All logical CPUs online, max hardware frequency, fastest available governor. |
| `balanced` | All logical CPUs online, moderate max frequency, conservative/scheduler governor. |
| `powersave` | Reduced logical CPU count and lower max frequency for UPS or heat events. |
| `emergency` | Minimum practical CPU footprint for long UPS runtime. |
| `restore` | All logical CPUs online and max hardware frequency restored. |

### Validation rules

- Invalid governors are rejected unless the CPU does not expose an allowed list.
- `min_freq_khz` and `max_freq_khz` must stay inside hardware limits.
- `min_freq_khz` cannot be greater than `max_freq_khz`.
- `online_cpus` must be between `1` and the total logical CPU count.
- CPU0 is never offlined.
- If `PVE_CPU_API_TOKEN` is set, all mutation endpoints require `Authorization: Bearer <token>` or `X-API-Token: <token>`.

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
- `/usr/local/bin/pve-cpus-set.sh` (change online logical CPU count)
- `/usr/local/bin/pve-cpufreq-api.py` + systemd service on port 8087
- Patches to `/usr/share/perl5/PVE/API2/Nodes.pm` (exposes thermal data)
- JS override at `/usr/share/pve-manager/js/pve_node_summary.js`

Backups of all original files are saved with `bak_<timestamp>` suffix.

---

## 2. Install Home Assistant integration

The HA integration lives in its own repository for cleaner HACS installation:

### 👉 [mrkvka/ha-proxmox-cpu-ctl](https://github.com/mrkvka/ha-proxmox-cpu-ctl)

Quick install via HACS:
1. HACS → **Integrations** → three-dot menu → **Custom repositories**
2. Add `https://github.com/mrkvka/ha-proxmox-cpu-ctl`, category **Integration**
3. Install, restart HA
4. **Settings → Devices & Services → + Add Integration → Proxmox CPU Dashboard**
5. Enter Proxmox IP (e.g. `192.168.1.200`)

See the HA integration's README for manual install and automation examples.

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

## Development and Testing

Run local checks before deploying:

```bash
bash -n install.sh uninstall.sh src/patch-nodes.sh src/pve-cpufreq-set.sh src/pve-cpus-set.sh src/pve-hwinfo.sh
node --check src/pve_node_summary.js
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

The unit tests build a fake sysfs tree, so they do not change the local machine.
They verify:

- CPU count and online/offline detection
- cpufreq governor/frequency parsing
- sensor normalization from `sensors -jA`
- safe sysfs writes against fake files
- dry-run profile behavior
- legacy `/status` shape for Home Assistant

---

## Uninstall

```bash
bash uninstall.sh          # on Proxmox
```

Remove HA integration from Settings → Devices & Services, then delete `custom_components/proxmox_cpu_ctl/`.

---

## Security

The API listens on **0.0.0.0:8087**. By default it does not require authentication
for LAN compatibility, but you can require a token for mutations:

```bash
systemctl edit pve-cpufreq-api.service
```

Add:

```ini
[Service]
Environment=PVE_CPU_API_TOKEN=change-this-token
```

Then:

```bash
systemctl daemon-reload
systemctl restart pve-cpufreq-api.service
```

Do not expose the API to the internet. Add a firewall rule if needed:

```bash
iptables -A INPUT -p tcp --dport 8087 ! -s 192.168.1.0/24 -j DROP
```

---

## License

MIT
