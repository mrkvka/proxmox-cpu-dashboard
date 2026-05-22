# Security

## Trust model

All features use the **Proxmox API** on port **8006** (`pveproxy`). There is no separate unauthenticated HTTP service in v3.2+.

| Action | PVE permission |
|--------|----------------|
| Read `/hw`, `/hwlive` | `Sys.Audit` on the node |
| Write `/hwapply`, `/hwcpufreq`, `/hwcpus` | `Sys.Modify` on the node |

Use **API tokens** with least privilege for automation. Do not expose port 8006 to the public internet without VPN or strict firewall.

## Risks

1. **CPU offlining** — `hwcpus` and the `emergency` profile can reduce online logical CPUs and affect running VMs. The web UI asks for confirmation (v3.1+).
2. **`Nodes.pm` hook** — a small install-time registration block; re-run `bash install.sh` after `pve-manager` upgrades.
3. **Collector** — runs via `pvedaemon` as root; reads sysfs/SMART only, no shell input from API clients.

## Reporting

Open an issue: [mrkvka/proxmox-cpu-dashboard](https://github.com/mrkvka/proxmox-cpu-dashboard/issues)
