# Proxmox CPU Dashboard **v3.0.0** (stable)

Нативное расширение Proxmox VE: мониторинг железа и управление CPU через **официальный API** (`:8006`, ACL, CSRF). Без отдельного HTTP-сервиса на `:8087`.

**Стабильная ветка:** `master` · **Тег:** `v3.0.0`

## UI

| Место | Содержимое |
|-------|------------|
| **Node → Summary** | Температуры, частоты CPU, governor / max MHz, пресеты |
| **Node → Hardware** | Полный инвентарь (таблица), live-обновление 1 с, Apply |

## API (порт 8006)

Права PVE: `Sys.Audit` (чтение), `Sys.Modify` (запись).

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/nodes/{node}/hw` | Полный снимок железа |
| GET | `/nodes/{node}/hwlive` | Лёгкий снимок для live UI |
| POST | `/nodes/{node}/hw/cpufreq` | Governor + max_freq (kHz) |
| POST | `/nodes/{node}/hw/cpus` | Online logical CPUs |
| POST | `/nodes/{node}/hw/apply` | Профиль или набор параметров |
| GET | `/nodes/{node}/status` | `thermalstate` = compact JSON |

```bash
pvesh get /nodes/$(hostname -s)/hw
pvesh get /nodes/$(hostname -s)/hwlive
pvesh create /nodes/$(hostname -s)/hw/apply --profile balanced
```

Home Assistant: [ha-proxmox-cpu-ctl](https://github.com/mrkvka/ha-proxmox-cpu-ctl) — используйте PVE API token (`:8006`).

## Установка (stable)

```bash
git clone https://github.com/mrkvka/proxmox-cpu-dashboard.git
cd proxmox-cpu-dashboard
git checkout master   # или: git checkout v3.0.0
bash install.sh
```

В браузере: **Node → Summary** и **Node → Hardware**, затем **Ctrl+Shift+R**.

## Обновление с v0.5 / :8087

```bash
cd proxmox-cpu-dashboard && git pull
bash install.sh
# при необходимости: systemctl disable --now pve-cpufreq-api 2>/dev/null
```

## Удаление

```bash
bash uninstall.sh
```

## Аудит

```bash
/usr/local/bin/pve-hw-collect.py --pretty | less
bash scripts/audit-hardware.sh
```

См. [CHANGELOG.md](CHANGELOG.md).

## Лицензия

MIT
