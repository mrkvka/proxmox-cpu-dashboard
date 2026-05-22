# Security

## Trust model

All dashboard features use the **native Proxmox API** on port **8006** (`pveproxy`). There is no separate unauthenticated HTTP service.

| Action | PVE permission | Effect |
|--------|----------------|--------|
| View Hardware tab / `GET /hw` | `Sys.Audit` on node | Read sensors, disks, frequencies |
| Apply governor / profile / CPUs | `Sys.Modify` on node | Change cpufreq and CPU online count |

Only users who can modify the node in Proxmox can change CPU settings — same as shell access to sysfs on the host.

## Risks

1. **CPU offlining** — lowering `online_cpus` or the **Emergency** profile can affect running VMs. The UI shows a confirmation dialog (v3.1+).
2. **Host file patches** — `install.sh` adds a small hook to `PVE::API2::Nodes.pm`. Re-run `bash install.sh` after `apt upgrade pve-manager`.
3. **Collector subprocess** — `pve-hw-collect.py` runs as root via `pvedaemon`; it only reads sysfs/SMART and does not accept user shell input.
4. **Legacy :8087** — older versions used `pve-cpufreq-api` without auth. v3.1 disables and removes it on install.

## Recommendations

- Do not expose port 8006 to the public internet without VPN or strict firewall.
- Use dedicated PVE users/roles with least privilege for monitoring-only access.
- For Home Assistant, use an API token with minimal permissions (see [ha-proxmox-cpu-ctl](https://github.com/mrkvka/ha-proxmox-cpu-ctl)).

## Reporting

Open a GitHub issue on [mrkvka/proxmox-cpu-dashboard](https://github.com/mrkvka/proxmox-cpu-dashboard) for vulnerabilities.
