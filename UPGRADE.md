# Upgrade guide

## After Proxmox VE / pve-manager upgrade

`apt upgrade` can replace `/usr/share/perl5/PVE/API2/Nodes.pm` and remove the hardware API hook.

```bash
cd proxmox-cpu-dashboard   # or use files in /usr/share/pve-node-hw-api
git pull                   # or reinstall the same .deb version
bash install.sh
bash scripts/verify-patch.sh
```

Browser: **Ctrl+Shift+R** on the Hardware tab.

## Upgrade from v0.5 / :8087

1. `bash install.sh` — disables `pve-cpufreq-api` if present  
2. Point external clients to native API: [docs/API.md](docs/API.md)  
3. Remove firewall rules for port 8087 if you added any  

## Debian package

```bash
# build on any Linux with dpkg-deb
make deb
dpkg -i dist/proxmox-node-hw-api_*_all.deb
```

Reinstall the same or newer package after `pve-manager` upgrades.

## API-only nodes

```bash
bash install.sh --api-only
```

No changes to `index.html.tpl` or ExtJS files — only `/nodes/{node}/hw*`.
