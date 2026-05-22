# Upgrade guide

## After `apt upgrade pve-manager`

Re-apply both components you use:

```bash
cd proxmox-cpu-dashboard && git pull
bash install-api.sh
bash install-ui.sh    # skip if API-only
bash scripts/verify-patch.sh
bash scripts/verify-ui.sh    # if UI installed
```

## Debian packages

```bash
dpkg -i dist/proxmox-node-hw-api_<version>_all.deb
dpkg -i dist/proxmox-node-hw-ui_<version>_all.deb
```

Upgrade API before UI (same version number in both packages).

## API-only nodes

Install only `proxmox-node-hw-api` — no changes to `index.html.tpl` or ExtJS.

## Remove UI, keep API

```bash
bash uninstall-ui.sh
```

API endpoints remain available for external clients.
