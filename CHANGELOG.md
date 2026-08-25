# Changelog

## [3.6.1] — 2026-08-25

### CPU load in Hardware + Guests

- Группа **CPU**: строки **Load average** (1/5/15) и **Utilization** (% busy из `/proc/stat`)
- Вкладка **Guests**: chip **CPU %** в верхней полоске узла
- Кэш `/var/cache/pve-hw-dashboard/cpu_stat.json` для live-опросов (общий для collector и `/hwguests`)

## [3.6.0] — 2026-07-15

### Guests dashboard tab

- New node tab **Guests** (Pulse-style): VM/LXC table with CPU/MEM/DISK bars, uptime, live net/IO rates
- `GET /nodes/{node}/hwguests` — unified guest list from `PVE::QemuServer::vmstatus` + `PVE::LXC::vmstatus` plus node strip (load/RAM/uptime)
- Filters: type (All/VM/LXC), status (All/Running/Stopped), name/ID search
- Double-click a guest to open the stock Proxmox guest view

## [3.5.5] — 2026-06-19

### Fix — power estimates and UI clarity

- Parse AMD/Intel model suffixes for TDP (e.g. Ryzen 4800H → 45 W, not 280 W)
- Use physical core count for load factor, not logical CPU count
- Power tab: show measured RAPL first; hide misleading TDP/heuristic rows when RAPL is available

## [3.5.4] — 2026-06-19

### Fix — CPU / system power

- **CPU package** (`package_watts`): RAPL package zone only — no summing core/dram/psys zones
- **System total** (`system_watts`): PSYS when available, else hybrid (package + RAM/disks/platform estimate), else heuristic
- **Live polling** (`hwlive`): RAPL energy deltas cached in `/var/cache/pve-hw-dashboard/rapl_state.json` so HA polls get real watts without inflating readings

## [3.5.3] — 2026-05-23

### Public release

- GitHub Releases + `.deb` assets, CI release workflow, issue templates, README screenshots

### Network inventory

- One **Network** section with subgroups per interface (Ethernet, Wi-Fi, bridge, …)
- Detect kind/MAC/wireless mode; sort Ethernet before Wi-Fi

## [3.5.2] — 2026-05-23

### Fix

- Hardware tab only on **node** config (`PVE.node.Config`), not on VM/CT guests

## [3.5.1] — 2026-05-23

### Fix

- `install-ui.sh`: script tags were not injected (`\${tag}` never expanded); use awk append

## [3.5.0] — 2026-05-22

### P2: UI plugin polish

- Split UI into `src/ui/`: `pve_hw_core.js`, `pve_hw_tab.js`, `pve_hw_plugin.js`
- `install-ui.sh` migrates legacy `pve_node_*.js` names; chained script load order
- `docs/PLUGIN.md`, `docs/ROADMAP.md`

## [3.4.2] — 2026-05-22

### System power estimate

- `power.system_watts` — whole-node estimate (measured RAPL/sensors, hybrid, or heuristic)
- `power.method` / `power.confidence`, `power.estimate` breakdown (CPU TDP, memory, storage, platform)
- Inventory **Power** section shows system total plus component estimates

## [3.4.0] — 2026-05-22

### Split packages for distribution

- **proxmox-node-hw-api** — `install-api.sh`, `uninstall-api.sh`, `build-deb-api.sh`
- **proxmox-node-hw-ui** — `install-ui.sh`, `uninstall-ui.sh`, `build-deb-ui.sh` (Depends on API same version)
- `install.sh` / `uninstall.sh` — convenience wrappers (API+UI)
- `scripts/verify-ui.sh` — UI install checks
- `make deb-api` / `make deb-ui` / `make deb`

## [3.3.0]

Product quality: VERSION file, `/usr/share/pve-node-hw-api/`, `make deb`, warnings[].

## [3.2.0]

API-first docs, CI, no HA in repo.

## [3.1.0]

P0: Hardware.pm, verify scripts, CPU confirm.

## [3.0.0]

Stable Hardware tab and live inventory.

## [0.5.0]

Legacy HTTP API on port 8087.
