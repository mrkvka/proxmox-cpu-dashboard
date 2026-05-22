# Proxmox Node Hardware API

Native HTTP API on the **Proxmox VE API port** (`8006` / `pveproxy`). No separate dashboard port.

## Authentication

Use a [Proxmox API token](https://pve.proxmox.com/pve-docs/pve-admin-guide.html#pveum_tokens) or session cookie from the web UI.

```bash
export PVE_HOST="https://proxmox.example:8006"
export PVE_TOKEN="PVEAPIToken=user@pam!monitor=YOUR-SECRET"
export NODE="proxmox"

curl -sk -H "Authorization: $PVE_TOKEN" \
  "$PVE_HOST/api2/json/nodes/$NODE/hw"
```

Permissions:

| Endpoint group | PVE permission |
|----------------|----------------|
| `GET /hw`, `GET /hwlive` | `Sys.Audit` on `/nodes/{node}` |
| `POST /hw*` | `Sys.Modify` on `/nodes/{node}` |

## Endpoints

Base path: `/api2/json/nodes/{node}/`

### `GET /hw`

Full hardware snapshot (CPU, sensors, RAPL, memory, disks, network, profiles).

```bash
pvesh get /nodes/$NODE/hw
```

Response includes:

- `meta.version` — package version
- `warnings` — optional list (e.g. missing smartctl)
- `cpu`, `sensors`, `memory`, `storage`, `inventory`, `profiles`, `capabilities`

### `GET /hwlive`

Lightweight snapshot for polling (live fields + cached static data).

```bash
pvesh get /nodes/$NODE/hwlive
```

### `POST /hwapply`

Apply a named profile or combined settings.

```bash
pvesh create /nodes/$NODE/hwapply --profile balanced
pvesh create /nodes/$NODE/hwapply --governor ondemand --max_freq 1700000
```

Profiles: `performance`, `balanced`, `powersave`, `emergency`, `restore`.

Profile `emergency` reduces online CPUs — use with care on hosts running VMs.

### `POST /hwcpufreq`

Set governor and/or maximum frequency (kHz).

```bash
pvesh create /nodes/$NODE/hwcpufreq --governor performance --max_freq 2900000
```

### `POST /hwcpus`

Set number of logical CPUs kept online.

```bash
pvesh create /nodes/$NODE/hwcpus --online_cpus 8
```

### `POST /cpufreq` (legacy alias)

Same as combined cpufreq apply; kept for older clients.

```bash
pvesh create /nodes/$NODE/cpufreq --governor powersave --max_freq 1400000
```

## Local collector (no API)

For debugging on the host:

```bash
/usr/local/bin/pve-hw-collect.py --pretty
/usr/local/bin/pve-hw-collect.py --live
/usr/local/bin/pve-hw-collect.py --compact
```

## Integration notes

- **HTTPS** — use the same host/port as the Proxmox UI.
- **CSRF** — browser UI uses `Proxmox.Utils.API2Request`; external apps use API tokens (no CSRF).
- **Rate** — prefer `hwlive` for periodic polling (1–5 s), `hw` for full refresh.
- Third-party automation (Home Assistant, scripts, monitoring) should call these endpoints only — not a separate HTTP service.

## Upgrade

After `apt upgrade pve-manager`, re-run `bash install.sh` on the node.

## API-only install

`bash install.sh --api-only` — no changes to Proxmox web UI files.


### Power (`power`)

| Field | Description |
|-------|-------------|
| `system_watts` | Display power (W): measured RAPL/sensors, hybrid, or estimated total |
| `package_watts` | CPU package from RAPL when available |
| `method` | `measured`, `hybrid`, or `estimated` |
| `confidence` | `low`, `medium` |
| `estimate` | Heuristic breakdown: `cpu_tdp_w`, `memory_w`, `storage_w`, `platform_w`, `load_total_w`, `idle_total_w` |
| `rapl_breakdown` | Per-zone RAPL readings |

