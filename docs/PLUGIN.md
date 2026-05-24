# UI plugin architecture (P2)

The web UI is a **minimal ExtJS plugin**: three scripts plus build metadata, loaded in strict order from `index.html.tpl`.

## Load order

| # | File | Role |
|---|------|------|
| 1 | `pve_hw_core.js` | `PVECPUDash` — styles, inventory tables, API calls |
| 2 | `pve_hw_tab.js` | `PVE.node.HardwareView` — Hardware tab panel |
| 3 | `pve_hw_plugin.js` | `PVE.panel.Config` override — inserts tab after Summary |
| 4 | `pve_hw_build_info.js` | Version/commit footer (`PVECPUDash.BUILD_INFO`) |

Sources live in `src/ui/`; installed copies under `/usr/share/pve-manager/js/` and `/usr/share/pve-node-hw-ui/ui/`.

## Why not patch `pve_node_summary.js`?

Replacing stock Proxmox Summary JS breaks on every `pve-manager` upgrade. The plugin overrides `PVE.panel.Config.insertNodes` but **only when `$className === 'PVE.node.Config'`** (physical node, not VM/CT). It also matches `xtype: 'pveNodeSummary'`, not guest summary tabs to add one menu entry — the smallest stable hook available today.

## Upstream direction

Proxmox is adding formal plugin slots (e.g. storage UI via `/api2/extjs/plugins/...`). When a **node-level** extension point exists in `pve-manager`, this project should migrate `pve_hw_plugin.js` to that API and drop `index.html.tpl` sed hooks.

Until then, `install-ui.sh` manages script tags idempotently and removes legacy names (`pve_node_summary.js`, `pve_node_hardware.js`).

## Capabilities

The Hardware tab requires `Sys.Audit` on nodes (same as other node config tabs).

## Reinstall

```bash
bash install-ui.sh
```

Ctrl+Shift+R in the browser after install or `pve-manager` upgrade.
