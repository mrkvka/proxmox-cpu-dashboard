# Roadmap

## Done

| Phase | Focus |
|-------|--------|
| **P0** | Native PVE API (`Hardware.pm`), patch verify, CPU safety confirm, uninstall |
| **P1** | API-first docs, split `proxmox-node-hw-api` / `proxmox-node-hw-ui`, CI, `.deb` |
| **P2** | UI plugin split (`core` / `tab` / `plugin`), legacy script migration, docs |
| **3.4.x** | System power estimate (`power.system_watts`), inventory Power section |

## Next (P3+)

- **Upstream slot** — move tab registration to official ExtJS plugin API when available in PVE
- **Optional Summary strip** — color-coded thermals on Summary without full StatusView override
- **GPU power** — estimate from `lspci` where no sensor exists
- **HA integration** — separate repo; consume `docs/API.md` only

## Out of scope

- HTTP API on port 8087 (legacy; use `:8006` `/nodes/{node}/hw*`)
- Bundling Home Assistant (see [ha-proxmox-cpu-ctl](https://github.com/mrkvka/ha-proxmox-cpu-ctl))
